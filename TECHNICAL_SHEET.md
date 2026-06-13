# PhytoSynergyDB - Technical Sheet

> Reference technical specification for manuscript preparation.
> Statistics are live values as of 2026-06-12. All facts verified against the
> source code and the live API. Replace dated figures before submission.

---

## 1. Resource overview and availability

| Item | Detail |
|------|--------|
| Name | PhytoSynergyDB |
| Scope | Phytochemical-antibiotic synergy experiments against ESKAPE pathogens |
| URL | https://phytosynergydb.in |
| REST API | https://phytosynergydb.in/api/v1/ |
| Source code | https://github.com/argajitsarkr/phytosynergy-db-project |
| License | Software: MIT; Data: CC-BY-4.0 |
| Access model | Open, read-only public access; closed expert curation (no public submission) |
| Hosting | Self-hosted, Dell PowerEdge R730 (84 GB RAM), public via Cloudflare Tunnel |

---

## 2. System architecture

| Layer | Technology | Version |
|-------|-----------|---------|
| Web framework | Django (Python 3.12) | 4.2.23 LTS |
| Database | PostgreSQL | 15 |
| WSGI app server | Gunicorn (3 workers, 120 s timeout) | 23.0.0 |
| Reverse proxy / static serving | Nginx | latest |
| Containerization | Docker Compose (4 services: db, web, nginx, tunnel) | - |
| Public ingress | Cloudflare Tunnel (cloudflared), TLS at edge, HSTS | - |
| Frontend | Bootstrap 5, Chart.js (analytics), 3Dmol.js (3D viewer) | - |
| Cheminformatics | RDKit | >= 2024.3.1 |
| Ingest / parse | openpyxl, csv, BeautifulSoup4 | - |
| External annotation | PubChem PUG REST, ClassyFire (Wishart Lab + GNPS fallback) | - |

Request path: client -> Cloudflare edge (TLS) -> Cloudflare Tunnel -> Nginx
-> Gunicorn (Django) -> PostgreSQL.

---

## 3. Database schema (relational data model)

Eight tables: a central fact table (`SynergyExperiment`) with foreign keys to
normalized dimension tables.

### SynergyExperiment (fact table)

- Foreign keys -> `Phytochemical`, `Antibiotic`, `Pathogen`, `Source` (all CASCADE)
- `mic_phyto_alone`, `mic_abx_alone`, `mic_phyto_in_combo`, `mic_abx_in_combo`: DECIMAL(10,4), nullable
- `mic_units`: default `ug/mL`
- `fic_index`: DECIMAL(10,4), auto-computed
- `interpretation`: controlled vocabulary (Synergy / Additive / Indifference / Antagonism)
- `assay_method`: controlled vocabulary (see Section 4)
- `moa_observed`: free text (observed mechanism of action)
- `notes`: free text

### Phytochemical

- `compound_name` (unique), `pubchem_cid` (unique), `inchi_key` (unique, 27 char), `canonical_smiles`
- PubChem-derived: `molecular_weight`, `molecular_formula`, `xlogp`, `hbd`, `hba`, `tpsa`, `rotatable_bonds`
- RDKit-computed: `logp` (Wildman-Crippen), `num_rings`, `heavy_atom_count`, `lipinski_violations`, `is_drug_like`
- ClassyFire taxonomy: `chemical_superclass`, `chemical_class`, `chemical_subclass`

### Antibiotic

- `antibiotic_name` (unique), `drugbank_id` (unique), foreign key -> `AntibioticClass`

### AntibioticClass

- `class_name` (unique), `description`

### Pathogen

- `genus`, `species`, `strain`, `gram_stain`
- Unique constraint on (`genus`, `species`, `strain`)

### Source

- `doi` (unique), `pmid` (unique), `publication_year`, `article_title`, `journal`

### Plant

- `scientific_name` (unique), `common_name`, `family`
- Many-to-many -> `Phytochemical` (source plant of a compound)

---

## 4. Controlled vocabularies and data standards

- FIC interpretation (4 classes): Synergy (FIC <= 0.5), Additive (0.5 < FIC <= 1.0), Indifference (1.0 < FIC <= 4.0), Antagonism (FIC > 4.0)
- Assay method (5 classes): Checkerboard, Time-Kill, Disk Diffusion, Broth Microdilution, Other
- MIC units: default ug/mL, overridable per record
- Provenance: every record links to a DOI- or PMID-identified peer-reviewed source

