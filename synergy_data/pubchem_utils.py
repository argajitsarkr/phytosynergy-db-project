"""
PubChem & ClassyFire API utilities for auto-enriching phytochemical data.

This module provides functions to:
1. Fetch molecular identifiers and physicochemical properties from PubChem PUG REST API
2. Fetch chemical taxonomy classification from ClassyFire API
3. Orchestrate enrichment of a Phytochemical model instance

All API calls are best-effort: failures are caught silently so that
data entry is never blocked by external service issues.
"""

import logging
from decimal import Decimal, InvalidOperation

import requests

logger = logging.getLogger(__name__)

# ==============================================================================
# CONSTANTS
# ==============================================================================

PUBCHEM_BASE_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound"
PUBCHEM_PROPERTIES = (
    "CID,CanonicalSMILES,InChIKey,MolecularWeight,MolecularFormula,"
    "XLogP,HBondDonorCount,HBondAcceptorCount,TPSA,RotatableBondCount"
)
PUBCHEM_TIMEOUT = 5  # seconds

CLASSYFIRE_BASE_URL = "http://classyfire.wishartlab.com/entities"
GNPS_CLASSYFIRE_URL = "https://structure.gnps2.org/classyfire"
CLASSYFIRE_TIMEOUT = 8  # seconds (ClassyFire can be slow)


# ==============================================================================
# PUBCHEM API
# ==============================================================================

def fetch_pubchem_data(compound_name):
    """
    Fetch molecular properties from PubChem PUG REST API by compound name.

    Args:
        compound_name: The common name of the compound (e.g., "Quercetin")

    Returns:
        dict with keys: cid, smiles, inchikey, molecular_weight, molecular_formula,
        xlogp, hbd, hba, tpsa, rotatable_bonds. Or None on failure.
    """
    try:
        url = (
            f"{PUBCHEM_BASE_URL}/name/{requests.utils.quote(compound_name)}"
            f"/property/{PUBCHEM_PROPERTIES}/JSON"
        )
        response = requests.get(url, timeout=PUBCHEM_TIMEOUT)
        response.raise_for_status()

        data = response.json()
        props = data.get("PropertyTable", {}).get("Properties", [])
        if not props:
            logger.info("PubChem returned no properties for '%s'", compound_name)
            return None

        p = props[0]  # First (best) match
        return {
            "cid": p.get("CID"),
            "smiles": p.get("CanonicalSMILES"),
            "inchikey": p.get("InChIKey"),
            "molecular_weight": p.get("MolecularWeight"),
            "molecular_formula": p.get("MolecularFormula"),
            "xlogp": p.get("XLogP"),
            "hbd": p.get("HBondDonorCount"),
            "hba": p.get("HBondAcceptorCount"),
            "tpsa": p.get("TPSA"),
            "rotatable_bonds": p.get("RotatableBondCount"),
        }

    except requests.exceptions.Timeout:
        logger.warning("PubChem API timeout for '%s'", compound_name)
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            logger.info("Compound '%s' not found in PubChem", compound_name)
        else:
            logger.warning("PubChem HTTP error for '%s': %s", compound_name, e)
    except Exception as e:
        logger.warning("PubChem API error for '%s': %s", compound_name, e)

    return None


# ==============================================================================
# CLASSYFIRE API
# ==============================================================================

def fetch_classyfire_data(inchikey=None, smiles=None):
    """
    Fetch chemical taxonomy from ClassyFire API.

    Tries the Wishart Lab ClassyFire API first (by InChIKey), then falls back
    to the GNPS ClassyFire endpoint (by SMILES).

    Args:
        inchikey: InChIKey string (preferred lookup)
        smiles: SMILES string (fallback lookup)

    Returns:
        dict with keys: superclass, class, subclass. Or None on failure.
    """
    # Try primary ClassyFire API (by InChIKey)
    if inchikey:
        try:
            url = f"{CLASSYFIRE_BASE_URL}/{inchikey}.json"
            response = requests.get(url, timeout=CLASSYFIRE_TIMEOUT)
            if response.status_code == 200:
                data = response.json()
                result = _parse_classyfire_response(data)
                if result:
                    return result
        except Exception as e:
            logger.warning("ClassyFire API error for InChIKey '%s': %s", inchikey, e)

    # Fallback: GNPS ClassyFire endpoint (by SMILES)
    if smiles:
        try:
            response = requests.get(
                GNPS_CLASSYFIRE_URL,
                params={"smiles": smiles},
                timeout=CLASSYFIRE_TIMEOUT,
            )
            if response.status_code == 200:
                data = response.json()
                result = _parse_classyfire_response(data)
                if result:
                    return result
        except Exception as e:
            logger.warning("GNPS ClassyFire error for SMILES: %s", e)

    return None


