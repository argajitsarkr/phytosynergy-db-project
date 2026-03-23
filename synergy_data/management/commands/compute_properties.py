from django.core.management.base import BaseCommand
from synergy_data.models import Phytochemical
from decimal import Decimal


class Command(BaseCommand):
    help = "Batch-compute cheminformatics properties from SMILES using RDKit"

    def handle(self, *args, **options):
        try:
            from rdkit import Chem
            from rdkit.Chem import Descriptors, Lipinski, rdMolDescriptors
        except ImportError:
            self.stderr.write(self.style.ERROR(
                "RDKit is not installed. Install it with: pip install rdkit-pypi"
            ))
            return

        # Query phytochemicals that have SMILES but haven't been processed yet
        qs = Phytochemical.objects.filter(
            canonical_smiles__isnull=False,
            logp__isnull=True,
        ).exclude(canonical_smiles='')

        total = qs.count()
        if total == 0:
            self.stdout.write(self.style.SUCCESS("No unprocessed phytochemicals found."))
            return

        self.stdout.write(f"Processing {total} phytochemicals...")

        processed = 0
        errors = 0

        for phyto in qs.iterator():
            mol = Chem.MolFromSmiles(phyto.canonical_smiles)
            if mol is None:
                self.stderr.write(
                    self.style.WARNING(f"  Invalid SMILES for '{phyto.compound_name}', skipping.")
                )
                errors += 1
                continue

            # Compute properties
            logp = Descriptors.MolLogP(mol)
            tpsa = Descriptors.TPSA(mol)
            hbd = Lipinski.NumHDonors(mol)
            hba = Lipinski.NumHAcceptors(mol)
            rotatable = Lipinski.NumRotatableBonds(mol)
            num_rings = rdMolDescriptors.CalcNumRings(mol)
            heavy_atoms = mol.GetNumHeavyAtoms()
            mw = Descriptors.MolWt(mol)

            # Compute Lipinski violations
            violations = 0
            if mw > 500:
                violations += 1
            if logp > 5:
                violations += 1
            if hbd > 5:
                violations += 1
            if hba > 10:
                violations += 1

            # Update the record
            phyto.logp = Decimal(str(round(logp, 3)))
            phyto.tpsa = round(tpsa, 3)
            phyto.hbd = hbd
            phyto.hba = hba
            phyto.rotatable_bonds = rotatable
            phyto.num_rings = num_rings
            phyto.heavy_atom_count = heavy_atoms
            phyto.lipinski_violations = violations
            phyto.is_drug_like = violations <= 1

            if phyto.molecular_weight is None:
                phyto.molecular_weight = Decimal(str(round(mw, 4)))

            phyto.save()
            processed += 1

            if processed % 10 == 0 or processed == total:
                self.stdout.write(f"  Processed {processed}/{total} phytochemicals")

        self.stdout.write(self.style.SUCCESS(
            f"Done. Processed: {processed}, Errors: {errors}"
        ))