---

## 5. Synergy quantification (FIC index)

The Fractional Inhibitory Concentration (FIC) index is computed automatically
when all four MIC values are present and non-zero:

```
FIC = (MIC_phyto_combo / MIC_phyto_alone) + (MIC_abx_combo / MIC_abx_alone)
```

Interpretation is then derived from the thresholds in Section 4. Records
lacking any of the four MIC values retain a curator-supplied FIC and
interpretation where available.

---

## 6. Chemical annotation pipeline (automated, offline)

Enrichment runs as out-of-request management commands (never inside a user
request, to avoid blocking the single-threaded request path):

1. PubChem PUG REST (5 s timeout): CID, CanonicalSMILES, InChIKey, MolecularWeight, MolecularFormula, XLogP, HBondDonorCount, HBondAcceptorCount, TPSA, RotatableBondCount
2. ClassyFire (Wishart Lab `entities`, with GNPS `structure.gnps2.org` fallback; 8 s timeout): chemical superclass / class / subclass
3. RDKit batch: Wildman-Crippen LogP, ring count, heavy-atom count, Lipinski Rule-of-Five violations
4. Lipinski Rule of Five flag: MW < 500, LogP < 5, HBD <= 5, HBA <= 10; classified drug-like if <= 1 violation

All external calls are best-effort and fail silently so curation is never
blocked by third-party service issues.

---

## 7. Database content (live, 2026-06-12)

| Metric | Count |
|--------|-------|
| Synergy experiments | 309 |
| Unique phytochemicals | 43 |
| Unique antibiotics | 43 |
| Pathogen strains | 149 |
| Source publications | 33 |

Interpretation distribution: Synergy 166 (53.7%), Additive 83, Indifference 50,
Antagonism 9 (308 classified; 1 record uninterpreted).

Experiments per ESKAPE genus: S. aureus 85, K. pneumoniae 72, P. aeruginosa 55,
A. baumannii 16, E. faecium 13, Enterobacter spp. 1.

---

## 8. Web interface

- Faceted search: free-text query plus filters on pathogen, FIC interpretation, ESKAPE membership, and chemical class
- CSV export of any filtered subset
- Analytics dashboard (Chart.js): top compounds and antibiotics, FIC-class breakdown, ESKAPE coverage, compound-by-antibiotic synergy heatmap
- 3D molecular viewer (3Dmol.js) rendered from stored SMILES
- Curator tools (authenticated): single-record entry form and bulk CSV/XLSX import with column-alias mapping, per-row validation, encoding repair, range/inequality normalization, and duplicate detection (atomic per-row transactions)

---

## 9. Programmatic access (REST API)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/experiments/` | GET | Paginated, filterable experiments (JSON) |
| `/api/v1/statistics/` | GET | Aggregate counts and distributions (JSON) |

- Pagination: `limit` (default 100, max 500), `offset`; response includes `count`, `limit`, `offset`, `results`
- Record payload: nested phytochemical (identifiers, physicochemical properties, chemical taxonomy), antibiotic (with class), pathogen (with gram stain), all four MIC values plus units, FIC index, interpretation, mechanism of action, and full source citation (DOI/PMID/journal/year/title)

---

## 10. Deployment, security and sustainability

- Immutable container images (application code baked in at build); reproducible via Docker Compose
- Production hardening: `DEBUG=0`, HSTS (1 year, includeSubDomains), secure and HttpOnly cookies, `X-Frame-Options: DENY`, content-type nosniff, referrer policy, server-token suppression
- Crawler policy: search engines and AI citation bots permitted; AI-training crawlers and bulk-data endpoints disallowed; XML sitemap, robots.txt, llms.txt, and schema.org Dataset structured data published

---

## 11. Items to supply before submission

These require author input and are not derivable from the code:

- Curation protocol: inclusion/exclusion criteria, number of papers screened versus included, literature date range, and any inter-curator agreement measure
- A citation and DOI for the database release (v1.0 pending)
- Author list and affiliations
- Funding and acknowledgements
