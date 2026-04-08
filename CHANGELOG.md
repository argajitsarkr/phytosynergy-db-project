# PhytoSynergyDB — Project Changelog

> Curated database of phytochemical-antibiotic synergies against ESKAPE pathogens.
> Deployed via Docker Compose (Nginx + Gunicorn + Django 4.2 + PostgreSQL 15) on Dell PowerEdge R730.

---

## Current Stack

| Component | Version / Detail |
|-----------|-----------------|
| Django | 4.2.23 (LTS) |
| PostgreSQL | 15 |
| Python | 3.12-slim (Docker) |
| Server | Nginx → Gunicorn → Django → PostgreSQL |
| Host | Dell PowerEdge R730, 84GB RAM |
| Public access | ngrok tunnel |
| Repo | github.com/argajitsarkr/phytosynergy-db-project |

---

## Phase 4 — AI-Assisted Extraction + Analytics Dashboard (2026-03-24 – ongoing)

### Enhancement 4: AI-Assisted PDF Data Extraction (`/extract/`)
- **Login-required page** for curators to upload research paper PDFs
- PyMuPDF extracts text → Google Gemini API structures it into JSON
- Editable review table with row selection before saving
- Full entity resolution on save (case-insensitive get_or_create, pathogen parsing, FIC auto-calc, Plant M2M linking)
- Gemini API key configurable via `GEMINI_API_KEY` environment variable

| Commit | Date | Description |
|--------|------|-------------|
| `c1d46aa` | 2026-03-24 | Add AI-assisted PDF data extraction page using Gemini API |
| `7a20a9d` | 2026-03-24 | Fix template error: rename underscore-prefixed variables |
| `90380c8` | 2026-03-24 | Increase Nginx client_max_body_size to 50M for PDF uploads |

### Enhancement 3: Interactive Analytics Dashboard (`/analytics/`)
- **Public page** with 7 real-time visualizations (Chart.js CDN)
- Synergy interpretation donut chart (Synergy/Additive/Indifference/Antagonism)
- ESKAPE pathogen experiment counts (horizontal bar)
- Top 10 phytochemicals by synergy count (horizontal bar)
- Top 10 antibiotics by synergy count (horizontal bar)
- Publication year trend (line chart with filled area)
- FIC index distribution histogram (color-coded by synergy zone)
- Phytochemical x Antibiotic heatmap (HTML table, interpolated color gradient)
- Custom template filter (`analytics_filters.py`) for heatmap FIC-to-color mapping
- Added to navbar for all users

| Commit | Date | Description |
|--------|------|-------------|
| `24312a9` | 2026-03-24 | Add interactive analytics dashboard with Chart.js visualizations |
| `56dcc51` | 2026-03-24 | Apply custom color palette to analytics dashboard |
| `2ae03fa` | 2026-03-25 | Revise analytics page to blue color palette |
| `b90acd1` | 2026-03-25 | Revert site-wide CSS to original blue theme |

### Enhancement 1: Schema Expansion — Plant Source + Cheminformatics
- **Plant model** with M2M relationship to Phytochemical (scientific_name, common_name, family)
- New Phytochemical fields: logp, num_rings, heavy_atom_count, lipinski_violations, is_drug_like
- New SynergyExperiment field: assay_method (checkerboard, time-kill, disk diffusion, etc.)
- `compute_properties` management command for batch RDKit cheminformatics computation
- Plant registered in Django admin with filter_horizontal M2M widget

| Commit | Date | Description |
|--------|------|-------------|
| `9062a89` | 2026-03-24 | Add Plant model, cheminformatics fields, assay_method, and RDKit compute command |
| `aa7d1ed` | 2026-03-24 | Fix rdkit package name for Python 3.12 compatibility |

---

## Phase 3 — Production Hardening + UX Fixes (2026-03-06 – 2026-03-07)

### Production Safety Scripts
- Automated DB backup, restore, and safe deploy scripts

### PubChem Auto-Enrichment
- Auto-fetch SMILES, molecular weight, InChI Key, Lipinski properties from PubChem on data entry
- Robust name lookup with POST fallback for tricky compound names
- ClassyFire chemical classification (superclass, class, subclass)
- Backfill enrichment management command for existing records

### Edit Entries
- Edit existing SynergyExperiment records (pre-populated form)
- Publication year field added

### UI Fixes
- Search result card alignment: widen MIC columns, prevent text stacking
- Fix CID removal from PubChem property list (was causing 400 error)

