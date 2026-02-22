"""
Management command: import_data
================================
Bulk-imports synergy experiment data from a CSV file into PhytoSynergyDB.

Expected CSV columns (order does not matter, names are case-insensitive):
    source_doi              – DOI of the source publication (required)
    publication_year        – e.g. 2023
    journal                 – Journal name
    article_title           – Full article title
    pathogen_full_name      – e.g. "Pseudomonas aeruginosa MTCC 2488"
    gram_stain              – "Gram-positive" or "Gram-negative"
    phytochemical_name      – e.g. "Vitexin"
    antibiotic_name         – e.g. "Azithromycin"
    antibiotic_class        – e.g. "Macrolide"
    mic_phyto_alone         – numeric MIC value
    mic_abx_alone           – numeric MIC value
    mic_phyto_in_combo      – numeric MIC value
    mic_abx_in_combo        – numeric MIC value
    mic_units               – e.g. "µg/mL"
    fic_index               – numeric FIC value
    interpretation          – Synergy / Additive / Indifference / Antagonism
    moa_observed            – free-text mechanism of action notes
    notes                   – any other notes

Usage:
    python manage.py import_data path/to/your_data.csv
    python manage.py import_data path/to/your_data.csv --dry-run
    python manage.py import_data path/to/your_data.csv --skip-errors
"""

