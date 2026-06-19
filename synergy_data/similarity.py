"""Chemical similarity search utilities (Morgan / ECFP4 + Tanimoto).

A researcher pastes a SMILES string and we return the structurally most similar
phytochemicals already in PhytoSynergyDB, ranked by Tanimoto similarity.

Fingerprints are 2048-bit Morgan fingerprints with radius 2 (the ECFP4
equivalent). They are precomputed at curation time and stored on
`Phytochemical.morgan_fp` as a 2048-character '0'/'1' bit string, so a query
only has to fingerprint the single input molecule and run cheap Tanimoto
comparisons in Python against the stored set.

All RDKit imports are deferred so the Django app still boots if RDKit is absent;
the query path then surfaces a clear error instead of failing at import time.
"""

import logging

logger = logging.getLogger(__name__)

# ECFP4 == Morgan fingerprint, radius 2. 2048 bits is the community-standard size.
FP_RADIUS = 2
FP_NBITS = 2048


def _rdkit():
    """Import RDKit lazily. Raises ImportError if RDKit is not installed."""
    from rdkit import Chem, DataStructs
    from rdkit.Chem import rdFingerprintGenerator
    return Chem, rdFingerprintGenerator, DataStructs


# Cache the Morgan generator so we build it once, not per-molecule.
_morgan_generator = None


def _get_morgan_generator():
    """Return a cached Morgan (ECFP4) fingerprint generator."""
    global _morgan_generator
    if _morgan_generator is None:
        _, rdFingerprintGenerator, _ = _rdkit()
        _morgan_generator = rdFingerprintGenerator.GetMorganGenerator(
            radius=FP_RADIUS, fpSize=FP_NBITS
        )
    return _morgan_generator


def rdkit_available():
    """True if RDKit can be imported on this server."""
    try:
        _rdkit()
        return True
    except Exception:
        return False


def compute_fingerprint(smiles):
    """Return the ECFP4 ``ExplicitBitVect`` for a SMILES string.

    Returns None if the SMILES is empty, unparseable, or RDKit is unavailable.
    """
    if not smiles:
        return None
    try:
        Chem, _, _ = _rdkit()
        generator = _get_morgan_generator()
    except Exception:
        return None
    mol = Chem.MolFromSmiles(str(smiles).strip())
    if mol is None:
        return None
    return generator.GetFingerprint(mol)


def fp_to_bitstring(fp):
    """Serialise an ``ExplicitBitVect`` to a 2048-char '0'/'1' string for storage."""
    return fp.ToBitString() if fp is not None else None


def bitstring_to_fp(bitstring):
    """Rebuild an ``ExplicitBitVect`` from a stored bit string, or None."""
    if not bitstring:
        return None
    try:
        _, _, DataStructs = _rdkit()
        return DataStructs.CreateFromBitString(str(bitstring).strip())
    except Exception:
        return None


def tanimoto(fp1, fp2):
    """Tanimoto similarity between two ``ExplicitBitVect`` objects (0.0 - 1.0)."""
    _, _, DataStructs = _rdkit()
    return DataStructs.TanimotoSimilarity(fp1, fp2)


def get_phyto_fingerprint(phyto):
    """Fingerprint for a Phytochemical: prefer the stored bit string, fall back
    to computing it live from canonical_smiles (so search still works before the
    backfill command has been run)."""
    fp = bitstring_to_fp(getattr(phyto, 'morgan_fp', None))
    if fp is None:
        fp = compute_fingerprint(phyto.canonical_smiles)
    return fp


def update_fingerprint(phyto):
    """Compute and store the fingerprint for a phytochemical from its SMILES.

    Returns True if a fingerprint was stored, False otherwise (no SMILES,
    unparseable structure, or RDKit unavailable). Safe to call after every
    enrichment - it no-ops gracefully when chemistry data is missing.
    """
    fp = compute_fingerprint(phyto.canonical_smiles)
    if fp is None:
        return False
    phyto.morgan_fp = fp_to_bitstring(fp)
    phyto.save(update_fields=['morgan_fp'])
    return True


def search_similar(query_smiles, limit=25, threshold=0.0):
    """Rank stored phytochemicals by Tanimoto similarity to ``query_smiles``.

    Returns a list of ``{'phytochemical': <obj>, 'similarity': <float>}`` dicts
    sorted by descending similarity (ties broken by compound name).

    Raises:
        RuntimeError: RDKit is not installed on the server.
        ValueError:   the query SMILES could not be parsed.
    """
    if not rdkit_available():
        raise RuntimeError(
            "Similarity search is unavailable: RDKit is not installed on the server."
        )

    query_fp = compute_fingerprint(query_smiles)
    if query_fp is None:
        raise ValueError("Could not parse that SMILES string. Please check the structure.")

    # Imported here to avoid a circular import at module load time.
    from .models import Phytochemical

    candidates = (
        Phytochemical.objects
        .exclude(canonical_smiles__isnull=True)
        .exclude(canonical_smiles__exact='')
    )

    results = []
    for phyto in candidates:
        fp = get_phyto_fingerprint(phyto)
        if fp is None:
            continue
        sim = tanimoto(query_fp, fp)
        if sim >= threshold:
            results.append({'phytochemical': phyto, 'similarity': sim})

    results.sort(key=lambda r: (-r['similarity'], r['phytochemical'].compound_name.lower()))
    return results[:limit]