| Commit | Date | Description |
|--------|------|-------------|
| `e553539` | 2026-03-07 | Add production safety scripts |
| `2931ec4` | 2026-03-07 | Fix search result card alignment |
| `c871aee` | 2026-03-07 | Fix: Remove CID from PubChem property list |
| `46064b2` | 2026-03-07 | Fix: Robust PubChem name lookup with POST fallback |
| `2c10058` | 2026-03-06 | Add edit entries, publication year, and backfill enrichment command |
| `cb15767` | 2026-03-06 | Add migration for Phytochemical chemoinformatics fields |
| `b42d5f1` | 2026-03-06 | Add PubChem auto-enrichment, Lipinski profiling & ClassyFire classification |

---

## Phase 2 — Major Redesign + Features (2026-03-03 – 2026-03-05)

### DrugBank-Inspired Redesign
- Full UI overhaul: Black + Blue minimalistic palette
- Primary: #00447c (deep navy), Accent: #0b7b9e (teal)
- Font: Plus Jakarta Sans (300-800 weights)
- Bootstrap 5 + Font Awesome 6.5

### New Features
- 3Dmol.js embedded molecular structure viewer
- REST API endpoints (`/api/v1/experiments/`, `/api/v1/statistics/`)
- CSV data export (`/database/download/`)
- API documentation page (`/api/docs/`)
- Advanced search with ESKAPE pathogen filters, interpretation filters, chemical class filters
- Hero section with background image and dark overlay
- Site view counter

### Infrastructure
- Switched from Cloudflare Tunnel to ngrok for public access
- Updated production credentials for Docker deployment on 192.168.1.35
- Site logo added

| Commit | Date | Description |
|--------|------|-------------|
| `3ac9cd0` | 2026-03-05 | Add embedded 3Dmol.js molecular structure viewer |
| `999ebe9` | 2026-03-05 | Apply Black+Blue minimalistic palette |
| `2e9d38a` | 2026-03-03 | DrugBank-inspired redesign with API, CSV export, and schema docs |
| `8732102` | 2026-03-05 | Replace Cloudflare tunnel with ngrok |
| `ac4fc9b` | 2026-03-05 | Update site logo |

---

## Phase 1 — Initial Build + Deployment (2025-08-14 – 2026-03-03)

### Project Creation
- Django 4.2 project with `synergy_data` app
- Database schema: AntibioticClass, Phytochemical, Antibiotic, Pathogen, Source, SynergyExperiment
- FIC auto-calculation and interpretation auto-derivation
- Case-insensitive entity resolution
- Pathogen name parsing (genus/species/strain)

### Deployment
- Docker Compose setup (Nginx + Gunicorn + PostgreSQL 15)
- Initially targeted Railway, later moved to self-hosted Dell PowerEdge R730
- Production settings with dj-database-url

### Complete Website Build
- Home page with stats
- Database search and browse
- Data entry form (login-protected)
- About page
- Django admin registration

| Commit | Date | Description |
|--------|------|-------------|
| `ea97e93` | 2025-08-14 | Initial commit of PhytoSynergyDB project |
| `156099c` | 2026-01-19 | Add Docker configuration for production deployment |
| `ac81c72` | 2026-02-22 | Complete website build — all 4 pages, data import, production config |
| `a917b5a` | 2026-03-03 | Add home page redesign, data entry system |

---

## Known Limitations

1. No HTTPS (runs on HTTP port 80, ngrok provides HTTPS on tunnel)
2. No pagination on search results
3. No bulk import (except PDF extraction via Gemini)
4. No compound/pathogen/antibiotic detail pages
5. Secrets hardcoded in docker-compose.yml (should move to .env)
6. RDKit `compute_properties` command requires manual run

---

## Deployment Checklist (for new updates)

```bash
# On server (Dell PowerEdge R730, via AnyDesk)
cd ~/Desktop/Database/phytosynergy-project
git pull origin main
docker compose up -d --build
docker compose exec web python manage.py migrate          # if schema changed
docker compose exec web python manage.py collectstatic --noinput
```

---

## Design System Reference

| Token | Value |
|-------|-------|
| Primary | #00447c (deep navy) |
| Accent | #0b7b9e (teal) |
| Dark | #212121 |
| Font | Plus Jakarta Sans (300-800) |
| CSS | Bootstrap 5 |
| Icons | Font Awesome 6.5 |
| Synergy badge | green (#2e7d32) |
| Additive badge | orange (#e65100) |
| Indifference badge | gray (#757575) |
| Antagonism badge | red (#c62828) |

---

*Last updated: 2026-03-25*
