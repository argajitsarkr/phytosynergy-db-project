from django.core.management.base import BaseCommand
from django.db.models import Q

from synergy_data import similarity
from synergy_data.models import Phytochemical


class Command(BaseCommand):
    help = (
        "Compute and store Morgan/ECFP4 fingerprints (radius 2, 2048-bit) for "
        "phytochemicals with a SMILES, enabling chemical similarity search. "
        "Run after every bulk import / enrichment cycle."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--all', action='store_true',
            help="Recompute for every compound with a SMILES, not just those missing a fingerprint.",
        )
        parser.add_argument(
            '--name', type=str,
            help="Only (re)compute the fingerprint for this single compound (case-insensitive name).",
        )

    def handle(self, *args, **options):
        if not similarity.rdkit_available():
            self.stderr.write(self.style.ERROR(
                "RDKit is not installed. Install it with: pip install rdkit"
            ))
            return

        qs = (
            Phytochemical.objects
            .exclude(canonical_smiles__isnull=True)
            .exclude(canonical_smiles__exact='')
        )

        if options.get('name'):
            qs = qs.filter(compound_name__iexact=options['name'].strip())
        elif not options.get('all'):
            # Only those missing a fingerprint.
            qs = qs.filter(Q(morgan_fp__isnull=True) | Q(morgan_fp__exact=''))

        total = qs.count()
        if total == 0:
            self.stdout.write(self.style.SUCCESS(
                "No phytochemicals need fingerprinting."
            ))
            return

        self.stdout.write(f"Fingerprinting {total} phytochemical(s)...")

        processed = 0
        errors = 0
        for phyto in qs.iterator():
            if similarity.update_fingerprint(phyto):
                processed += 1
            else:
                errors += 1
                self.stderr.write(self.style.WARNING(
                    f"  Could not fingerprint '{phyto.compound_name}' "
                    f"(invalid or missing SMILES), skipping."
                ))

            if processed and (processed % 10 == 0 or processed == total):
                self.stdout.write(f"  Fingerprinted {processed}/{total}")

        self.stdout.write(self.style.SUCCESS(
            f"Done. Fingerprinted: {processed}, Skipped: {errors}"
        ))
