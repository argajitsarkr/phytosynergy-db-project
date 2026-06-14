"""Normalize abbreviated pathogen genera, then backfill Pathogen.gram_stain
from genus for existing records (older rows predate the auto-derive).

Phase 1 - expand known abbreviated genera (e.g. "S." -> "Staphylococcus";
in the current data every "S." row is S. aureus, with species/strain already
stored correctly). Merges onto an existing pathogen if the normalized
(genus, species, strain) already exists.

Phase 2 - fill gram_stain from genus via the shared GRAM_STAIN_BY_GENUS map.

Dry-run by default; pass --apply to write. Back up the DB first.
"""
from django.core.management.base import BaseCommand
from django.db import IntegrityError, transaction

from synergy_data.models import Pathogen, SynergyExperiment
from synergy_data.views import derive_gram_stain

# Abbreviated genus -> full name. Only entries that are unambiguous in the
# current dataset. Keyed on lower-cased genus.
GENUS_EXPANSION = {
    "s.": "Staphylococcus",
}


class Command(BaseCommand):
    help = "Normalize abbreviated genera and backfill gram_stain from genus."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply", action="store_true",
            help="Write changes. Without this flag the command is a dry run.",
        )

    def handle(self, *args, **opts):
        apply = opts["apply"]

        # --- Phase 1: normalize abbreviated genera ---
        self.stdout.write("=== Phase 1: normalize abbreviated genera ===")
        norm = 0
        for p in list(Pathogen.objects.all()):
            full = GENUS_EXPANSION.get((p.genus or "").strip().lower())
            if not full or full == p.genus:
                continue
            norm += 1
            self.stdout.write(
                f"  [id {p.id}] '{p.genus} {p.species} {p.strain or ''}'".rstrip()
                + f" -> genus '{full}'"
            )
            if not apply:
                continue
            existing = (
                Pathogen.objects
                .filter(genus=full, species=p.species, strain=p.strain)
                .exclude(id=p.id).first()
            )
            if existing:
                # Re-point experiments to the existing pathogen, drop the dup.
                SynergyExperiment.objects.filter(pathogen=p).update(pathogen=existing)
                p.delete()
            else:
                p.genus = full
                try:
                    with transaction.atomic():
                        p.save()
                except IntegrityError:
                    self.stdout.write(self.style.WARNING(
                        f"     skipped [id {p.id}] - unique conflict on save"
                    ))
        self.stdout.write(f"  {norm} pathogen(s) flagged for genus normalization.")

        # --- Phase 2: backfill gram_stain ---
        self.stdout.write("\n=== Phase 2: backfill gram_stain from genus ===")
        filled = 0
        unknown = {}
        for p in Pathogen.objects.all():
            if (p.gram_stain or "").strip():
                continue
            gs = derive_gram_stain(p.genus)
            if gs:
                filled += 1
                self.stdout.write(f"  [id {p.id}] {p.genus} {p.species} -> {gs}")
                if apply:
                    p.gram_stain = gs
                    p.save(update_fields=["gram_stain"])
            else:
                unknown[p.genus] = unknown.get(p.genus, 0) + 1
        self.stdout.write(f"  {filled} pathogen(s) will get a gram_stain value.")
        if unknown:
            pretty = ", ".join(f"{g} ({n})" for g, n in sorted(unknown.items()))
            self.stdout.write(self.style.WARNING(
                f"  Unresolved genera (not in the map, left blank): {pretty}"
            ))

        if not apply:
            self.stdout.write(self.style.WARNING(
                "\nDRY RUN - nothing was changed. Re-run with --apply to write."
            ))
        else:
            self.stdout.write(self.style.SUCCESS("\nDone."))
