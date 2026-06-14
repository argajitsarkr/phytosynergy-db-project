"""Backfill Source.pmid from the DOI using NCBI E-utilities (esearch).

Runs offline (management command), never inside a web request - it makes one
external HTTP call per source and must not block a gunicorn worker.

Dry-run by default; pass --apply to write. NCBI allows ~3 requests/sec without
an API key, so we sleep between calls. Supplying --email is recommended by NCBI.
"""
import time

import requests
from django.core.management.base import BaseCommand

from synergy_data.models import Source

ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"


class Command(BaseCommand):
    help = "Backfill Source.pmid from DOI via NCBI E-utilities."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true",
                            help="Write PMIDs. Without this flag it is a dry run.")
        parser.add_argument("--sleep", type=float, default=0.4,
                            help="Seconds between NCBI requests (default 0.4).")
        parser.add_argument("--email", default="",
                            help="Contact email sent to NCBI (recommended).")

    def handle(self, *args, **opts):
        apply = opts["apply"]
        qs = (
            Source.objects
            .filter(pmid__isnull=True)
            .exclude(doi__isnull=True).exclude(doi="")
        )
        total = qs.count()
        self.stdout.write(f"{total} source(s) have a DOI but no PMID.\n")
        found = 0

        for s in qs:
            doi = (s.doi or "").strip()
            params = {"db": "pubmed", "term": f"{doi}[DOI]", "retmode": "json"}
            if opts["email"]:
                params["email"] = opts["email"]
            try:
                r = requests.get(ESEARCH_URL, params=params, timeout=10)
                ids = r.json().get("esearchresult", {}).get("idlist", [])
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"  {doi}: lookup failed ({e})"))
                time.sleep(opts["sleep"])
                continue

            if ids:
                pmid = int(ids[0])
                found += 1
                self.stdout.write(f"  {doi} -> PMID {pmid}")
                if apply:
                    s.pmid = pmid
                    try:
                        s.save(update_fields=["pmid"])
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f"    save failed: {e}"))
            else:
                self.stdout.write(f"  {doi} -> (no PMID found)")
            time.sleep(opts["sleep"])

        msg = f"\nResolved {found}/{total} PMID(s)."
        if not apply:
            msg += " DRY RUN - re-run with --apply to save."
        self.stdout.write(self.style.SUCCESS(msg))
