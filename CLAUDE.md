# CLAUDE.md - PhytoSynergyDB Project Guide

> **READ THIS BEFORE MAKING ANY CHANGES.**
> Update this file after every session with a summary of changes made and any new lessons learned.

---

## Project Overview

**App:** PhytoSynergyDB - curated database of phytochemical-antibiotic synergy experiments against ESKAPE pathogens.
**Stack:** Django 4.2 LTS · PostgreSQL 15 · Gunicorn · Nginx · Docker Compose · Cloudflare Tunnel
**Host:** Dell PowerEdge R730, 84 GB RAM (self-hosted, public domain `https://phytosynergydb.in`)
**Repo:** `https://github.com/argajitsarkr/phytosynergy-db-project.git`
**Active branch:** `main` (only branch; `color-palette-redesign` was merged & deleted on 2026-04-30)
**Server path:** `/home/mmilab/Desktop/Database/phytosynergy-project/` (NOT `~/phytosynergy-db-project`)
**Local dev machine git root:** `D:\Sites\Projects` (this varies by machine/user - a prior revision of this file said `C:\Users\Arghya\Downloads\Projects\`, which is stale; always confirm with `git rev-parse --show-toplevel` rather than trusting a hardcoded path here)

---

## CURRENT STATE - READ THIS FIRST (as of 2026-08-13)

> Snapshot of what is committed vs. actually live, and what is half-finished.
> **Update or delete this section as items are closed.** If something on the site
> looks broken, start here before digging.

### Deploy status
`main` is at `7d33771`. Six commits landed on 2026-08-13 and, unless the maintainer
has since run the deploy, **they are on GitHub but NOT on the server**. The server
serves code baked into the `web` image, so nothing is live until a rebuild (rule #7).

Deploying all of them at once needs the FULL sequence, because the batch includes a
`requirements.txt` change (django-axes), a new migration, and CSS changes:
```bash
cd ~/Desktop/Database/phytosynergy-project && git pull origin main \
  && docker compose build --no-cache web && docker compose up -d web \
  && docker compose exec web python manage.py migrate \
  && docker compose exec web python manage.py collectstatic --noinput \
  && docker compose restart nginx
```
Then verify: `docker compose exec nginx nginx -t`, log in successfully, confirm
`/analytics/` charts draw and the `/database/` 3D viewer renders (the SRI canaries),
and open the `/database/` filter dropdowns.

### What each of today's commits can break, and how to back it out
| Commit | Risk if it misbehaves | Revert |
|--------|----------------------|--------|
| `7d33771` axes + rate limiting | Lockouts or 429s. Highest-risk change of the day; NOT tested. | `git revert 7d33771` (also needs a `--no-cache` rebuild) |
| `fd8b08e` SRI | Blank analytics charts / dead 3D viewer = a wrong hash (see rule #12) | `git revert fd8b08e` |
| `fa1fde3` + `a75567e` search filters | Filter row visually wrong, or dropdowns not applying | `git revert a75567e fa1fde3` restores native selects |
| `441604e` social links removed | Cosmetic only | `git revert 441604e` |
| `f359abb` stats band colour | Cosmetic only | `git revert f359abb` |

### Open items (NOT done)
1. **Committed secrets - highest priority.** `docker-compose.yml` still contains the live
   `POSTGRES_PASSWORD` and `DJANGO_SECRET_KEY` in plaintext, and they are in git history
   from `d92ae84` onward. **The repo is currently PUBLIC**, so both must be treated as
   compromised. Maintainer's decision: rotate the credentials, then make the repo private
   (no history rewrite). `.env` is already in `.gitignore` but is not used by anything yet.
2. **Going private will break the SERVER's `git pull`.** A public repo pulls anonymously;
   a private one does not. The server needs a read-only deploy key (SSH) and its remote
   switched to the SSH URL BEFORE the visibility flip, or deploys stop working. The laptop
   is unaffected - pushing already requires authentication.
3. **Footer "Contact" link is dead.** `base.html` links to `{% url 'about' %}#contact`, but
   no `id="contact"` exists in `about.html` (that section was removed 2026-05-16).
4. **Footer email is a plain-text `mailto:`** to a personal Gmail - it will be harvested.
5. **CSP not implemented.** Considered and deferred; would need report-only mode first
   because of the volume of inline JS.
6. **Dead paint-bug workarounds.** The `translateZ`/`will-change` hacks and the
   `display:none`/`offsetHeight` repaint script in `base.html` were chasing a bug that did
   not exist (see the `f359abb` entry). Safe to strip in their own commit.

### Dev-machine constraint that shapes everything
This laptop has **only Python 2.7 (MGLTools)** on PATH - no Python 3, no Django, no RDKit -
and the browser tooling is policy-blocked for `phytosynergydb.in`. So `manage.py check`,
`migrate`, `collectstatic` and any page render CANNOT be run here; they happen in Docker on
the server. Everything is verified by inspection only, which is exactly how `a75567e`
shipped broken. Treat any template/config change as UNVERIFIED until seen on the live site.

---

## Repository Layout

```
<git root>                               ← confirm actual path with `git rev-parse --show-toplevel`
├── manage.py
├── requirements.txt                    ← add packages here; rebuild Docker after changes
├── Dockerfile                          ← Python 3.12-slim; gunicorn CMD here
├── docker-compose.yml                  ← db / web / nginx / tunnel services
├── nginx.conf                          ← proxy pass to gunicorn:8000
├── Procfile                            ← Heroku-style; not used in Docker deploy
├── phytosynergy_project/
│   ├── settings.py                     ← env-var driven; DATABASE_URL / SECRET_KEY / DEBUG / STORAGES
│   ├── urls.py                         ← includes synergy_data.urls
│   ├── storages.py                     ← StableManifestStaticFilesStorage (content-hashed static in prod)
│   └── wsgi.py
├── synergy_data/                       ← the only Django app
│   ├── models.py                       ← AntibioticClass · Phytochemical · Antibiotic
│   │                                      Pathogen · Source · SynergyExperiment · Plant
│   ├── views.py                        ← all views + helper functions
│   ├── forms.py                        ← SynergyEntryForm · BulkCSVUploadForm
│   │                                      BULK_CSV_COLUMNS · COLUMN_MAP · _canonical_header
│   ├── urls.py                         ← URL routing (see table below)
│   ├── pubchem_utils.py                ← PubChem + ClassyFire HTTP enrichment
│   ├── similarity.py                   ← RDKit fingerprint/Tanimoto logic (lazy RDKit import)
│   ├── seo_views.py                    ← robots.txt / sitemap.xml / llms.txt hand-rolled views
│   ├── context_processors.py           ← view_counter (injected into all templates)
│   ├── admin.py
│   ├── tests.py
│   ├── management/commands/
│   │   ├── enrich_phytochemicals.py    ← offline PubChem/ClassyFire backfill
│   │   ├── compute_properties.py       ← RDKit cheminformatics batch compute
│   │   ├── compute_fingerprints.py     ← backfill Morgan/ECFP4 fingerprints for similarity search
│   │   ├── prune_non_eskape.py         ← delete out-of-scope (non-ESKAPE) experiments; dry-run by default, --apply to write
│   │   ├── backfill_gram_stain.py      ← normalize abbreviated pathogen genera + backfill gram_stain; dry-run by default, --apply to write
│   │   └── backfill_pmid.py            ← backfill Source.pmid from DOI via NCBI E-utilities; dry-run by default, --apply to write
│   ├── templates/synergy_data/
│   │   ├── base.html                   ← Plus Jakarta Sans, Bootstrap 5, blue palette
│   │   ├── home.html · about.html · login.html
│   │   ├── database_search.html · download.html
│   │   ├── data_entry.html · bulk_import.html
│   │   ├── similarity_search.html
│   │   └── analytics.html · api_docs.html
│   ├── static/                         ← app-level static assets
│   └── templatetags/analytics_filters.py  ← heatmap_color (analytics) + chem_class_color (result-card class chips)
├── staticfiles/                        ← collectstatic output (do NOT edit manually)
├── scripts/                             ← operational shell scripts (server-side; not run from Docker)
│   ├── deploy.sh                       ← safe deploy: pre-deploy backup, git pull, rebuild web, migrate, collectstatic, health check, auto-info for rollback (`deploy.sh rollback`)
│   ├── backup_db.sh                    ← pg_dump -> gzip into ~/phytosynergy_backups/; daily/pre-deploy/manual tags; keeps last 30 daily backups
│   ├── restore_db.sh                   ← restore a backup produced by backup_db.sh
│   └── setup_cron.sh                   ← one-time cron install for a 2 AM daily backup_db.sh run
├── phytosynergydb-worker/               ← Cloudflare Worker passthrough (maintenance-page redirect on origin-down); NOT yet deployed as of the 2026-06-12 changelog entry - confirm current status before relying on it
├── CHANGELOG.md                        ← curated history of all features
├── DEPLOYMENT.md                       ← step-by-step server deploy guide
├── DEVELOPMENT.md, SCHEMA.md, SITE_REPORT.md, TECHNICAL_SHEET.md, README.md  ← supporting docs, not covered in detail by this file
└── CLAUDE.md                           ← this file
```

---

## URL Map

| URL | View | Auth | Notes |
|-----|------|------|-------|
| `/` | `home_page` | Public | Stats counters, ESKAPE summary |
| `/database/` | `database_search_page` | Public | Filterable experiment table (also accepts `?phytochemical=<id>`) |
| `/database/download/` | `download_data` | Public | CSV export of filtered results |
| `/similarity/` | `similarity_search_page` | Public | SMILES -> Tanimoto/ECFP4 structural similarity search |
| `/about/` | `about_page` | Public | |
| `/data-entry/` | `data_entry_view` | Login | Single-row form; calls `enrich_phytochemical` on save |
| `/data-entry/edit/<pk>/` | `edit_entry_view` | Login | |
| `/bulk-import/` | `bulk_import_view` | Login | CSV/XLSX import (see section below) |
| `/bulk-import/template/` | `bulk_import_template` | Login | Downloads XLSX template |
| `/analytics/` | `analytics_page` | Public | Chart.js dashboard |
| `/api/v1/experiments/` | `api_experiments` | Public | JSON, paginated, filterable |
| `/api/v1/statistics/` | `api_statistics` | Public | Aggregate stats JSON |
| `/api/v1/similarity/` | `api_similarity` | Public | JSON, `?smiles=` Tanimoto/ECFP4 ranking |
| `/api/docs/` | `api_docs` | Public | |
| `/accounts/login/` | Django `LoginView` | - | Template: `synergy_data/login.html` |
| `/accounts/logout/` | Django `LogoutView` | - | Redirects to `home` |

---

## Data Model (key fields)

```
SynergyExperiment
  ├── phytochemical → Phytochemical (compound_name, pubchem_cid, smiles, Lipinski, ClassyFire, morgan_fp)
  ├── antibiotic    → Antibiotic (antibiotic_name, antibiotic_class → AntibioticClass)
  ├── pathogen      → Pathogen (genus, species, strain)  unique_together on all three
  ├── source        → Source (doi, pmid, publication_year, article_title, journal)
  ├── mic_phyto_alone / mic_abx_alone / mic_phyto_in_combo / mic_abx_in_combo (Decimal, nullable)
  ├── mic_units (default µg/mL)
  ├── fic_index (Decimal, nullable) - auto-calculated if all 4 MICs present
  ├── interpretation (Synergy / Additive / Indifference / Antagonism) - auto-derived from FIC
  ├── assay_method (checkerboard / time_kill / disk_diffusion / broth_microdilution / other)
  ├── moa_observed (TextField, nullable)
  └── notes (TextField, nullable)
```

**FIC thresholds:** ≤0.5 Synergy · ≤1.0 Additive · ≤4.0 Indifference · >4.0 Antagonism

---

## Bulk Import (`/bulk-import/`) - Critical Rules

### What it does
Accepts `.csv` or `.xlsx` uploads. Phase 1 parses and shows a colour-coded preview (green/yellow/red). Phase 2 (confirm) imports all non-error rows.

### IMPORTANT: PubChem enrichment is NOT called during bulk import
Calling `enrich_phytochemical()` per row inside the request makes **~46 s of HTTP calls per row** and freezes the whole site with 1 gunicorn worker. It was removed (commit `71263e3`).

**After every bulk import, run the offline backfill:**
```bash
docker compose exec web python manage.py enrich_phytochemicals
```

### Data cleaning applied automatically
- Literal `null`, `N/A`, `ND`, `NR`, `--`, empty cells → Python `None`
- `Âµg/mL`, `Î¼g/mL` → `µg/mL` (encoding corruption repair)
- Decimal ranges `32-64` → `64` (upper bound); inequalities `>256` → `256`
- Duplicate experiments (same phyto + abx + pathogen + source) are skipped, counted separately

### Each row is wrapped in `transaction.atomic()`
A failure on any row rolls back only that row - no orphan FK records, no partial state.

### Column aliases (COLUMN_MAP in `forms.py`)
The import recognises common variants: `doi` → `source_doi`, `fic` → `fic_index`, `compound` → `phytochemical_name`, `antibiotic` → `antibiotic_name`, `mechanism` → `moa_observed`, etc. Full map in `synergy_data/forms.py`.

---

## Key Helper Functions in `views.py`

| Function | Purpose |
|----------|---------|
| `parse_pathogen_name(full_name)` | Splits `"Staphylococcus aureus 03"` → `("Staphylococcus", "aureus", "03")` |
| `auto_calculate_fic(...)` | `(mic_phyto_combo / mic_phyto_alone) + (mic_abx_combo / mic_abx_alone)` - returns None if any value is zero/None |
| `auto_interpret_fic(fic)` | Maps FIC float → `"Synergy"` / `"Additive"` / etc. |
| `get_or_create_case_insensitive(model, field, value)` | Race-condition-safe iexact lookup with IntegrityError fallback |
| `_clean_value(value, field_type)` | Strips null strings, fixes encoding, handles ranges/inequalities |
| `_parse_upload_to_rows(file)` | Reads CSV or XLSX → list of canonical-keyed dicts |
| `_stage_row(row_num, raw_row)` | Validates + classifies a single row as valid / warning / error |
| `_apply_search_filters(qs, request)` | Applies GET params (query, pathogen_id, interpretation, ESKAPE, chemical_class) to a queryset |

---

## Management Commands

```bash
# Backfill PubChem + ClassyFire data for compounds missing it (run after bulk imports)
docker compose exec web python manage.py enrich_phytochemicals

# Force re-enrich all compounds
docker compose exec web python manage.py enrich_phytochemicals --all

# Enrich a single compound
docker compose exec web python manage.py enrich_phytochemicals --name "Berberine"

# Batch-compute RDKit cheminformatics properties (logP, rings, Lipinski, etc.)
docker compose exec web python manage.py compute_properties

# Compute + store Morgan/ECFP4 fingerprints for chemical similarity search
# (only compounds missing a fingerprint; run after every import/enrich cycle)
docker compose exec web python manage.py compute_fingerprints

# Force re-fingerprint everything, or just one compound
docker compose exec web python manage.py compute_fingerprints --all
docker compose exec web python manage.py compute_fingerprints --name "Berberine"

# Delete out-of-scope (non-ESKAPE) synergy experiments. Dry-run by default (prints
# what would be deleted); pass --apply to actually delete. Back up the DB first.
docker compose exec web python manage.py prune_non_eskape
docker compose exec web python manage.py prune_non_eskape --apply
docker compose exec web python manage.py prune_non_eskape --apply --clean-orphan-phyto

# Normalize abbreviated pathogen genera (e.g. "S." -> "Staphylococcus") and backfill
# Pathogen.gram_stain from genus for older rows. Dry-run by default; pass --apply to write.
docker compose exec web python manage.py backfill_gram_stain
docker compose exec web python manage.py backfill_gram_stain --apply

# Backfill Source.pmid from DOI via NCBI E-utilities (esearch). Offline only - makes
# one external HTTP call per source, never run inside a web request. Dry-run by
# default; pass --apply to write. NCBI allows ~3 req/sec without an API key.
docker compose exec web python manage.py backfill_pmid
docker compose exec web python manage.py backfill_pmid --apply --email "you@example.com"
```

---

## Chemical Similarity Search (`/similarity/`)

A researcher pastes a SMILES string and gets the structurally most similar
phytochemicals in the DB, ranked by **Tanimoto similarity** on 2048-bit
**Morgan / ECFP4** fingerprints (radius 2). Each hit links to its recorded
synergy experiments via `database/?phytochemical=<id>`.

- **Fingerprints are precomputed at curation time** and stored on
  `Phytochemical.morgan_fp` (a 2048-char bit string). They are written by
  `manage.py compute_fingerprints` and refreshed on save in `data_entry_view` /
  `edit_entry_view` (via `similarity.update_fingerprint`). Bulk import does NOT
  fingerprint (same no-network-in-request rule as enrichment) - run the command
  after importing.
- All fingerprint/Tanimoto logic lives in `synergy_data/similarity.py`. RDKit is
  imported lazily there so the app still boots if RDKit is missing; the query
  path then returns a clear "RDKit not installed" error instead of crashing.
- The query view falls back to computing a compound's fingerprint live from its
  SMILES when `morgan_fp` is blank, so search works even before the backfill is run.
- JSON API: `GET /api/v1/similarity/?smiles=<SMILES>&limit=25&threshold=0.4`.

---

## Correct Workflow for Making Changes

1. **Read this file first**
2. Edit files inside the git root (confirm the path with `git rev-parse --show-toplevel` - it varies by machine, see the note under Project Overview)
3. Run `python manage.py check` to catch Django-level errors before committing
4. Stage specific files - **NEVER `git add .`** (the root contains personal files)
5. Commit and push:
   ```bash
   git add <specific files>
   git commit -m "descriptive message"
   git push origin main
   ```
6. Deploy on the server (see **Deploy Workflow** below)
7. Update the **Changelog** section at the bottom of this file

---

## Deploy Workflow (on the server)

> **Server project path:** `/home/mmilab/Desktop/Database/phytosynergy-project/`
> **CRITICAL:** The Django source code is BAKED INTO the `web` Docker image at build time (no bind-mount). `git pull` updates the host filesystem but NOT the running container. Every code change requires a rebuild - `docker compose restart web` alone will keep serving the OLD code.

```bash
cd ~/Desktop/Database/phytosynergy-project
git pull origin main

# ALWAYS rebuild the web image after a pull (code is baked in, not mounted):
docker compose build web
docker compose up -d web
docker compose exec web python manage.py collectstatic --noinput
docker compose restart nginx

# If requirements.txt or Dockerfile changed, force a clean rebuild:
docker compose build --no-cache web
docker compose up -d web

# Verify:
docker compose ps                      # all four services should be Up
docker compose logs --tail=50 web      # check for startup errors
docker compose exec web head -5 /app/staticfiles/synergy_data/css/custom.css   # confirm new CSS landed
```

**Data safety:** `docker compose build` and `docker compose up -d web` do NOT touch the `db` container or its volume. PostgreSQL data persists in a named volume independent of containers/images. Only `docker compose down -v` or `docker volume rm` would wipe the database. Optional pre-deploy backup:
```bash
docker compose exec db pg_dump -U <db_user> phytosynergy_db > ~/phytosynergy_backup_$(date +%F).sql
```

**After any bulk import:**
```bash
docker compose exec web python manage.py enrich_phytochemicals   # backfill PubChem/ClassyFire + SMILES
docker compose exec web python manage.py compute_fingerprints    # backfill ECFP4 fingerprints for similarity search
```

> **NOTE:** The similarity-search feature adds migration `0006_phytochemical_morgan_fp`. On first deploy of that change run `docker compose exec web python manage.py migrate` and then `compute_fingerprints` once to fingerprint the existing compounds.

**If the site freezes / gunicorn gets wedged:**
```bash
docker compose logs --tail=300 web     # look for [CRITICAL] WORKER TIMEOUT
docker compose restart web             # nginx + db stay up; only web restarts
```

---

## Environment Variables (set in `docker-compose.yml`)

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | Postgres connection string - `postgres://user:pass@db:5432/phytosynergy_db` |
| `DJANGO_SECRET_KEY` | Django secret key |
| `DEBUG` | `0` for production, `1` for dev |
| `ALLOWED_HOSTS` | Comma-separated; include `phytosynergydb.in`, `www.phytosynergydb.in`, server IP, `localhost`, `127.0.0.1` |
| `CSRF_TRUSTED_ORIGINS` | Must include `https://phytosynergydb.in,https://www.phytosynergydb.in` |
| `SECURE_HSTS_SECONDS` | `31536000` in production (enabled now that the domain is dedicated) |

---

## ❌ MISTAKES LOG - What NOT To Do

### 1. NEVER call `enrich_phytochemical()` inside a request that processes multiple rows
- **What happened (2026-04-17):** 30-row XLSX import triggered ~46 s of PubChem/ClassyFire HTTP calls per row inside the gunicorn worker. Single worker blocked → site froze for all users for ~23 minutes.
- **Fix:** Removed the enrichment call from `bulk_import_view`; runs offline via `manage.py enrich_phytochemicals` instead.
- **Rule:** Any operation that makes unbounded external HTTP calls MUST run in a management command or background worker, never inside a Django view handling a user request.

### 2. NEVER run gunicorn with default 1 worker in production
- **What happened:** One blocked worker = entire site unreachable.
- **Fix:** Added `--workers 3 --timeout 120 --access-logfile - --error-logfile -` to the `Dockerfile` CMD.
- **Rule:** Always set `--workers` explicitly. Rule of thumb: `2 × CPU_count + 1`.

### 3. NEVER use `git add .` or `git add -A` from the project root without checking `git status` first
- The working directory is inside `C:\Users\Arghya\Downloads\Projects\` - check `git status` carefully before staging.

### 4. ALWAYS wrap multi-step DB operations in `transaction.atomic()`
- Without it, a partially-completed loop leaves orphan FK records that are hard to clean up.

### 5. If you add a new Python package, rebuild the Docker image
- `requirements.txt` changes are only picked up on `docker compose build --no-cache web`.
- `docker compose restart web` does NOT reinstall packages.

### 6. HARD RULE - NEVER use em dashes (—) ANYWHERE
- **Rule:** The em dash character `—` (U+2014) is BANNED in this project. Always use a plain ASCII hyphen `-` instead. No exceptions.
- **Applies to:** EVERY file and EVERY surface - HTML templates, CSS, Python source, JS, Markdown, CLAUDE.md, CHANGELOG.md, DEPLOYMENT.md, commit messages, PR descriptions, page copy, button labels, comments, docstrings, alt text, meta tags, error messages, and any user-facing text rendered on the site.
- **Also banned:** the en dash `–` (U+2013) - use `-` for ranges too (e.g. `32-64`, not `32–64`).
- **Why:** Em dashes break grep, look like AI-generated output, and have caused encoding corruption in CSV/XLSX uploads.
- **How to check before committing:**
  ```bash
  grep -rn $'—\|–' --include="*.py" --include="*.html" --include="*.css" --include="*.md" --include="*.js" .
  ```
  Should return zero results. If anything matches, replace with `-` before committing.

### 7. CRITICAL - Code is baked into the Docker image; `restart` does NOT pick up new code
- **What happened (2026-04-30):** After `git pull` on the server, ran `docker compose restart web` and the navbar redesign did not appear. The web container had been running for 13 days off an image built before the pull. `git pull` updated the host source but the container kept serving its baked-in copy.
- **Fix:** Always `docker compose build web && docker compose up -d web` after a pull. `restart` only restarts the same image.
- **Rule:** ANY code/template/static change requires `build` + `up -d`, plus `collectstatic` for static files. See Deploy Workflow above.

### 8. After deploying static file changes, always run `collectstatic` AND restart nginx
- nginx serves CSS/JS from the `staticfiles/` volume populated by `collectstatic`.
- Skipping `collectstatic` means nginx keeps serving the old CSS even with a freshly-built web image.
- Run `docker compose exec web python manage.py collectstatic --noinput && docker compose restart nginx` after every static asset change.

### 8b. Static files are CONTENT-HASHED in production - do NOT advise a manual Cloudflare purge for CSS/JS anymore
- **As of 2026-06-25:** prod uses `STORAGES` -> `phytosynergy_project.storages.StableManifestStaticFilesStorage` (a `ManifestStaticFilesStorage` subclass with `manifest_strict = False`). `collectstatic` emits content-hashed names (`custom.<hash>.css`) and `{% static %}` renders the hashed URL, so a changed file gets a brand-new URL no cache has seen. Browsers AND the Cloudflare edge therefore CANNOT serve a stale copy - the old manual "Purge Everything after collectstatic" step (see the 2026-06-13 favicon GOTCHA) is **no longer needed for static assets**.
- **The one standing requirement:** `collectstatic` MUST run on every deploy (already in the Deploy Workflow). Storage is gated on DEBUG: prod (DEBUG=0) = hashed; local runserver (DEBUG=1) = plain `StaticFilesStorage`, so dev works without collectstatic.
- **GOTCHA - `collectstatic` is now STRICT about CSS `url()` refs:** if `custom.css` (or any collected CSS) references `url(...)` to a file that does not exist, `collectstatic` post-processing HARD-FAILS the deploy. Before adding a new `url()` (background image, font, etc.), make sure the target exists in `static/`. Absolute `https://` URLs and `data:` URIs are skipped (fine). The only local ref today is `../images/hero_background-green.jpg`.
- Orphan files like `custom_<random>.css` in `staticfiles/` are harmless leftovers from earlier collectstatic runs (Django collision-rename); clear them any time with `collectstatic --noinput --clear`.

### 9. Server project path is NOT what CLAUDE.md said before
- **Real path:** `/home/mmilab/Desktop/Database/phytosynergy-project/`
- **Wrong path** previously documented: `~/phytosynergy-db-project` (does not exist on the server).

### 10. PhytoSynergyDB is a CLOSED, EXPERT-CURATED database - no public submissions
- **Rule:** PhytoSynergyDB is maintained in-house by the authoring team. Public users have **read-only** access (search, download, REST API). The Data Entry and Bulk Import views exist for internal curators only and are gated behind `@login_required`.
- **What this means for UI copy:** NEVER add user-facing text that invites the general public to contribute, submit, or upload data. No "Contribute Data" buttons, no "How can I contribute?" FAQs, no community-submission CTAs anywhere on the public site (home, about, footer, API docs, etc.).
- **Acceptable language:** describe the resource as "curated", "expert-curated", or "manually extracted from peer-reviewed literature by the authors". Do not describe it as "community-contributed" or "crowd-sourced".
- **Where to check before committing:** about.html, home.html, base.html (footer), and `home_page` / `about_page` view contexts (FAQ entries). Grep for `contribut`, `submit your`, `community`, `crowd` and rephrase any matches.

### 11. NEVER write a multi-line Django `{# ... #}` comment - it leaks onto the page
- **What happened (2026-08-13):** the new searchable filter dropdowns were introduced with an 7-line explanatory `{# ... #}` comment in `database_search.html`. Django's hash-comment lexer matches on a SINGLE line only, so the whole block was emitted as literal text and appeared on the live search page. It also contained the literal text `<select>`, which the browser then parsed as a REAL empty select element - that swallowed the surrounding markup and destroyed the filter-row grid. The page shipped visibly broken.
- **Rule:** `{# ... #}` is single-line ONLY. For anything spanning more than one line use `{% comment %} ... {% endcomment %}`. Never put raw HTML tag text inside a template comment either - if the comment ever leaks, the browser will parse those tags.
- **How to check before committing:**
  ```bash
  python -c "
  import glob
  for f in glob.glob('synergy_data/templates/synergy_data/*.html'):
      for i,l in enumerate(open(f).read().split('\n'),1):
          if '{#' in l and '#}' not in l: print(f,'line',i)
  "
  ```
  Should print nothing.
- **Bigger lesson:** this shipped because the change was verified by inspection only (no Python 3/Django on the dev machine, Browser pane policy-blocked for the live domain). Structural greps confirmed balanced `{% for %}`/`{% if %}`/`<div>` tags and caught nothing, because the markup WAS balanced - the defect was in the templating layer. Grep-level checks cannot substitute for rendering the page. Any template change that cannot be rendered locally must be treated as unverified and looked at immediately after deploy.

### 12. NEVER derive an SRI hash by piping curl through a shell variable
- **What happened (2026-08-13):** computing the `integrity=` hash for `chart.umd.min.js` with `h=$(curl -sL URL)` then hashing `$h` produced a hash of 205888 bytes instead of the true 205889. Command substitution `$(...)` STRIPS TRAILING NEWLINES, and that file ends in one. The two other assets happened to match only because they do not end in a newline.
- **Why it matters:** a wrong SRI hash fails SILENTLY. The browser simply refuses to execute the asset - no Django error, no 500, nothing in `docker compose logs`. The analytics charts and the 3D viewer would just be blank.
- **Rule:** always download to a FILE and hash the file:
  ```bash
  curl -sL -o /tmp/asset URL && openssl dgst -sha384 -binary /tmp/asset | openssl base64 -A
  ```
  Confirm the byte count looks right and, ideally, that two downloads are `cmp`-identical.
- **After deploying any SRI change, check the canaries:** `/analytics/` charts must draw and the 3D viewer modal on `/database/` must render a molecule.
- Bootstrap is exempt: `django-bootstrap-v5` renders its own CDN tags WITH integrity already, and there is no `BOOTSTRAP5` override in settings.py.

### 13. This app is behind a proxy - NEVER key a lockout or rate limit on the client IP
- **The trap:** traffic arrives Cloudflare -> `cloudflared` container -> nginx -> gunicorn. So `$remote_addr` in nginx, and `REMOTE_ADDR` in Django, are the PROXY's address on every single request. Anything keyed on them treats the entire internet as ONE client.
- **What that would cause:** `limit_req_zone $binary_remote_addr` throttles all visitors together as if they were a single abuser. `AXES_LOCKOUT_PARAMETERS = ['ip_address']` means 5 bad logins by anyone lock out EVERY curator at once. Both are self-inflicted denial of service, and both are the "obvious" default configuration.
- **What is actually configured (2026-08-13):** nginx resolves `$limit_key` through two `map`s - `CF-Connecting-IP` -> `X-Forwarded-For` -> `$remote_addr`. django-axes locks on `username` ONLY; `AXES_IPWARE_META_PRECEDENCE_ORDER` resolves the real IP for the AUDIT LOG but is deliberately not used for lockout decisions.
- **Also remember:** a matched prefix `location` in nginx does NOT inherit from `location /`. The rate-limited blocks (`/accounts/login/`, `/admin/`, `/api/v1/`) each repeat all four `proxy_set_header` lines. Dropping `X-Forwarded-Proto` there would break Django's HTTPS detection on exactly the login page.
- **Escape hatches if a lockout goes wrong:** `manage.py axes_reset_username <name>` for one account, `manage.py axes_reset` to clear everything.

---

## Typography (Navbar - GrantSetu style)

The navigation bar uses the same font stack as the GrantSetu project for visual consistency:

| Element | Font | Source |
|---------|------|--------|
| Brand wordmark (`.navbar-brand`) | **Inter** weight 900, uppercase | Google Fonts CDN |
| Nav links, dropdown items, login button | **Roboto Mono** weight 600-700, uppercase, 13px, letter-spacing 0.06em | Google Fonts CDN |
| Body / headings (rest of site) | Plus Jakarta Sans | Google Fonts CDN |

CSS variables defined in `synergy_data/static/synergy_data/css/custom.css`:
```css
--font-nav-mono:    'Roboto Mono', ui-monospace, SFMono-Regular, Menlo, monospace;
--font-nav-display: 'Inter', system-ui, sans-serif;
```
Imported via the single Google Fonts URL at the top of `custom.css`. Do NOT add separate `<link>` tags in templates - keep all font loading in CSS.

**Navbar visual spec (matches GrantSetu):**
- 72 px tall, sticky top, white background
- 2 px solid black bottom border
- Brand: black uppercase Inter 900
- Links: black Roboto Mono 600 uppercase 13px, hover -> red (`var(--primary)`)
- Dropdown: 2px black border, rounded 12px, shadow
- Login button: 2px black border, hover fills black

---

## Changelog

| Date | Commit | Description |
|------|--------|-------------|
| 2026-08-13 | `7d33771` | **Security: brute-force lockout (django-axes) + nginx rate limiting.** Both `/accounts/login/` and `/admin/` previously accepted UNLIMITED login attempts, and the public `/api/v1/` had no rate limit at all. ADDED: `django-axes>=6.3,<7.0` to requirements.txt; `'axes'` in INSTALLED_APPS; `axes.middleware.AxesMiddleware` LAST in MIDDLEWARE (it must see the auth outcome); `AUTHENTICATION_BACKENDS` with `axes.backends.AxesStandaloneBackend` FIRST then the stock ModelBackend. Defaults: 5 failures, 1 hour cooloff, reset on success, all env-overridable (`AXES_FAILURE_LIMIT`, `AXES_COOLOFF_TIME_HOURS`). **THE KEY DECISION - `AXES_LOCKOUT_PARAMETERS = ['username']`, deliberately NOT ip_address.** This stack is cloudflared -> nginx -> gunicorn, so unless the real client IP is resolved perfectly EVERY request looks like it comes from the proxy; locking on ip_address there means 5 bad logins by anyone locks out every curator simultaneously - a self-inflicted DoS. Username locking cannot do that. Trade-off accepted: someone can deliberately lock a known username for the cooloff window, which with a handful of internal curators is much the lesser risk. `AXES_IPWARE_META_PRECEDENCE_ORDER` (CF-Connecting-IP -> X-Forwarded-For -> REMOTE_ADDR) is set so the audit log records the true IP, but it is NOT used for lockout decisions. NGINX: the same proxy-IP trap applies to `limit_req` - keying a zone on `$remote_addr`/`$binary_remote_addr` would treat the entire internet as ONE client and throttle all visitors together, so two `map`s resolve `$limit_key` from CF-Connecting-IP -> X-Forwarded-For -> $remote_addr. Zones: `login_zone` 10r/m burst 5 nodelay on `/accounts/login/` and `/admin/`; `api_zone` 60r/m burst 20 nodelay on `/api/v1/`; `limit_req_status 429`. NOTE these three `location` blocks must be declared BEFORE `location /` and each REPEATS the four proxy_set_header lines, because a matched prefix location does NOT inherit from `location /` - dropping those headers would break Django's HTTPS detection on exactly the login page. Verified: nginx braces 10/10, location order correct, settings.py parses, no em/en dashes. NOT run (no Python 3/Django/nginx on this dev machine). **DEPLOY IS DIFFERENT FROM THE USUAL - requirements.txt changed AND axes needs its own tables:** `git pull && docker compose build --no-cache web && docker compose up -d web && docker compose exec web python manage.py migrate && docker compose restart nginx`. A plain `build` will NOT reinstall requirements (mistake #5). VALIDATE BEFORE TRUSTING: `docker compose exec nginx nginx -t` must pass, then confirm you can still log in normally, and that a locked-out username frees up after the cooloff (or clear it with `docker compose exec web python manage.py axes_reset_username <name>`). If a lockout ever locks out everyone, `axes_reset` clears all attempts. |
| 2026-08-13 | `fd8b08e` | **Security: add Subresource Integrity (SRI) to the three CDN-loaded assets.** Chart.js (jsdelivr, analytics.html), 3Dmol and FontAwesome (both cdnjs, base.html) were loaded with NO `integrity` attribute, so a compromise of either CDN would execute arbitrary JS on every page of the site. All three now carry `integrity="sha384-..."` + `crossorigin="anonymous"` + `referrerpolicy="no-referrer"`. Bootstrap needed no change: there is no `BOOTSTRAP5` override in settings.py, so `django-bootstrap-v5` renders its package-default CDN URLs which ALREADY include integrity/crossorigin. HOW THE HASHES WERE PRODUCED (repeat this exactly if a version is ever bumped): download each asset to a FILE and hash the file - `curl -sL -o f URL && openssl dgst -sha384 -binary f \| openssl base64 -A`. Do NOT pipe curl through a shell variable: `$(curl ...)` strips trailing newlines, which silently produced a WRONG hash for chart.umd.min.js (205888 vs the true 205889 bytes) on the first attempt. A wrong hash does not error loudly - the browser just refuses to run the asset, so the analytics charts and the 3D viewer would have died silently. Verified: all 3 tags carry integrity, a regex sweep found no other cdnjs/jsdelivr/unpkg tag lacking it, and chart.js was confirmed byte-identical across two downloads. NOT rendered locally (no Python 3/Django on this dev machine). AFTER DEPLOY CHECK BOTH: `/analytics/` charts must draw, and the 3D viewer modal on `/database/` must render a molecule; if either is blank, the hash is wrong - re-derive it with the file method above. DEPLOY: templates only -> `git pull && docker compose build web && docker compose up -d web`. |
| 2026-08-13 | `fa1fde3` | **HOTFIX for the commit below: the searchable-dropdown change shipped a broken search page.** The explanatory comment above the new filter markup in `database_search.html` was written as a 7-line `{# ... #}` block. Django's hash-comment lexer is SINGLE-LINE ONLY, so the entire block rendered as visible text on `/database/`, and because the comment text contained a literal `<select>` the browser parsed it as a real empty select element, which swallowed the following markup and collapsed the 4-column filter grid (screenshot: stray blank dropdown, comment text on the page, filters stacked into one column). FIX: converted it to `{% comment %} ... {% endcomment %}` and removed the raw tag text from inside the comment. Swept ALL templates for the same defect - zero others found. Re-verified: `{% for %}` 6/6, `{% if %}` 65/65, `{% block %}` 6/6, `{% comment %}` 1/1, `<div>` 58/58, 4 `col-md-3` / 4 `.fsel`. The one remaining literal `<select>` (line 534) is inside the `<script>` block, where the HTML tokenizer only breaks on `</script`, so it is safe. Added MISTAKES LOG rule #11 with a one-liner grep to catch this class of bug. ROOT LESSON recorded there: the original change was verified by inspection only (no Python 3/Django on the dev machine, Browser pane policy-blocked for phytosynergydb.in) and every structural grep PASSED, because the markup genuinely was balanced - the defect lived in the templating layer, which greps cannot see. Template changes that cannot be rendered locally must be treated as unverified. DEPLOY: template only -> `git pull && docker compose build web && docker compose up -d web` (the CSS from the commit below is already collected if that deploy ran). |
| 2026-08-13 | `a75567e` | **Database search: replace the 4 native `<select>` filters with searchable, height-capped dropdowns (`.fsel`).** Symptom: opening the "Any Antibiotic" filter expanded its option list over the ENTIRE viewport, covering the navbar and the whole page. ROOT CAUSE: these were native `<select>` elements, and a native select's popup is drawn by the browser/OS - `max-height` on `select` or `option` has NO effect in Chrome, so with 100+ antibiotics the list simply grows to fill the screen. There is no CSS-only fix; the control had to be replaced. FIX: each filter is now `<div class="fsel">` = a `<button class="form-select form-select-sm fsel-toggle">` + a `<input type="hidden">` carrying the value + a `.fsel-menu` popup containing a type-to-filter box and a `.fsel-list` capped at `max-height:240px; overflow-y:auto` (the actual fix), plus a "No match" state. CRITICAL - the server contract is UNCHANGED: the hidden inputs keep the same `name`s and the same value types (`pathogen`/`antibiotic` submit an id, `mechanism`/`chemical_class` submit a string), so `_apply_search_filters` in views.py needed NO edit. The hidden inputs sit inside the existing `#filterForm`, so the `query` hidden field is still preserved and choosing an option still auto-submits (JS `hidden.form.submit()` mirrors the old `onchange="this.form.submit()"`). Closed-state appearance is deliberately IDENTICAL (the toggle reuses `.form-select.form-select-sm`) - only the open state differs, chosen that way because of the 2026-06-13 reverted-redesigns lesson. The JS also reconstructs the closed label from `.fsel-opt.is-selected` on load, so a filter that is already active after a page load still reads correctly. TWO BUGS CAUGHT DURING REVIEW, both fixed before commit: (1) a click on the search box bubbled to the `document` click handler and closed the menu instantly - fixed with `stopPropagation()` on `.fsel-menu`; (2) Enter inside the filter box would submit the surrounding form - suppressed in a `keydown` handler (Escape closes instead). `.fsel-menu` uses `z-index:1056` to clear the Bootstrap modal backdrop (1050), since this page has the 3D-viewer and Notes modals. Verified: no `<select>` left in the filter row, Django tags balanced (6/6 for, 65/65 if, 6/6 block), CSS braces balanced (617/617), no em/en dashes. NOT TESTED IN A BROWSER - no Python 3/Django on this dev machine (only Python 2.7 / MGLTools) and the Browser pane is policy-blocked for phytosynergydb.in, so this is verified by inspection only; it has more moving parts than a CSS fix and needs eyes-on after deploy. DEPLOY: template AND CSS changed -> `git pull && docker compose build web && docker compose up -d web && docker compose exec web python manage.py collectstatic --noinput && docker compose restart nginx`. |
| 2026-08-13 | `441604e` | **Remove all social + repository links from the public site; point the footer email at the author.** Maintainer request. REMOVED (4 places, templates only): (1) the "GitHub" text link in the footer "Company" column (base.html), (2) the GitHub and X/Twitter icon links in the footer bottom bar (base.html), (3) the `"sameAs": ["https://github.com/..."]` property in the sitewide Organization JSON-LD (base.html) - the whole property was dropped rather than left as an empty array, and the trailing comma on the preceding `description` key was removed to keep the JSON valid, (4) the inline GitHub link in the About page "License & Reuse" paragraph (about.html) - the sentence was reworded to end at "released under the **MIT License**." so the licensing claim survives without a dangling link. ALSO removed the whole `<!-- Twitter Card -->` meta block (`twitter:card` / `twitter:title` / `twitter:description` / `twitter:image`) from base.html `<head>`, on explicit follow-up instruction. Verified first that NO child template overrode the `twitter_title` / `twitter_description` / `twitter_image` blocks, so nothing was left dangling. The 7 Open Graph tags were deliberately KEPT - X/Twitter, Slack, WhatsApp, LinkedIn, Discord and iMessage all fall back to OG when Twitter Card tags are absent, so link previews still render; the only real loss is X showing the smaller `summary` card instead of `summary_large_image`. EMAIL: the footer mailto went from `contact@phytosynergydb.in` to `argajit05@gmail.com` (only occurrence in the codebase). The `.footer-social` div was KEPT because the email icon still lives inside it. KNOWN OPEN ITEMS surfaced but NOT changed (need a maintainer decision): (a) the footer "Contact" link still points at `{% url 'about' %}#contact`, but no `id="contact"` exists in about.html - that section was removed in the 2026-05-16 contribute-copy strip and the footer link was never updated, so it silently lands at the top of the page; (b) the plain-text Gmail in the served HTML will be harvested by scrapers, and unlike a domain address it cannot be filtered or reassigned later - a forwarding address on the domain, or JS-rendering the mailto, would avoid that. Verified: zero `github` / `twitter` / social refs remain in any template or .py. NOTE: `manage.py check` was NOT run - this dev machine has only Python 2.7 (MGLTools) on PATH, no Python 3/Django. DEPLOY: templates only, no static asset changed -> `git pull && docker compose build web && docker compose up -d web` (no `collectstatic`, no nginx restart needed). |
| 2026-08-10 | `f359abb` | **Home stats band: fix the invisible stat numbers (a CONTRAST bug that was misdiagnosed three times as a Chromium paint bug).** Symptom: the 637 / 56% / 6 figures in the dark `.stats-dark-band` did not appear on page load, then became readable once the user dragged the cursor across them. ROOT CAUSE: `.stats-dark-value` set `color: var(--primary)`, while `.section-dark, .stats-dark-band` set `background: var(--rzp-ink) !important`. In the `:root` block at custom.css:2443 BOTH variables resolve to the same hex `#0D2366`, so the numbers rendered navy-on-navy at contrast ratio 1:1 - painted correctly the whole time, just in the exact colour of the slab behind them. The "appears when I swipe over it" clue was drag-SELECTION, not a repaint: `::selection { color:#ffffff }` (custom.css:1738) recolours selected text white. The `.stats-dark-label` text never vanished because it uses `rgba(255,255,255,0.6)` rather than the variable. FIX: one line - `.stats-dark-value` now hardcodes `color:#ffffff`, with an inline comment recording why `var(--primary)` must never be used on an `--rzp-ink` background. LESSON: three earlier attempts (`dce1d06` translateZ+backface on the bands, `a624a95` translateZ+will-change on the navbar, and the `display:none`/`offsetHeight` forced-repaint script still in base.html:250) all chased a Chromium stale-paint bug that never existed - a repaint cannot help when the colour being repainted is invisible, which is exactly why each attempt was recorded as "almost working". BEFORE blaming the compositor for missing text, diff the computed text colour against the computed background. FOLLOW-UP (not done here, deliberately kept out of a bug-fix commit): those three layer hacks plus the repaint script are now very likely dead weight, and the script forces a full synchronous reflow of three sections on every page load - strip them in their own revertible commit and confirm no regression. Verified: braces balanced (606/606), no em/en dashes, `.stats-dark-value` used only by home.html. NOT verified in a browser - this dev machine has only Python 2.7 (MGLTools), no Python 3/Django, so the page cannot be rendered locally; needs eyes-on after deploy. DEPLOY: CSS only -> `git pull && docker compose build web && docker compose up -d web && docker compose exec web python manage.py collectstatic --noinput && docker compose restart nginx` (no Cloudflare purge - static files are content-hashed). |
| 2026-07-29 | - | **Hide the publication count and the journal list from all public UI.** Maintainer request: the number of curated papers and the names of the journals they came from should no longer be shown on the site. REMOVED (UI only): (1) the "Publications" cell from the home dark stats band, (2) the "Publications" tile from the About page stats strip, (3) the "Publications" stat card from the Analytics dashboard, (4) the entire home-page "Data Provenance" journal marquee section (added 2026-06-25) together with its backing query in `home_page` and its ~55-line `.jm-*` CSS block. Dead context keys dropped: `source_count` (home), `total_sources` (about + analytics), `journals_row1`/`journals_row2`. LAYOUT FIXES needed by the removals - `.stats-dark-grid` went from `repeat(4, 1fr)` to `repeat(3, 1fr)` (a fixed 4-col grid with 3 cells leaves a blank quarter), and its `max-width:767px` rule went from `1fr 1fr` to a single-column stack (2 cols with 3 cells leaves a half-empty trailing row); the About and Analytics stat strips are Bootstrap `col-lg-2` rows that dropped 6 cells -> 5 (10 of 12 columns), so both rows gained `justify-content-center` to avoid a ragged right edge. DELIBERATELY KEPT (explicitly confirmed with the maintainer before editing, to avoid a breaking change): `total_sources` in `GET /api/v1/statistics/` and its `api_docs.html` example, and the per-record `journal` field in the CSV export and `GET /api/v1/experiments/` - per-record citation metadata, so source traceability and the public API contract are unchanged. Verified: CSS braces balanced (606/606), no leftover refs to the removed context vars, no em/en dashes. NOTE: `manage.py check` was NOT run - this dev machine has only Python 2.7 (MGLTools) on PATH, no Python 3/Django - so it needs running in Docker. DEPLOY: templates + Python + CSS changed -> `git pull && docker compose build web && docker compose up -d web && docker compose exec web python manage.py collectstatic --noinput && docker compose restart nginx`. |
| 2026-07-18 | - | **CLAUDE.md accuracy pass (docs only, no code change).** Fixed five drift items found vs. the actual repo: (1) the hardcoded local git root `C:\Users\Arghya\Downloads\Projects\` was stale (current dev machine root is `D:\Sites\Projects`) - replaced with a note to confirm via `git rev-parse --show-toplevel` in both the Project Overview and the Correct Workflow steps, since the path is machine-dependent and will drift again; (2) Management Commands section was missing three existing commands - `prune_non_eskape` (dry-run delete of non-ESKAPE experiments, `--apply`/`--clean-orphan-phyto`), `backfill_gram_stain` (normalize abbreviated genera + backfill gram_stain, `--apply`), `backfill_pmid` (DOI -> PMID via NCBI E-utilities, offline-only, `--apply`/`--email`) - all added with usage examples; (3) `scripts/` directory (deploy.sh, backup_db.sh, restore_db.sh, setup_cron.sh) was absent from the Repository Layout tree - added with one-line descriptions; (4) `phytosynergydb-worker/` was only mentioned in an old changelog row - added to the layout tree with a note that its deploy status needs reconfirming; (5) `similarity.py`, `seo_views.py`, `similarity_search.html`, and the supporting doc files (DEVELOPMENT.md, SCHEMA.md, SITE_REPORT.md, TECHNICAL_SHEET.md, README.md) were missing from the layout tree - added. No em/en dashes introduced.
| 2026-07-02 | - | **About page rebuilt in GrantSetu / NUUK editorial style + similarity page UI fix & functionality upgrade.** ABOUT: `about.html` rewritten to reuse the proven home-page GrantSetu classes - `hero-nuuk` hero (`label-pill` + `heading-display` + mini-stats), alternating `section-band section-white` / `section-tinted` sections each led by a label pill + display heading, a dark `section-dark` Methodology band with a `grid-band-dark` 6-cell grid, the Data Model as a `grid-band grid-2x2`, the FIC table in `table-bordered-nuuk`, FAQ as `faq-row` `<details>`, and a closing `cta-band`. ALL prior content preserved (Problem/Approach, Scope, Data Model, Methodology, FIC standards, Limitations, Versioning, FAQ, Cite, License, Terms, Privacy) - only re-styled/re-tiered. Dropped the old `.about-page-header` hero and sticky `.about-toc` (their CSS is now dead, left in place). Added one small new CSS block `.about-list` (dotted-bullet list). SIMILARITY (`/similarity/`): (1) UI fix - the hero renders in the base `search_banner` block OUTSIDE `.simx-page`, but all `--simx-*` vars were scoped to `.simx-page`, so the search bar lost its white pill / rounding / shadow and text colours fell back (the "messed" look); moved the var block onto a shared `.simx-hero, .simx-page` selector. (2) Name search - `similarity_search_page` now resolves a non-SMILES input to a curated compound by name (iexact then icontains) and searches by its structure, excluding the self-match (new `exclude_id` param on `search_similar`); results header shows `Matched name X -> structure`, the box echoes the typed input, unresolvable input gets a clearer error. (3) Faster scoring - `search_similar` runs one `DataStructs.BulkTanimotoSimilarity` C-level pass instead of a per-compound Python `tanimoto()` loop. Files: `about.html`, `similarity_search.html`, `views.py`, `similarity.py`, `custom.css`. `py_compile` clean; no em/en dashes. NOTE: not verified live (Chrome extension not connected) - needs eyes-on after deploy, and per the 2026-06-13 reverted-redesigns lesson the About restyle should be previewed before trusting. DEPLOY: templates + Python + CSS changed -> `git pull && docker compose build web && docker compose up -d web && docker compose exec web python manage.py collectstatic --noinput && docker compose restart nginx`. |
| 2026-06-28 | - | **Bulk import: fix `value too long for type character varying(20)` on `mic_units`** (same class of bug as the 2026-06-18 varchar(50) assay_method overflow). A maintainer sheet had `mic_units = "mixed: phytochemical µl/mL, antimicrobial µg/mL"` (47 chars) on 4 rows, where the phytochemical was dosed by volume and the antibiotic by mass; `mic_units` is `varchar(20)`, so every such row crashed at the confirm step. Added `normalize_mic_units(raw_value, notes)` + `MIC_UNITS_MAX_LENGTH=20` in views.py (mirrors `normalize_assay_method`): any units string over 20 chars collapses to a short token (`mixed`, else a 20-char trim) and the full original is preserved by prepending `MIC units: ...` to `notes`, so no curated detail is lost. Wired into the bulk-import confirm step right after `normalize_assay_method` (chained on the same `notes`), replacing the old raw `mic_units = (row.get('mic_units') or 'µg/mL').strip()` line. Also defensively guarded `gram_stain` in `resolve_pathogen` with `[:20]` (also varchar(20); e.g. `Gram-negative bacilli` is 21). The third varchar(20) field, `interpretation`, was already safe (importer forces one of the four valid words). Also produced a corrected `_FIXED.xlsx` for the maintainer's failing upload (mic_units -> `mixed`, full string moved to notes). `py_compile` clean; no em/en dashes. DEPLOY: code-only change -> `git pull && docker compose build web && docker compose up -d web` (no collectstatic/nginx). |
| 2026-06-25 | - | **Result card: navy + brown thematic colour split** (`#1D276F` navy = data / antibiotic side, `#6F431D` brown = phytochemical / botanical side). Approved via mockup first. In `database_search.html` the title now wraps each name (`<span class="rl-phyto">` brown phytochemical, `<span class="rl-abx">` navy antibiotic, muted `+`) so the pairing title doubles as a legend; the two MIC lines got `rl-mic-abx` (navy) / `rl-mic-phyto` (brown) classes and their icons switched to FontAwesome (`fa-pills` / `fa-leaf`) so the glyph inherits the theme colour. In custom.css: brown 3px `border-top` on `.rl-card` (preserved on hover), navy FIC value + abx MIC, brown phyto MIC, navy `.rl-btn-primary` (Source paper). IMPORTANT - the theme is non-semantic and used ONLY on these cues: the interpretation badge keeps its meaning-colours and the categorical class chips keep the `chem_class_color` map (a class reads the same colour on cards and, later, in filters), so the two colour systems never collide. `#1D276F` is a near-match to the existing brand navy, so it is not a palette shift; brown is the genuinely new accent. Deferred this round (maintainer said skip): the chemical-class filter dropdown -> colour chips, and an analytics chemical-class chart. Braces balanced; no em/en dashes. |
| 2026-06-25 | - | **Cleanup: removed the dead old result-card CSS** now that the `.rl-*` re-tiered card is confirmed live. Deleted three scattered, unused blocks from custom.css: the original `.result-card` grid + `.rc-*` rules, the `.lipinski-bar`/`.lipinski-prop`/`.lipinski-verdict`/`.chem-class-badge` block + its `@media (max-width:992px)` grid override, and the Razorpay "REFINED STAT TILES" `.result-card`/`.rc-data-point`/`.rc-value`/`.rc-label` override block. Kept the shared `.results-count-text`. Verified only `database_search.html` ever used these classes (now on `.rl-*`) and braces stay balanced. No visual change. |
| 2026-06-25 | - | **Static files: content-hashed filenames (ManifestStaticFilesStorage) to end the stale-CSS/Cloudflare-cache problem permanently.** Root cause of the recurring "deployed CSS doesn't show up" issue (favicon refresh, then the result-card redesign): `custom.css` is a fixed URL, so the browser AND the Cloudflare edge cache keep serving the old copy until a manual "Purge Everything". Fix: in production, `collectstatic` now writes content-hashed names (`custom.7f3a2c.css`) and `{% static %}` emits the hashed URL, so a changed file gets a brand-new URL that no cache has seen - no purge ever needed again. Added `STORAGES` to settings.py (gated on DEBUG: plain `StaticFilesStorage` in dev so runserver works without collectstatic; hashed storage in prod) and a `phytosynergy_project/storages.py` `StableManifestStaticFilesStorage` subclass with `manifest_strict = False` (a `{% static %}` ref missing from the manifest falls back to the un-hashed name instead of 500ing). Audited before enabling: only one CSS file, its only local `url()` ref (`hero_background-green.jpg`) exists, and all templates use `{% static %}` (no hardcoded `/static/` paths), so `collectstatic` post-processing won't hard-fail. NOTE: this also fixes the *current* unstyled-card issue on deploy WITHOUT a manual purge, because base.html will reference `custom.<hash>.css` (a URL Cloudflare has never cached). Operational requirement (already in the deploy flow): `collectstatic` must run on every deploy. `py_compile` clean; `manage.py check`/`collectstatic` to be run in Docker by the maintainer. |
| 2026-06-25 | - | **Database search: redesigned result card (re-tiered vertical card).** Replaced the dense 6-column `.result-card` grid (a spreadsheet row dressed as a card) with a vertical card that has clear hierarchy, ported from GrantSetu's grant-card patterns. Four tiers: (1) identity - interpretation badge top-left + year/assay top-right in mono, then the synergy PAIR as the bold Inter title (`phyto + antibiotic`) with `vs <pathogen>` subtitle; (2) headline metric - FIC index promoted to a large navy number with the two MIC-combo values (now with units) beside it as icon+label support; (3) cheminformatics strip - class chip + MW/LogP/HBD/HBA/TPSA/formula + Lipinski verdict in one hairline-bounded mono row; (4) action footer (hairline top) - `Source paper` as the filled primary, then 3D / Notes / Share / Copy citation / Edit. NOTHING dropped - every field from the old card is preserved, just re-tiered (the maintainer reverted past table redesigns, so all data was kept and a faithful mockup was approved before building, per the 2026-06-13 lesson). New scoped `.rl-*` CSS block; the old `.result-card`/`.rc-*`/`.lipinski-*` styles are now UNUSED (only this page referenced them) and left in place for a follow-up cleanup. ALSO ships two queued patterns: Share (native `navigator.share` -> clipboard fallback, brief "Copied" state) + Copy citation buttons, and a chemical-class colour map via a new `chem_class_color` template filter (deterministic hash of the class name -> one of six chip colours `.rl-chip-c0..c5`, so a class is always the same colour, zero map to maintain). FIC stays navy regardless of interpretation (colour signal lives in the badge, whose existing colours were kept). Files: `database_search.html` (markup + `{% load analytics_filters %}` + share/cite JS in the existing script block), `custom.css` (`.rl-*` block), `templatetags/analytics_filters.py` (`chem_class_color`). DEPLOY: templates + templatetag + CSS changed -> rebuild web + `collectstatic` + nginx restart. `manage.py check` to be run in Docker by maintainer (no Django in dev shell; `py_compile` clean). |
| 2026-06-25 | - | **Home: "Data Provenance" journal marquee** (first of the GrantSetu UI patterns ported into the Django/Bootstrap stack - zero new infra). A new white `.section-band` between Recent Entries and the dark Process band: eyebrow label-pill ("Data Provenance"), display heading "Curated from peer-reviewed literature.", and two opposite-scrolling rows of journal-name pills (every 4th gets a navy `#E8ECF5/#0D2366` accent). Journals are pulled LIVE from the DB in `home_page` (`Source.journal`, de-duplicated case-insensitively, sorted, split into two rows) so the strip always reflects real provenance; the section self-hides unless there are >= 6 distinct journals (avoids a stuttering short loop). Row content is rendered twice in the template so the CSS `translateX(-50%)` loop is seamless. All styles scoped under `.jm-*` in custom.css (white pills, 1.5px border, edge fade `mask-image`, 50s linear tracks, pause-on-hover) with a `prefers-reduced-motion` fallback that drops the animation and allows plain horizontal scroll. Provenance framing only - no "community/contribute" copy (rule #10). Previewed as a faithful brand mockup and green-lit before implementing (per the 2026-06-13 reverted-redesigns lesson). DEPLOY: CSS changed, so `collectstatic` + nginx restart needed in addition to the web rebuild. Next ported patterns queued: share / copy-citation buttons on result cards, and a chemical/antibiotic class colour map. |
| 2026-06-25 | - | **Home dark bands: deterministic repaint to kill the Chromium stale-paint bug (attempt 3).** The "Process" (`.section-dark`) and stats (`.stats-dark-band`) bands, plus the dark footer (`.site-footer-dark`), intermittently rendered with an UNPAINTED (white) background while sitting under the composited sticky navbar, hiding the always-white text until a hover/scroll forced a repaint. This is a paint/compositing bug, NOT a text-color bug - which is why the prior two CSS-only GPU-layer hacks (`dce1d06` translateZ+backface on the bands, `a624a95` translateZ+will-change on the navbar) only ever almost worked: layer promotion HINTS at compositing but does not GUARANTEE an initial paint. Fix is additive and lives in `base.html` only (no CSS/color change, nothing in the section to "break"): a small script forces a deterministic repaint of the dark bands by toggling each out of layout and back synchronously (`display:none` -> read `offsetHeight` -> restore), so no frame paints in between (no flash) and Chromium must repaint the band. Runs on `load` and once more after the first scroll (lazy scroll-in case). The existing translateZ layers were left in place so the forced paint persists as the bands composite in on scroll. NOTE: could not reproduce/verify locally - no browser was connected in the session and the dev shell has no running site - so this needs eyes-on confirmation on the live deploy. Deploy = template change, so rebuild required (`git pull && docker compose build web && docker compose up -d web`); no `collectstatic` needed (no static asset changed). If it still flickers, next escalation is to consolidate/remove the competing CSS layer hacks or promote a single content wrapper. |
| 2026-06-21 | - | **Navbar: center the main links** (GrantSetu three-zone layout). One-line change in `base.html`: the primary links `<ul>` went from `me-auto` (left-aligned right after the brand) to `mx-auto`, so the layout is now logo left / links centered / auth cluster right, matching the GrantSetu `grantsetu-frontend/src/components/Navbar.tsx` build (`flex-1 justify-center`). Verified against that file that the nav FONTS were already a faithful copy and needed no change: Roboto Mono, 13px, weight 600, `letter-spacing 0.06em`, uppercase, black, 72px bar, 2px black bottom border, 2px-black rounded dropdown. Link hover deliberately kept at navy `var(--primary)` rather than GrantSetu's brand red `#E9283D`, to stay consistent with PhytoSynergyDB's navy/blue palette. Affects every page (shared navbar); previewed before/after as a mockup first. |
| 2026-06-20 | - | **Similarity page redesign** (job-board / sage aesthetic). Restyle only - all functionality, form fields (`smiles`/`threshold`/`limit`), results logic, examples, error/empty states and the 3Dmol viewer are unchanged; no view or model change. `similarity_search.html` rewritten: full-width olive->sage gradient hero (inline botanical-leaf SVG bleeding off the right, eyebrow pill, near-black bold headline, hand-drawn scribble under "SMILES"), floating white pill search bar (search icon + monospace SMILES input + near-black Search button), chip-style threshold/limit controls + "Searching N fingerprinted compounds." status, rounded outline example chips; results as stacked white rounded cards (bold name, green Tanimoto score pill that shades by tier, icon-label metadata row, near-black/ghost actions, decorative bookmark corner) with a pink monospace code-chip for the query SMILES; soft off-white empty-state card. All new styles are scoped under `.simx-*` (off-white #FAFAF8 page, near-black #1A1A1A buttons, Inter headings, monospace SMILES) so NO other page is affected; the old `.sim-*` block was removed from custom.css. The shared navbar was left untouched (login/logout was already a near-black outlined pill, no bright blue). Card metadata intentionally keeps the per-compound fields (class/MW/experiments/synergistic/CID) rather than inventing a representative antibiotic/pathogen/FICI/PMID, per "keep all data fields, do not invent features". Previewed as a faithful mockup before committing (per the 2026-06-13 reverted-redesigns lesson). |
| 2026-06-20 | - | **New feature: Chemical Similarity Search** (`/similarity/`). A researcher pastes a SMILES and gets the structurally most similar phytochemicals in the DB, ranked by Tanimoto similarity on 2048-bit Morgan/ECFP4 fingerprints (radius 2), each linked to its synergy experiments. New `synergy_data/similarity.py` (all RDKit logic, lazy imports so the app boots without RDKit; `compute_fingerprint`/`fp_to_bitstring`/`bitstring_to_fp`/`tanimoto`/`update_fingerprint`/`search_similar`). New `Phytochemical.morgan_fp` TextField + migration `0006`. New `manage.py compute_fingerprints` command (`--all`/`--name`) to backfill the stored bit strings; fingerprints are also refreshed on save in `data_entry_view`/`edit_entry_view`. View `similarity_search_page` + template `similarity_search.html` (SMILES bar, threshold/limit controls, example pills, ranked result cards with similarity bar, experiment/synergy counts, 3Dmol viewer reused). JSON API `GET /api/v1/similarity/?smiles=&limit=&threshold=` (`api_similarity`) + API-docs entry. Added a `phytochemical` filter to `_apply_search_filters` so result cards can deep-link to `database/?phytochemical=<id>`. Navbar Explore dropdown gains "Similarity Search". The query view falls back to live fingerprinting from SMILES when `morgan_fp` is blank, so search works before the backfill runs. DEPLOY: run `migrate` then `compute_fingerprints` once. `py_compile` clean; `manage.py check` to be run in Docker by the maintainer (RDKit/Django not installed in the dev shell). |
| 2026-06-18 | - | Bulk import preview now detects duplicates up front. Previously the Validate/preview pass never ran the duplicate check (it only happened at Confirm), so re-uploading a sheet showed already-imported rows as "importable" and the known-papers banner falsely claimed "byte-identical re-entries are skipped". Added read-only `_row_already_imported()` (mirrors the confirm-step phyto+abx+pathogen+source key without creating FK rows); staging now flags existing rows with a new `duplicate` status, excludes them from `importable_count` and the confirm payload. Template: 4th summary card ("Already in DB"), blue "In DB" row badge + shading, honest summary line, and corrected known-papers banner copy. |
| 2026-06-18 | - | Bulk import: fix `value too long for type character varying(50)` failures + clean up the error UI. Root cause: free-text/oversized `assay_method` values (e.g. a 100-char "Checkerboard microbroth dilution (...)" sentence) overflow the varchar(50) choices column. Added `normalize_assay_method()` + `VALID_ASSAY_METHODS`/keyword map in views.py: any non-vocabulary value is mapped to a valid code (keyword match, else `other`) and the original text is preserved by prepending `Assay method: ...` to `notes`; wired into the confirm step of `bulk_import_view`. UI: the page was rendering Django messages twice (base.html AND bulk_import.html both looped `messages`) and emitting one full-width alert per row error. Removed the duplicate loop in bulk_import.html; the confirm step now stashes a single structured `bulk_import_result` in the session, rendered as one compact "Import Summary" card (count pill badges + collapsible scrollable row-error list). Also produced a corrected `_FIXED.xlsx` for the maintainer's failing upload (assay_method -> `checkerboard`, long text moved to notes). |
| 2026-06-13 | `791b7aa` | Database search page UI: tried two redesigns and reverted both back to the original card view at the maintainer's request. History only (no net change to the page): `e974d3d` (Untitled-UI card/list, reverted by `1a8b71e`), then `2e8d185` (dark DrugBank-style data table with inline expandable Details rows) and `1f9e6b9` (lighter clean-SaaS table), both reverted by `791b7aa`. The expandable-details table work is recoverable from those commits if revisited. Lesson: preview big visual changes (a mockup or local render) before deploying - the maintainer reverted each time after seeing it. |
| 2026-06-13 | `704ebc0` `7faded3` | Favicon refresh + footer recolor. Replaced the favicon set (ico, 16/32, apple-touch, android-chrome 192/512) from a new favicon.io export; fixed base.html to reference the actual files (the old links pointed at a non-existent `favicon-96x96.png`/`favicon.svg`) and rewrote `site.webmanifest` (name + relative icon paths + navy theme). Recolored `.site-footer-dark` from `#000000` to dark navy `#0A1733`. GOTCHA: Cloudflare edge-caches static assets (favicon, CSS) - changes need a Cloudflare "Purge Everything" after `collectstatic`, not just a hard refresh. |
| 2026-06-13 | `0459ba1` `3fd70eb` `07732b0` `bf6bf3c` | SEO + LLM-crawler pass. Added hand-rolled `/robots.txt`, `/sitemap.xml`, and `/llms.txt` (new `synergy_data/seo_views.py`, wired in `phytosynergy_project/urls.py`; no sitemaps/sites framework, no migration). Added `SITE_URL` setting + `seo` context processor; base.html now emits canonical, robots, Open Graph and Twitter tags with per-page override blocks, plus sitewide Organization + WebSite JSON-LD (SearchAction) and a server-rendered schema.org `Dataset` block on the home page (Google Dataset Search). Unique titles/meta-descriptions on database, analytics, about, download, api_docs. Fixed stale `.org` -> `.in` (footer email, citation). robots policy: search engines + AI *citation* bots (OAI-SearchBot, ChatGPT-User, PerplexityBot, Perplexity-User, Claude-Web) allowed; AI *training* crawlers (GPTBot, ClaudeBot, Google-Extended, CCBot, Bytespider, etc.) disallowed; bulk endpoints (`/api/v1/`, `*export=`) blocked; `Content-Signal: search=yes,ai-input=yes,ai-train=no`. Added optional `GOOGLE_SITE_VERIFICATION` / `BING_SITE_VERIFICATION` env-driven meta tags. Added `TECHNICAL_SHEET.md` (manuscript reference; not committed yet at time of writing). |
| 2026-06-13 | - | Cloudflare/indexing ops (dashboard, no code). Google Search Console verified for `phytosynergydb.in`; sitemap submit initially failed with **HTTP 403** because a Cloudflare **custom WAF rule "AI Crawl Control - Block AI bots by User Agent"** was blocking Googlebot AND Bingbot (not Bot Fight Mode, which was already off, nor Browser Integrity Check). Diagnosed via `curl -A "...Googlebot..."` returning 403 while a normal UA got 200. Fix: disabled that custom rule (Security -> Security rules); Googlebot/Bingbot then returned 200. AI-training enforcement now relies on robots.txt (advisory) + the Cloudflare AI Audit per-crawler toggles. LESSON: any Cloudflare AI-bot blocking feature can sweep in search engines - after enabling one, always re-test Googlebot (`curl -A Googlebot` or GSC "Test Live URL") before trusting it. Maintenance page still NOT deployed (needs the `phytosynergydb-offline` GitHub Pages repo + `wrangler deploy`). |
| 2026-06-12 | `ea50e54` `9b4e914` `dd22d5d` | Migrate ngrok -> dedicated Cloudflare Tunnel on the new domain `phytosynergydb.in` (purchased from Hostinger; nameservers moved to Cloudflare). Removed the ngrok `tunnel` service from docker-compose; added a `cloudflared` container running a dedicated tunnel (`phytosynergy`, id `38203e22-6472-4cbf-9e33-fad6e510d7d0`) with ingress -> `nginx:80` (config in `cloudflared.yml`, no secrets; creds JSON mounted from `/home/mmilab/.cloudflared/`, never committed). Container runs as `user: root` so it can read the 0400 creds file (mirrors the grantsetu host systemd tunnel) - the `nonroot` default user hit `permission denied`. Updated `ALLOWED_HOSTS`/`CSRF_TRUSTED_ORIGINS` to the new domain; enabled HSTS (`SECURE_HSTS_SECONDS=31536000`, includeSubDomains) now that the domain is dedicated. nginx `server_name` -> `phytosynergydb.in www.phytosynergydb.in`. Added `phytosynergydb-worker/` (Cloudflare Worker passthrough that redirects to a GitHub Pages maintenance page on origin-down statuses incl. 530, plus the offline page) - NOT yet deployed. GOTCHA: `cloudflared tunnel route dns` created junk `*.grantsetu.in` records because the existing `cert.pem` is scoped to the grantsetu.in zone; DNS for the new zone was created by hand in the Cloudflare dashboard as proxied CNAMEs to `<tunnel-id>.cfargotunnel.com` instead. Verified live: `curl -I https://phytosynergydb.in` -> HTTP/2 200, HSTS header present, 4 tunnel connections registered. |
| 2026-06-09 | - | Security & publication hardening pass (code only; secrets remediation left to the maintainer). settings.py: DEBUG now defaults to 0 (fail closed); SECRET_KEY raises in production if unset (dev fallback only when DEBUG); ALLOWED_HOSTS defaults to localhost,127.0.0.1 not '*'; added production-only block (SECURE_PROXY_SSL_HEADER for the nginx+tunnel chain, SECURE_SSL_REDIRECT, SESSION/CSRF_COOKIE_SECURE, SESSION_COOKIE_HTTPONLY, nosniff, X_FRAME_OPTIONS DENY, Referrer-Policy; HSTS off by default with a comment - shared ngrok domain); added LOGGING to stdout. nginx.conf: forward X-Forwarded-Proto via a map fallback, add security headers, gzip, static caching, server_tokens off. Wired the existing health_check view to /health/. Reworded the false "API is rate-limited" home FAQ to describe the real pagination cap. Added MIT LICENSE file (code MIT, data CC-BY-4.0 note) to back the README badge / About claim. Fixed README Django badge 5.2 -> 4.2 LTS. KNOWN OPEN ITEM: docker-compose.yml still has live secrets committed and in git history (DB password, DJANGO_SECRET_KEY, ngrok authtoken) - must be rotated, moved to .env, and purged from history / repo made private. py_compile clean; full `manage.py check` to be run in Docker by maintainer. |
| 2026-05-29 | - | Fix data-loss: `assay_method`, `antibiotic_class`, `plant_source` and `gram_stain` were accepted by the import template/COLUMN_MAP (and partly the form) but never written. Added `resolve_pathogen` (auto-derives gram stain from genus via GRAM_STAIN_BY_GENUS, explicit value wins), `resolve_antibiotic` (links AntibioticClass, fills only when blank) and `link_plant_source` (get_or_create Plant + M2M) helpers in views.py. Added the four fields to SynergyEntryForm + data_entry.html and wired them through data_entry_view, edit_entry_view (incl. pre-populate on edit) and bulk_import_view. No migration needed - columns already existed. Also swept all remaining em/en dashes from CHANGELOG.md, SCHEMA.md, SITE_REPORT.md, DEPLOYMENT.md, the settings.py comment, and two analytics files (rule #6); only CLAUDE.md rule text retains them by design. `manage.py check` clean. |
| 2026-05-17 | `19b71a6` | Analytics: drop chart-bar icon from main "Analytics Dashboard" heading. |
| 2026-05-17 | `83f32d7` | Analytics dashboard: swap remaining FontAwesome icons for Phosphor SVGs (chart-bar, unite, test-tube, plant, pill, calendar-dots, presentation-chart, grid-nine). Added `pill.svg` for Top Antibiotics. |
| 2026-05-17 | `a4f0983` | Begin Phosphor SVG icon migration. Added 25 SVGs to `synergy_data/static/synergy_data/icons/` and `.icon-svg` / `.icon-svg-sm/md/lg/xl` sizing helpers in custom.css. Migrated navbar dropdown (Browse / Synergistic / Antagonistic), authenticated nav (Data Entry / CSV Import / Logout / Login), footer mail, database search page (search button, Export CSV, MoA, PubChem link, chemical class tag, 3D, Notes, Edit, empty-state, 3D-modal external link), and bulk import (file-csv, cloud download, lock, upload, validate, valid/warning/error chips, table, confirm, start over). Remaining templates (home, data_entry, login, download, api_docs, about) still on FontAwesome - migrate in follow-up passes. |
| 2026-05-17 | `c9e2fa4` | Navbar: merge duplicate "Search Database" + "Browse All Entries" dropdown items into single "Browse Database"; add "Antagonistic Pairs" shortcut alongside "Synergistic Pairs". |
| 2026-05-17 | `3782d45` | Search results: lay Notes button next to Source Paper (flex-nowrap, gap), navy hover fill on `.btn-outline-secondary` (primary border + white fill on hover) for consistency with Source Paper. |
| 2026-05-17 | `7f57fce` | Database search page: minimal text-only results count (drop the pill background), drop dead non-functional "All Categories" decorative dropdown, add Notes modal button (Bootstrap modal with curator notes, only shown when `experiment.notes` is non-empty). |
| 2026-05-17 | `f084356` | Recolor bright sky-blue `#3395FF` (Razorpay override block in custom.css) to dark navy `#0D2366`; recolor green Synergy pill to soft navy tint `#E8ECF5 / #0D2366` for site-wide dark navy consistency. |
| 2026-05-17 | `55e5532` | About: trim sticky TOC to 6 essential anchors (Overview / Methodology / FIC standards / FAQ / Cite / License); previously 14 chips overflowed visually. |
| 2026-05-17 | `b46b4d8` | Restore brand logo image to navbar (`<img src="logo.png" height="28">` alongside wordmark). Logo was lost in the prior icon-removal pass; this brings it back while keeping nav-link text-only. |
| 2026-05-16 | - | Strip "contribute / submit data" copy from the public site (about page Programmatic Access + Contribute + Contact sections removed, home Step 04 reworded, footer "Contribute Data" link removed, FAQ entries in `home_page` and `about_page` views rewritten to state the DB is closed/expert-curated). Added rule #10 to CLAUDE.md: PhytoSynergyDB is a closed expert-curated resource, no public submissions. |
| 2026-05-16 | `d7061b5` | Expand About page: live stats strip, Scope, Data Model (6 schema cards), expanded Methodology (PubChem + RDKit cards), Limitations, Versioning, FAQ accordion, License & Reuse, Terms, Privacy, sticky in-page TOC. New view context on `about_page` (stats + about_faqs). New CSS: `.about-toc`, `.about-stats-strip`, `.stat-mini`, `.schema-card`. Removed em-dashes throughout. |
| 2026-05-16 | `b46b4d8` | Remove FontAwesome / SVG icons from navbar links and dropdown items; keep brand logo image + text only. |
| 2026-05-01 | - | Rebuild home page in NUUK / GrantSetu editorial style (blue palette kept). Sections: left-aligned hero with label pill + giant display heading + 3 mini-stats; about with 2x2 hover-fill grid-band; ESKAPE pathogen cards refined; recent entries table in 2px black border; dark "Process" 4-cell band (added Cite & Share step); dark stats band (4 cols); FAQ accordion with schema.org JSON-LD; full-bleed primary-blue final CTA. New CSS classes: `.label-pill`, `.heading-display`, `.hero-nuuk`, `.btn-nuuk-primary/secondary/link/arrow`, `.section-band`, `.section-dark`, `.grid-band` (2x2 + 1x4), `.stats-dark-band`, `.faq-row`, `.cta-band`, `.btn-cta-white/outline-white`. New view context: `synergy_share`, `faq_data`. |
| 2026-04-30 | - | Apply GrantSetu navbar fonts (Inter + Roboto Mono); add Typography section + em-dash hard rule (#6 strengthened) + rules #7-9 (Docker rebuild required, collectstatic+nginx restart, server path) to CLAUDE.md |
| 2026-04-30 | `651ebde` | Restyle navbar to GrantSetu look: 72px height, 2px black border, uppercase mono links, fast-forward `color-palette-redesign` into `main` and delete the redesign branch |
| 2026-04-26 | - | Replace all em dashes with hyphens across templates, CSS, Python files; add rule #6 to CLAUDE.md |
| 2026-04-17 | `71263e3` | Fix bulk import freeze: remove in-request PubChem enrichment, add `transaction.atomic()`, harden gunicorn (--workers 3 --timeout 120) |
| 2026-04-17 | `8b94cd6` | Fix bulk import to accept XLSX + CSV, clean null strings / encoding, COLUMN_MAP aliases, colour-coded preview, duplicate detection |
| 2026-04-17 | `c820240` | Add bulk CSV import with strict MIC/FIC validation |
| 2026-03-25 | `b90acd1` | Revert site-wide CSS to original blue theme |
| 2026-03-24 | `b02c350` | Remove AI-assisted PDF extraction feature |
| 2026-03-24 | `44404a2` | Add CHANGELOG.md |
| 2026-03-24 | `24312a9` | Add interactive analytics dashboard (Chart.js) |
| 2026-03-24 | `9062a89` | Add Plant model, cheminformatics fields, assay_method, RDKit compute command |
