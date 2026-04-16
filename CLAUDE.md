# CLAUDE.md — PhytoSynergyDB Project Guide

> **READ THIS BEFORE MAKING ANY CHANGES.**
> Update this file after every session with a summary of changes made and any new lessons learned.

---

## Project Overview

**App:** PhytoSynergyDB — curated database of phytochemical–antibiotic synergy experiments against ESKAPE pathogens.
**Stack:** Django 4.2 LTS · PostgreSQL 15 · Gunicorn · Nginx · Docker Compose · ngrok tunnel
**Host:** Dell PowerEdge R730, 84 GB RAM (self-hosted, ngrok public URL)
**Repo:** `https://github.com/argajitsarkr/phytosynergy-db-project.git`
**Active branch:** `color-palette-redesign`

---

## Repository Layout

```
C:\Users\Arghya\Downloads\Projects\     ← GIT ROOT
├── manage.py
├── requirements.txt                    ← add packages here; rebuild Docker after changes
├── Dockerfile                          ← Python 3.12-slim; gunicorn CMD here
├── docker-compose.yml                  ← db / web / nginx / tunnel services
├── nginx.conf                          ← proxy pass to gunicorn:8000
├── Procfile                            ← Heroku-style; not used in Docker deploy
├── phytosynergy_project/
│   ├── settings.py                     ← env-var driven; DATABASE_URL / SECRET_KEY / DEBUG
│   ├── urls.py                         ← includes synergy_data.urls
│   └── wsgi.py
├── synergy_data/                       ← the only Django app
│   ├── models.py                       ← AntibioticClass · Phytochemical · Antibiotic
│   │                                      Pathogen · Source · SynergyExperiment · Plant
│   ├── views.py                        ← all views + helper functions
│   ├── forms.py                        ← SynergyEntryForm · BulkCSVUploadForm
│   │                                      BULK_CSV_COLUMNS · COLUMN_MAP · _canonical_header
│   ├── urls.py                         ← URL routing (see table below)
│   ├── pubchem_utils.py                ← PubChem + ClassyFire HTTP enrichment
│   ├── context_processors.py           ← view_counter (injected into all templates)
│   ├── admin.py
│   ├── tests.py
│   ├── management/commands/
│   │   ├── enrich_phytochemicals.py    ← offline PubChem/ClassyFire backfill
│   │   └── compute_properties.py      ← RDKit cheminformatics batch compute
│   ├── templates/synergy_data/
│   │   ├── base.html                   ← Plus Jakarta Sans, Bootstrap 5, blue palette
│   │   ├── home.html · about.html · login.html
│   │   ├── database_search.html · download.html
│   │   ├── data_entry.html · bulk_import.html
│   │   └── analytics.html · api_docs.html
│   ├── static/                         ← app-level static assets
│   └── templatetags/analytics_filters.py  ← custom filter for heatmap colour mapping
├── staticfiles/                        ← collectstatic output (do NOT edit manually)
├── CHANGELOG.md                        ← curated history of all features
├── DEPLOYMENT.md                       ← step-by-step server deploy guide
└── CLAUDE.md                           ← this file
```

---

## URL Map

| URL | View | Auth | Notes |
|-----|------|------|-------|
| `/` | `home_page` | Public | Stats counters, ESKAPE summary |
| `/database/` | `database_search_page` | Public | Filterable experiment table |
| `/database/download/` | `download_data` | Public | CSV export of filtered results |
| `/about/` | `about_page` | Public | |
| `/data-entry/` | `data_entry_view` | Login | Single-row form; calls `enrich_phytochemical` on save |
| `/data-entry/edit/<pk>/` | `edit_entry_view` | Login | |
| `/bulk-import/` | `bulk_import_view` | Login | CSV/XLSX import (see section below) |
| `/bulk-import/template/` | `bulk_import_template` | Login | Downloads XLSX template |
| `/analytics/` | `analytics_page` | Public | Chart.js dashboard |
| `/api/v1/experiments/` | `api_experiments` | Public | JSON, paginated, filterable |
| `/api/v1/statistics/` | `api_statistics` | Public | Aggregate stats JSON |
| `/api/docs/` | `api_docs` | Public | |
| `/accounts/login/` | Django `LoginView` | — | Template: `synergy_data/login.html` |
| `/accounts/logout/` | Django `LogoutView` | — | Redirects to `home` |

---

## Data Model (key fields)

```
SynergyExperiment
  ├── phytochemical → Phytochemical (compound_name, pubchem_cid, smiles, Lipinski, ClassyFire)
  ├── antibiotic    → Antibiotic (antibiotic_name, antibiotic_class → AntibioticClass)
  ├── pathogen      → Pathogen (genus, species, strain)  unique_together on all three
  ├── source        → Source (doi, pmid, publication_year, article_title, journal)
  ├── mic_phyto_alone / mic_abx_alone / mic_phyto_in_combo / mic_abx_in_combo (Decimal, nullable)
  ├── mic_units (default µg/mL)
  ├── fic_index (Decimal, nullable) — auto-calculated if all 4 MICs present
  ├── interpretation (Synergy / Additive / Indifference / Antagonism) — auto-derived from FIC
  ├── assay_method (checkerboard / time_kill / disk_diffusion / broth_microdilution / other)
  ├── moa_observed (TextField, nullable)
  └── notes (TextField, nullable)
```