def _parse_classyfire_response(data):
    """
    Extract superclass, class, and subclass from a ClassyFire JSON response.

    Returns dict or None if no useful classification found.
    """
    if not data or not isinstance(data, dict):
        return None

    superclass = None
    chem_class = None
    subclass = None

    # ClassyFire response structure varies; handle both formats
    if "superclass" in data and isinstance(data["superclass"], dict):
        superclass = data["superclass"].get("name")
    elif "superclass" in data and isinstance(data["superclass"], str):
        superclass = data["superclass"]

    if "class" in data and isinstance(data["class"], dict):
        chem_class = data["class"].get("name")
    elif "class" in data and isinstance(data["class"], str):
        chem_class = data["class"]

    if "subclass" in data and isinstance(data["subclass"], dict):
        subclass = data["subclass"].get("name")
    elif "subclass" in data and isinstance(data["subclass"], str):
        subclass = data["subclass"]

    # Also handle "direct_parent" as a useful fallback
    if not chem_class and "direct_parent" in data:
        dp = data["direct_parent"]
        if isinstance(dp, dict):
            chem_class = dp.get("name")
        elif isinstance(dp, str):
            chem_class = dp

    if not any([superclass, chem_class, subclass]):
        return None

    return {
        "superclass": superclass,
        "class": chem_class,
        "subclass": subclass,
    }


# ==============================================================================
# ORCHESTRATOR
# ==============================================================================

def enrich_phytochemical(phytochemical):
    """
    Auto-enrich a Phytochemical model instance with PubChem + ClassyFire data.

    Only fills in fields that are currently None/blank (never overwrites existing data).
    Saves the object after enrichment.

    Args:
        phytochemical: A Phytochemical model instance

    Returns:
        dict: {"pubchem": bool, "classyfire": bool} indicating success/failure
    """
    status = {"pubchem": False, "classyfire": False}

    # ---- Step 1: PubChem enrichment ----
    needs_pubchem = (
        not phytochemical.canonical_smiles
        or not phytochemical.pubchem_cid
        or not phytochemical.inchi_key
        or phytochemical.xlogp is None
        or phytochemical.hbd is None
        or phytochemical.hba is None
        or phytochemical.tpsa is None
    )

    pubchem_data = None
    if needs_pubchem:
        pubchem_data = fetch_pubchem_data(phytochemical.compound_name)
        if pubchem_data:
            status["pubchem"] = True
            _apply_pubchem_data(phytochemical, pubchem_data)

    # ---- Step 2: ClassyFire enrichment ----
    needs_classyfire = (
        not phytochemical.chemical_superclass
        and not phytochemical.chemical_class
    )

    if needs_classyfire:
        inchikey = phytochemical.inchi_key
        smiles = phytochemical.canonical_smiles

        classyfire_data = fetch_classyfire_data(inchikey=inchikey, smiles=smiles)
        if classyfire_data:
            status["classyfire"] = True
            _apply_classyfire_data(phytochemical, classyfire_data)

    # ---- Step 3: Save if anything changed ----
    if status["pubchem"] or status["classyfire"]:
        try:
            phytochemical.save()
        except Exception as e:
            logger.warning("Failed to save enriched phytochemical '%s': %s",
                           phytochemical.compound_name, e)

    return status


def _apply_pubchem_data(phytochemical, data):
    """Apply PubChem data to a Phytochemical instance (only fill blanks)."""
    if not phytochemical.pubchem_cid and data.get("cid"):
        phytochemical.pubchem_cid = data["cid"]

    if not phytochemical.canonical_smiles and data.get("smiles"):
        phytochemical.canonical_smiles = data["smiles"]

    if not phytochemical.inchi_key and data.get("inchikey"):
        phytochemical.inchi_key = data["inchikey"]

    if not phytochemical.molecular_weight and data.get("molecular_weight"):
        try:
            phytochemical.molecular_weight = Decimal(str(data["molecular_weight"]))
        except (InvalidOperation, ValueError):
            pass

    if not phytochemical.molecular_formula and data.get("molecular_formula"):
        phytochemical.molecular_formula = data["molecular_formula"]

    if phytochemical.xlogp is None and data.get("xlogp") is not None:
        phytochemical.xlogp = float(data["xlogp"])

    if phytochemical.hbd is None and data.get("hbd") is not None:
        phytochemical.hbd = int(data["hbd"])

    if phytochemical.hba is None and data.get("hba") is not None:
        phytochemical.hba = int(data["hba"])

    if phytochemical.tpsa is None and data.get("tpsa") is not None:
        phytochemical.tpsa = float(data["tpsa"])

    if phytochemical.rotatable_bonds is None and data.get("rotatable_bonds") is not None:
        phytochemical.rotatable_bonds = int(data["rotatable_bonds"])


def _apply_classyfire_data(phytochemical, data):
    """Apply ClassyFire taxonomy data to a Phytochemical instance (only fill blanks)."""
    if not phytochemical.chemical_superclass and data.get("superclass"):
        phytochemical.chemical_superclass = data["superclass"][:200]

    if not phytochemical.chemical_class and data.get("class"):
        phytochemical.chemical_class = data["class"][:200]

    if not phytochemical.chemical_subclass and data.get("subclass"):
        phytochemical.chemical_subclass = data["subclass"][:200]
