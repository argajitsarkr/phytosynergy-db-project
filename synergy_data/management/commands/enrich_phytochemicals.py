"""
Management command to backfill/re-enrich all Phytochemical records
with PubChem + ClassyFire data.

Usage:
    python manage.py enrich_phytochemicals          # Enrich all that need it
    python manage.py enrich_phytochemicals --all     # Force re-enrich everything
    python manage.py enrich_phytochemicals --name "Quercetin"  # Enrich one compound
"""

import time

from django.core.management.base import BaseCommand

from synergy_data.models import Phytochemical
from synergy_data.pubchem_utils import enrich_phytochemical


class Command(BaseCommand):
    help = "Backfill Phytochemical records with PubChem and ClassyFire data"

    def add_arguments(self, parser):
        parser.add_argument(
            "--all",
            action="store_true",
            help="Re-enrich ALL phytochemicals (even those already enriched)",
        )
        parser.add_argument(
            "--name",
            type=str,
            help="Enrich a specific compound by name",
        )

    def handle(self, *args, **options):
        if options["name"]:
            try:
                phyto = Phytochemical.objects.get(compound_name__iexact=options["name"])
                queryset = Phytochemical.objects.filter(pk=phyto.pk)
            except Phytochemical.DoesNotExist:
                self.stderr.write(
                    self.style.ERROR(f"Compound '{options['name']}' not found")
                )
                return
        elif options["all"]:
            queryset = Phytochemical.objects.all()
        else:
            # Only those missing key data
            queryset = Phytochemical.objects.filter(
                canonical_smiles__isnull=True
            ) | Phytochemical.objects.filter(
                canonical_smiles__exact=""
            ) | Phytochemical.objects.filter(
                xlogp__isnull=True
            ) | Phytochemical.objects.filter(
                chemical_class__isnull=True
            )
            queryset = queryset.distinct()

        total = queryset.count()
        if total == 0:
            self.stdout.write(self.style.SUCCESS("No phytochemicals need enrichment."))
            return

        self.stdout.write(f"Enriching {total} phytochemical(s)...\n")

        success_pubchem = 0
        success_classyfire = 0
        failed = 0

        for i, phyto in enumerate(queryset.iterator(), 1):
            self.stdout.write(f"  [{i}/{total}] {phyto.compound_name}... ", ending="")

            status = enrich_phytochemical(phyto)

            parts = []
            if status.get("pubchem"):
                parts.append("PubChem OK")
                success_pubchem += 1
            if status.get("classyfire"):
                parts.append("ClassyFire OK")
                success_classyfire += 1

            if parts:
                self.stdout.write(self.style.SUCCESS(" | ".join(parts)))
            else:
                self.stdout.write(self.style.WARNING("No data found"))
                failed += 1

            # Rate limiting: PubChem allows 5 req/sec
            time.sleep(0.3)

        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(
            self.style.SUCCESS(
                f"Done! PubChem: {success_pubchem}/{total}, "
                f"ClassyFire: {success_classyfire}/{total}, "
                f"No data: {failed}/{total}"
            )
        )