**FIC thresholds:** ≤0.5 Synergy · ≤1.0 Additive · ≤4.0 Indifference · >4.0 Antagonism

---

## Bulk Import (`/bulk-import/`) — Critical Rules

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
A failure on any row rolls back only that row — no orphan FK records, no partial state.

### Column aliases (COLUMN_MAP in `forms.py`)
The import recognises common variants: `doi` → `source_doi`, `fic` → `fic_index`, `compound` → `phytochemical_name`, `antibiotic` → `antibiotic_name`, `mechanism` → `moa_observed`, etc. Full map in `synergy_data/forms.py`.

---

## Key Helper Functions in `views.py`

| Function | Purpose |
|----------|---------|
| `parse_pathogen_name(full_name)` | Splits `"Staphylococcus aureus 03"` → `("Staphylococcus", "aureus", "03")` |
| `auto_calculate_fic(...)` | `(mic_phyto_combo / mic_phyto_alone) + (mic_abx_combo / mic_abx_alone)` — returns None if any value is zero/None |
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
```

---

## Correct Workflow for Making Changes

1. **Read this file first**
2. Edit files inside `C:\Users\Arghya\Downloads\Projects\`
3. Run `python manage.py check` to catch Django-level errors before committing
4. Stage specific files — **NEVER `git add .`** (the root contains personal files)
5. Commit and push:
   ```bash
   cd "C:/Users/Arghya/Downloads/Projects"
   git add <specific files>
   git commit -m "descriptive message"
   git push origin color-palette-redesign
   ```
6. Deploy on the server (see **Deploy Workflow** below)
7. Update the **Changelog** section at the bottom of this file

---

## Deploy Workflow (on the server)

```bash
cd ~/phytosynergy-db-project           # adjust if path differs
git pull origin color-palette-redesign

# If requirements.txt or Dockerfile changed:
docker compose down
docker compose build --no-cache web
docker compose up -d

# If only Python/template files changed (no new dependencies):
docker compose restart web

# Always run after deploy:
docker compose ps                      # all four services should be Up
docker compose logs --tail=50 web      # check for startup errors
```

**After any bulk import:**
```bash
docker compose exec web python manage.py enrich_phytochemicals
```

**If the site freezes / gunicorn gets wedged:**
```bash
docker compose logs --tail=300 web     # look for [CRITICAL] WORKER TIMEOUT
docker compose restart web             # nginx + db stay up; only web restarts
```

---

## Environment Variables (set in `docker-compose.yml`)

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | Postgres connection string — `postgres://user:pass@db:5432/phytosynergy_db` |
| `DJANGO_SECRET_KEY` | Django secret key |
| `DEBUG` | `0` for production, `1` for dev |
| `ALLOWED_HOSTS` | Comma-separated; include server IP, `localhost`, ngrok wildcard |
| `CSRF_TRUSTED_ORIGINS` | Must include `https://*.ngrok-free.dev` for ngrok to work |

---

## ❌ MISTAKES LOG — What NOT To Do

### 1. NEVER call `enrich_phytochemical()` inside a request that processes multiple rows
- **What happened (2026-04-17):** 30-row XLSX import triggered ~46 s of PubChem/ClassyFire HTTP calls per row inside the gunicorn worker. Single worker blocked → site froze for all users for ~23 minutes.
- **Fix:** Removed the enrichment call from `bulk_import_view`; runs offline via `manage.py enrich_phytochemicals` instead.
- **Rule:** Any operation that makes unbounded external HTTP calls MUST run in a management command or background worker, never inside a Django view handling a user request.

### 2. NEVER run gunicorn with default 1 worker in production
- **What happened:** One blocked worker = entire site unreachable.
- **Fix:** Added `--workers 3 --timeout 120 --access-logfile - --error-logfile -` to the `Dockerfile` CMD.
- **Rule:** Always set `--workers` explicitly. Rule of thumb: `2 × CPU_count + 1`.

### 3. NEVER use `git add .` or `git add -A` from the project root without checking `git status` first
- The working directory is inside `C:\Users\Arghya\Downloads\Projects\` — check `git status` carefully before staging.

### 4. ALWAYS wrap multi-step DB operations in `transaction.atomic()`
- Without it, a partially-completed loop leaves orphan FK records that are hard to clean up.

### 5. If you add a new Python package, rebuild the Docker image
- `requirements.txt` changes are only picked up on `docker compose build --no-cache web`.
- `docker compose restart web` does NOT reinstall packages.

---

## Changelog

| Date | Commit | Description |
|------|--------|-------------|
| 2026-04-17 | `71263e3` | Fix bulk import freeze: remove in-request PubChem enrichment, add `transaction.atomic()`, harden gunicorn (--workers 3 --timeout 120) |
| 2026-04-17 | `8b94cd6` | Fix bulk import to accept XLSX + CSV, clean null strings / encoding, COLUMN_MAP aliases, colour-coded preview, duplicate detection |
| 2026-04-17 | `c820240` | Add bulk CSV import with strict MIC/FIC validation |
| 2026-03-25 | `b90acd1` | Revert site-wide CSS to original blue theme |
| 2026-03-24 | `b02c350` | Remove AI-assisted PDF extraction feature |
| 2026-03-24 | `44404a2` | Add CHANGELOG.md |
| 2026-03-24 | `24312a9` | Add interactive analytics dashboard (Chart.js) |
| 2026-03-24 | `9062a89` | Add Plant model, cheminformatics fields, assay_method, RDKit compute command |