import csv
import re
from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from synergy_data.models import (
    AntibioticClass, Antibiotic, Phytochemical, Pathogen, Source, SynergyExperiment
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

INTERP_MAP = {
    'synergy':      'Synergy',
    'additive':     'Additive',
    'indifference': 'Indifference',
    'antagonism':   'Antagonism',
}


def normalise_header(name):
    """Lower-case, strip, collapse whitespace → underscores."""
    return re.sub(r'\s+', '_', name.strip().lower())


def to_decimal(value):
    """Convert a string to Decimal, return None if blank or unconvertable."""
    if value is None:
        return None
    value = str(value).strip()
    if not value or value in ('-', 'N/A', 'n/a', 'NA', 'nd', 'ND', '—'):
        return None
    try:
        return Decimal(value)
    except InvalidOperation:
        return None


def to_int(value):
    """Convert a string to int, return None if blank."""
    if value is None:
        return None
    value = str(value).strip()
    if not value:
        return None
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return None


def parse_pathogen(full_name):
    """
    Split a string like 'Pseudomonas aeruginosa MTCC 2488'
    into (genus, species, strain).
    """
    parts = full_name.strip().split()
    if len(parts) < 2:
        return full_name.strip(), '', ''
    genus = parts[0]
    species = parts[1]
    strain = ' '.join(parts[2:]) if len(parts) > 2 else ''
    return genus, species, strain


def normalise_interpretation(value):
    if not value:
        return None
    return INTERP_MAP.get(value.strip().lower())


# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------

class Command(BaseCommand):
    help = 'Import synergy experiment data from a CSV file.'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Path to the CSV file to import.')
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Parse and validate the file without saving anything to the database.',
        )
        parser.add_argument(
            '--skip-errors',
            action='store_true',
            help='Skip rows with errors instead of aborting the entire import.',
        )
        parser.add_argument(
            '--encoding',
            type=str,
            default='utf-8-sig',
            help='File encoding (default: utf-8-sig, handles Excel BOM).',
        )

    def handle(self, *args, **options):
        csv_path = options['csv_file']
        dry_run = options['dry_run']
        skip_errors = options['skip_errors']
        encoding = options['encoding']

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN — no data will be saved.\n'))

        try:
            with open(csv_path, newline='', encoding=encoding) as f:
                reader = csv.DictReader(f)
                # Normalise headers so column order / capitalisation doesn't matter
                reader.fieldnames = [normalise_header(h) for h in reader.fieldnames]
                rows = list(reader)
        except FileNotFoundError:
            raise CommandError(f'File not found: {csv_path}')
        except Exception as exc:
            raise CommandError(f'Could not read file: {exc}')

        self.stdout.write(f'Found {len(rows)} data rows. Starting import…\n')

        created = 0
        skipped = 0
        errors = 0

        with transaction.atomic():
            for i, row in enumerate(rows, start=2):   # row 1 is the header
                try:
                    created += self._import_row(row, dry_run)
                except Exception as exc:
                    msg = f'Row {i}: {exc}'
                    if skip_errors:
                        self.stderr.write(self.style.WARNING(f'  SKIPPED — {msg}'))
                        skipped += 1
                        errors += 1
                    else:
                        raise CommandError(
                            f'{msg}\n\nUse --skip-errors to continue past bad rows.'
                        )

            if dry_run:
                # Roll back everything — we just wanted validation
                transaction.set_rollback(True)

        self.stdout.write('\n' + '─' * 50)
        self.stdout.write(self.style.SUCCESS(f'  Created / updated : {created}'))
        if errors:
            self.stdout.write(self.style.WARNING(f'  Rows with errors  : {errors} (skipped)'))
        if dry_run:
            self.stdout.write(self.style.WARNING('  (dry-run — nothing was committed)'))
        self.stdout.write('─' * 50 + '\n')

    def _import_row(self, row, dry_run):
        """Process one CSV row. Returns 1 if a SynergyExperiment was created/updated, else 0."""

        # ---- Source ----
        doi = row.get('source_doi', '').strip() or None
        pub_year = to_int(row.get('publication_year', ''))
        journal = row.get('journal', '').strip() or None
        article_title = row.get('article_title', '').strip() or None

        if not doi and not article_title:
            raise ValueError('Row has neither a DOI nor an article title — cannot identify source.')

        if not dry_run:
            source, _ = Source.objects.get_or_create(
                doi=doi,
                defaults={
                    'publication_year': pub_year,
                    'journal': journal,
                    'article_title': article_title,
                },
            )
        else:
            source = None

        # ---- Pathogen ----
        pathogen_raw = row.get('pathogen_full_name', '').strip()
        if not pathogen_raw:
            raise ValueError('pathogen_full_name is required.')
        genus, species, strain = parse_pathogen(pathogen_raw)
        gram_stain = row.get('gram_stain', '').strip() or None

        if not dry_run:
            pathogen, _ = Pathogen.objects.get_or_create(
                genus=genus,
                species=species,
                strain=strain or None,
                defaults={'gram_stain': gram_stain},
            )
        else:
            pathogen = None

        # ---- Antibiotic Class (optional) ----
        abx_class_name = row.get('antibiotic_class', '').strip()
        abx_class_obj = None
        if abx_class_name and not dry_run:
            abx_class_obj, _ = AntibioticClass.objects.get_or_create(
                class_name=abx_class_name
            )

        # ---- Antibiotic ----
        abx_name = row.get('antibiotic_name', '').strip()
        if not abx_name:
            raise ValueError('antibiotic_name is required.')

        if not dry_run:
            antibiotic, _ = Antibiotic.objects.get_or_create(
                antibiotic_name=abx_name,
                defaults={'antibiotic_class': abx_class_obj},
            )
            # Update class if it was missing before
            if abx_class_obj and antibiotic.antibiotic_class is None:
                antibiotic.antibiotic_class = abx_class_obj
                antibiotic.save(update_fields=['antibiotic_class'])
        else:
            antibiotic = None

        # ---- Phytochemical ----
        phyto_name = row.get('phytochemical_name', '').strip()
        if not phyto_name:
            raise ValueError('phytochemical_name is required.')

        if not dry_run:
            phytochemical, _ = Phytochemical.objects.get_or_create(
                compound_name=phyto_name
            )
        else:
            phytochemical = None

        # ---- MIC values ----
        mic_phyto_alone    = to_decimal(row.get('mic_phyto_alone', ''))
        mic_abx_alone      = to_decimal(row.get('mic_abx_alone', ''))
        mic_phyto_in_combo = to_decimal(row.get('mic_phyto_in_combo', ''))
        mic_abx_in_combo   = to_decimal(row.get('mic_abx_in_combo', ''))
        mic_units          = row.get('mic_units', 'µg/mL').strip() or 'µg/mL'
        fic_index          = to_decimal(row.get('fic_index', ''))
        interpretation     = normalise_interpretation(row.get('interpretation', ''))
        moa_observed       = row.get('moa_observed', '').strip() or None
        notes              = row.get('notes', '').strip() or None

        if dry_run:
            # Validate interpretation value if present
            if row.get('interpretation', '').strip() and interpretation is None:
                raw = row.get('interpretation', '').strip()
                raise ValueError(
                    f'Unknown interpretation value "{raw}". '
                    f'Expected one of: Synergy, Additive, Indifference, Antagonism.'
                )
            self.stdout.write(f'  OK  {phyto_name} + {abx_name} vs {pathogen_raw}')
            return 1

        # ---- SynergyExperiment ----
        SynergyExperiment.objects.create(
            phytochemical=phytochemical,
            antibiotic=antibiotic,
            pathogen=pathogen,
            source=source,
            mic_phyto_alone=mic_phyto_alone,
            mic_abx_alone=mic_abx_alone,
            mic_phyto_in_combo=mic_phyto_in_combo,
            mic_abx_in_combo=mic_abx_in_combo,
            mic_units=mic_units,
            fic_index=fic_index,
            interpretation=interpretation,
            moa_observed=moa_observed,
            notes=notes,
        )

        self.stdout.write(f'  +   {phyto_name} + {abx_name} vs {pathogen_raw}')
        return 1
