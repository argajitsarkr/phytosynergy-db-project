"""Delete out-of-scope (non-ESKAPE) synergy experiments.

Scope decision (2026-06-14): keep ESKAPE genera + Escherichia (E. coli);
remove Candida (fungus), Propionibacterium, Bacillus, and Aeromonas.

Dry-run by default - prints what WOULD be deleted. Pass --apply to actually
delete. Take a database backup first (docker compose exec db pg_dump ...).
"""
from django.core.management.base import BaseCommand

from synergy_data.models import Pathogen, Phytochemical, SynergyExperiment

# Genera to remove. Edit here if the scope decision changes.
REMOVE_GENERA = ["Candida", "Propionibacterium", "Bacillus", "Aeromonas"]


class Command(BaseCommand):
    help = "Delete synergy experiments whose pathogen genus is out of scope (non-ESKAPE)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply", action="store_true",
            help="Actually delete. Without this flag the command is a dry run.",
        )
        parser.add_argument(
            "--genera", nargs="*", default=REMOVE_GENERA,
            help="Override the list of genera to remove.",
        )
        parser.add_argument(
            "--clean-orphan-phyto", action="store_true",
            help="Also delete phytochemicals left with zero experiments.",
        )

    def handle(self, *args, **opts):
        genera = opts["genera"]
        qs = (
            SynergyExperiment.objects
            .filter(pathogen__genus__in=genera)
            .select_related("pathogen", "phytochemical", "antibiotic")
        )
        count = qs.count()

        self.stdout.write(f"Genera targeted for removal: {', '.join(genera)}")
        self.stdout.write(f"Matched {count} synergy experiment(s):\n")
        for e in qs.order_by("pathogen__genus", "id"):
            self.stdout.write(
                f"  [id {e.id}] {e.phytochemical.compound_name} + "
                f"{e.antibiotic.antibiotic_name} vs {e.pathogen}"
            )

        if not opts["apply"]:
            self.stdout.write(self.style.WARNING(
                "\nDRY RUN - nothing was deleted. Re-run with --apply to delete "
                "(back up the database first)."
            ))
            return

        deleted, _ = qs.delete()
        self.stdout.write(self.style.SUCCESS(
            f"\nDeleted {count} experiment(s) ({deleted} rows incl. relations)."
        ))

        # Clean up pathogen records that no longer have any experiments.
        orphan_path = Pathogen.objects.filter(
            genus__in=genera, synergyexperiment__isnull=True
        )
        op = orphan_path.count()
        orphan_path.delete()

        self.stdout.write(self.style.SUCCESS(
            f"Removed {op} orphaned pathogen record(s)."
        ))

        # Phytochemicals left with zero experiments (e.g. a compound only ever
        # tested against a removed pathogen). Only deleted when explicitly asked,
        # since an orphaned compound is harmless and removal is destructive.
        orphan_phyto = Phytochemical.objects.filter(synergyexperiment__isnull=True)
        orphan_names = list(orphan_phyto.values_list("compound_name", flat=True))
        if opts["clean_orphan_phyto"]:
            orphan_phyto.delete()
            self.stdout.write(self.style.SUCCESS(
                f"Removed {len(orphan_names)} orphaned phytochemical(s): "
                + (", ".join(orphan_names) or "none")
            ))
        elif orphan_names:
            self.stdout.write(self.style.WARNING(
                f"{len(orphan_names)} phytochemical(s) now have no experiments "
                f"(left in place): {', '.join(orphan_names)}. "
                "Re-run with --clean-orphan-phyto to remove them."
            ))
