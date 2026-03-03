# PhytoSynergyDB — System Architecture & Database Schema

**For Manuscript Reference**

---

## 1. System Overview

PhytoSynergyDB is a web-based, curated relational database dedicated to synergistic interactions between phytochemicals (plant-derived compounds) and conventional antibiotics against ESKAPE pathogens. The system is designed for academic researchers studying antimicrobial resistance (AMR) and provides structured, peer-reviewed synergy data through both a web interface and a REST API.

### 1.1 Technology Stack

| Layer | Technology | Version | Role |
|-------|-----------|---------|------|
| **Backend Framework** | Django | 4.2 | Web application framework, ORM, routing, authentication |
| **Programming Language** | Python | 3.12 | Server-side logic, data processing |
| **Database** | PostgreSQL | 15 | Relational data storage with ACID compliance |
| **Frontend** | HTML5, CSS3, JavaScript | — | User interface, responsive design |
| **CSS Framework** | Bootstrap | 5 | Responsive grid, UI components |
| **Web Server** | Nginx | 1.25 | Reverse proxy, static file serving |
| **WSGI Server** | Gunicorn | 23.0 | Python WSGI HTTP server |
| **Containerization** | Docker + Docker Compose | — | Deployment orchestration |

### 1.2 Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                         │
│                                                             │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐ │
│   │  Web Browser  │  │  Python/R    │  │  curl/HTTP       │ │
│   │  (HTML/CSS/JS)│  │  Scripts     │  │  Client          │ │
│   └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘ │
└──────────┼─────────────────┼───────────────────┼───────────┘
           │                 │                   │
           ▼                 ▼                   ▼
┌─────────────────────────────────────────────────────────────┐
│                     PRESENTATION LAYER                      │
│                                                             │
│   ┌─────────────────────────────────────────────────────┐   │
│   │              Nginx Reverse Proxy (:80)              │   │
│   │   • Static file serving (/static/)                  │   │
│   │   • Request proxying to Gunicorn                    │   │
│   └──────────────────────┬──────────────────────────────┘   │
└──────────────────────────┼──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    APPLICATION LAYER                         │
│                                                             │
│   ┌─────────────────────────────────────────────────────┐   │
│   │             Gunicorn WSGI Server (:8000)             │   │
│   └──────────────────────┬──────────────────────────────┘   │
│                          │                                  │
│   ┌──────────────────────┴──────────────────────────────┐   │
│   │              Django Application                      │   │
│   │                                                      │   │
│   │  ┌────────────┐  ┌────────────┐  ┌──────────────┐  │   │
│   │  │   URL      │  │   Views    │  │  Templates   │  │   │
│   │  │   Router   │──│  (Logic)   │──│  (HTML)      │  │   │
│   │  └────────────┘  └─────┬──────┘  └──────────────┘  │   │
│   │                        │                             │   │
│   │  ┌─────────────┐  ┌───┴────────┐  ┌─────────────┐  │   │
│   │  │   Forms     │  │   Models   │  │   Context    │  │   │
│   │  │ (Validation)│  │   (ORM)    │  │  Processors  │  │   │
│   │  └─────────────┘  └─────┬──────┘  └─────────────┘  │   │
│   └──────────────────────────┼──────────────────────────┘   │
└──────────────────────────────┼──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                       DATA LAYER                            │
│                                                             │
│   ┌─────────────────────────────────────────────────────┐   │
│   │          PostgreSQL Database (:5432)                 │   │
│   │                                                      │   │
│   │   Tables: AntibioticClass, Phytochemical,            │   │
│   │           Antibiotic, Pathogen, Source,               │   │
│   │           SynergyExperiment, SiteViewCounter         │   │
│   └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Database Schema (Entity-Relationship Model)

### 2.1 Entity-Relationship Diagram

```
┌─────────────────────┐
│  AntibioticClass    │
│─────────────────────│
│  PK  id             │
│      class_name     │         ┌──────────────────────┐
│      description    │         │  Source               │
└──────────┬──────────┘         │──────────────────────│
           │ 1                  │  PK  id              │
           │                    │      doi (unique)     │
           │ 0..*              │      pmid (unique)    │
┌──────────┴──────────┐         │      publication_year │
│  Antibiotic         │         │      article_title   │
│─────────────────────│         │      journal         │
│  PK  id             │         └──────────┬───────────┘
│      antibiotic_name│                    │ 1
│      drugbank_id    │                    │
│  FK  antibiotic_class────────►           │ 0..*
└──────────┬──────────┘         ┌──────────┴───────────┐
           │ 1                  │                      │
           │                    │                      │
           │ 0..*              │                      │
┌──────────┴──────────────────────────────────────────────┐
│                   SynergyExperiment                      │
│──────────────────────────────────────────────────────────│
│  PK  id                                                  │
│  FK  phytochemical ──────► Phytochemical                │
│  FK  antibiotic ─────────► Antibiotic                   │
│  FK  pathogen ───────────► Pathogen                     │
│  FK  source ─────────────► Source                       │
│      mic_phyto_alone      (Decimal, nullable)           │
│      mic_abx_alone        (Decimal, nullable)           │
│      mic_phyto_in_combo   (Decimal, nullable)           │
│      mic_abx_in_combo     (Decimal, nullable)           │
│      mic_units            (String, default: µg/mL)      │
│      fic_index            (Decimal, nullable, computed)  │
│      interpretation       (Enum: S/A/I/Ant, nullable)   │
│      moa_observed         (Text, nullable)               │
│      notes                (Text, nullable)               │
└──────────┬──────────────────────────────────────────────┘
           │ 0..*             │ 0..*
           │                  │
           │ 1                │ 1
┌──────────┴──────────┐ ┌─────┴────────────────┐
│  Phytochemical      │ │  Pathogen            │
│─────────────────────│ │──────────────────────│
│  PK  id             │ │  PK  id              │
│      compound_name  │ │      genus           │
│      pubchem_cid    │ │      species         │
│      canonical_smiles│ │      strain          │
│      inchi_key      │ │      gram_stain      │
│      molecular_weight│ │  UQ (genus,species,  │
└─────────────────────┘ │      strain)          │
                        └──────────────────────┘
```

### 2.2 Table Definitions

#### Table: `synergy_data_antibioticclass`
**Purpose:** Controlled vocabulary for antibiotic drug classes.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | BigAutoField | PK, auto-increment | Primary key |
| `class_name` | VARCHAR(100) | UNIQUE, NOT NULL | Antibiotic class name (e.g., "Beta-lactam", "Aminoglycoside", "Macrolide") |
| `description` | TEXT | NULLABLE | Description of the antibiotic class |

**Example records:** Beta-lactam, Aminoglycoside, Fluoroquinolone, Macrolide, Tetracycline

---

#### Table: `synergy_data_phytochemical`
**Purpose:** Chemical identity of plant-derived compounds.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | BigAutoField | PK | Primary key |
| `compound_name` | VARCHAR(255) | UNIQUE, NOT NULL | Common/IUPAC name of the phytochemical |
| `pubchem_cid` | INTEGER | UNIQUE, NULLABLE | PubChem Compound Identifier for cross-referencing |
| `canonical_smiles` | TEXT | NULLABLE | SMILES notation for chemical structure representation |
| `inchi_key` | VARCHAR(27) | UNIQUE, NULLABLE | InChI Key for unambiguous compound identification |
| `molecular_weight` | DECIMAL(10,4) | NULLABLE | Molecular weight in g/mol |

**Chemical identifier rationale:**
- **PubChem CID**: Links to the NCBI PubChem database for comprehensive chemical data
- **SMILES**: Enables computational chemistry applications (docking, QSAR)
- **InChI Key**: Provides a fixed-length, hash-based identifier for exact compound matching
- **Molecular Weight**: Enables dose-response normalization and pharmacokinetic calculations

---

#### Table: `synergy_data_antibiotic`
**Purpose:** Identity and classification of conventional antibiotics.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | BigAutoField | PK | Primary key |
| `antibiotic_name` | VARCHAR(255) | UNIQUE, NOT NULL | Name of the antibiotic (e.g., "Azithromycin") |
| `drugbank_id` | VARCHAR(50) | UNIQUE, NULLABLE | DrugBank identifier for cross-referencing drug data |
| `antibiotic_class_id` | INTEGER | FK → AntibioticClass, NULLABLE | Foreign key to antibiotic classification |

---

#### Table: `synergy_data_pathogen`
**Purpose:** Taxonomic identification of test organisms.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | BigAutoField | PK | Primary key |
| `genus` | VARCHAR(100) | NOT NULL | Taxonomic genus (e.g., "Pseudomonas") |
| `species` | VARCHAR(100) | NOT NULL | Taxonomic species (e.g., "aeruginosa") |
| `strain` | VARCHAR(100) | NULLABLE | Specific strain identifier (e.g., "ATCC 27853", "MTCC 2488") |
| `gram_stain` | VARCHAR(20) | NULLABLE | Gram staining classification ("Gram-positive" or "Gram-negative") |

**Unique constraint:** (`genus`, `species`, `strain`) — prevents duplicate strain entries.

**Normalization:** Empty strain strings are normalized to NULL on save to maintain unique constraint integrity.

---

#### Table: `synergy_data_source`
**Purpose:** Bibliographic metadata for the source publication.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | BigAutoField | PK | Primary key |
| `doi` | VARCHAR(255) | UNIQUE, NULLABLE | Digital Object Identifier for the publication |
| `pmid` | INTEGER | UNIQUE, NULLABLE | PubMed Identifier |
| `publication_year` | INTEGER | NULLABLE | Year of publication |
| `article_title` | TEXT | NULLABLE | Title of the scientific article |
| `journal` | VARCHAR(255) | NULLABLE | Name of the journal |

**Data provenance:** Every experiment record links to its source publication via DOI, ensuring full traceability and reproducibility — a critical requirement for scientific databases.

---

#### Table: `synergy_data_synergyexperiment` (Central Fact Table)
**Purpose:** The primary data table storing individual synergy assay results.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | BigAutoField | PK | Primary key |
| `phytochemical_id` | INTEGER | FK → Phytochemical, NOT NULL, CASCADE | Link to phytochemical |
| `antibiotic_id` | INTEGER | FK → Antibiotic, NOT NULL, CASCADE | Link to antibiotic |
| `pathogen_id` | INTEGER | FK → Pathogen, NOT NULL, CASCADE | Link to pathogen |
| `source_id` | INTEGER | FK → Source, NOT NULL, CASCADE | Link to source publication |
| `mic_phyto_alone` | DECIMAL(10,4) | NULLABLE | MIC of phytochemical tested alone |
| `mic_abx_alone` | DECIMAL(10,4) | NULLABLE | MIC of antibiotic tested alone |
| `mic_phyto_in_combo` | DECIMAL(10,4) | NULLABLE | MIC of phytochemical in combination |
| `mic_abx_in_combo` | DECIMAL(10,4) | NULLABLE | MIC of antibiotic in combination |
| `mic_units` | VARCHAR(20) | DEFAULT 'µg/mL' | Units for all MIC values in this record |
| `fic_index` | DECIMAL(10,4) | NULLABLE | Fractional Inhibitory Concentration index |
| `interpretation` | VARCHAR(20) | NULLABLE, ENUM | Synergy interpretation (see below) |
| `moa_observed` | TEXT | NULLABLE | Observed mechanism of action |
| `notes` | TEXT | NULLABLE | Additional notes or observations |

**Interpretation choices (controlled vocabulary):**

| Value | Label | FIC Range | Definition |
|-------|-------|-----------|------------|
| `Synergy` | Synergy (FIC ≤ 0.5) | FIC ≤ 0.5 | Combination significantly more effective than either agent alone |
| `Additive` | Additive (0.5 < FIC ≤ 1.0) | 0.5 < FIC ≤ 1.0 | Combined effect equals sum of individual effects |
| `Indifference` | Indifference (1.0 < FIC ≤ 4.0) | 1.0 < FIC ≤ 4.0 | No significant interaction effect |
| `Antagonism` | Antagonism (FIC > 4.0) | FIC > 4.0 | Combination less effective than individual agents |

**FIC Index Calculation:**
```
FIC Index = (MIC_phyto_combo / MIC_phyto_alone) + (MIC_abx_combo / MIC_abx_alone)
```

When all four MIC values are provided, the FIC index is automatically calculated. When the FIC index is computed, the interpretation is automatically derived using the standard thresholds above. Users may also manually provide FIC and/or interpretation values from the original publication.

---

#### Table: `synergy_data_siteviewcounter`
**Purpose:** Simple analytics counter for total page views.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | BigAutoField | PK | Primary key |
| `count` | PositiveInteger | DEFAULT 0 | Total page views across the site |

---

### 2.3 Relationship Summary

| Relationship | Type | Cardinality | Description |
|-------------|------|-------------|-------------|
| AntibioticClass → Antibiotic | One-to-Many | 1:0..* | One class contains many antibiotics |
| Phytochemical → SynergyExperiment | One-to-Many | 1:0..* | One compound appears in many experiments |
| Antibiotic → SynergyExperiment | One-to-Many | 1:0..* | One antibiotic appears in many experiments |
| Pathogen → SynergyExperiment | One-to-Many | 1:0..* | One pathogen appears in many experiments |
| Source → SynergyExperiment | One-to-Many | 1:0..* | One publication contains many experiments |

The schema follows a **star schema** pattern: `SynergyExperiment` is the central fact table, with dimension tables (`Phytochemical`, `Antibiotic`, `Pathogen`, `Source`) linked via foreign keys. This design:

1. **Eliminates redundancy** — compound and pathogen data stored once, referenced many times
2. **Enables multi-dimensional queries** — filter/aggregate across any dimension
3. **Supports data integrity** — foreign key constraints prevent orphaned records
4. **Facilitates normalization** — case-insensitive lookups prevent duplicate entities

---

## 3. Data Flow Architecture

### 3.1 Data Entry Flow

```
┌──────────────┐     ┌───────────────┐     ┌────────────────────────┐
│  Researcher  │────►│  Login Page   │────►│  Data Entry Form       │
│  (Browser)   │     │  (Auth Check) │     │  (SynergyEntryForm)    │
└──────────────┘     └───────────────┘     └──────────┬─────────────┘
                                                       │ POST
                                                       ▼
                                           ┌────────────────────────┐
                                           │  data_entry_view()     │
                                           │                        │
                                           │  1. Validate form      │
                                           │  2. Resolve Source     │
                                           │     (get_or_create     │
                                           │      by DOI)           │
                                           │  3. Parse pathogen     │
                                           │     name → genus,      │
                                           │     species, strain    │
                                           │  4. Resolve Pathogen   │
                                           │     (get_or_create)    │
                                           │  5. Resolve Phyto      │
                                           │     (case-insensitive) │
                                           │  6. Resolve Antibiotic │
                                           │     (case-insensitive) │
                                           │  7. Auto-calc FIC      │
                                           │  8. Auto-interpret     │
                                           │  9. Create experiment  │
                                           └──────────┬─────────────┘
                                                       │
                                                       ▼
                                           ┌────────────────────────┐
                                           │  PostgreSQL Database   │
                                           │                        │
                                           │  INSERT INTO           │
                                           │  synergy_experiment    │
                                           │  (phytochemical_id,    │
                                           │   antibiotic_id,       │
                                           │   pathogen_id,         │
                                           │   source_id, ...)      │
                                           └────────────────────────┘
```

### 3.2 Search & Query Flow

```
┌──────────────┐     ┌────────────────────────┐     ┌──────────────────┐
│  User Query  │────►│  Search Parameters      │────►│  Django ORM      │
│  (Browser)   │     │                         │     │  Query Builder   │
└──────────────┘     │  • query (text search)  │     │                  │
                     │  • interpretation (pill) │     │  Q(phyto__name   │
                     │  • eskape (genus filter) │     │    __icontains)  │
                     │  • pathogen (dropdown)   │     │  | Q(abx__name   │
                     │  • antibiotic (dropdown) │     │    __icontains)  │
                     │  • mechanism (dropdown)  │     │  | Q(pathogen    │
                     └─────────────────────────┘     │    __icontains)  │
                                                      └────────┬─────────┘
                                                               │
                                                               ▼
                                                      ┌──────────────────┐
                                                      │  PostgreSQL      │
                                                      │  SELECT with     │
                                                      │  JOINs across    │
                                                      │  all 4 dimension │
                                                      │  tables          │
                                                      └────────┬─────────┘
                                                               │
                                                               ▼
                                                      ┌──────────────────┐
                                                      │  Result Cards    │
                                                      │  (HTML template) │
                                                      │  or JSON (API)   │
                                                      └──────────────────┘
```

### 3.3 API Access Flow

```
┌──────────────────┐     ┌───────────────────────────┐
│  External Client │     │  /api/v1/experiments/      │
│  (Python, R,     │────►│                            │
│   curl, etc.)    │     │  Query params:             │
└──────────────────┘     │  ?interpretation=Synergy   │
                         │  &eskape=Staphylococcus    │
                         │  &limit=100&offset=0       │
                         └──────────────┬────────────┘
                                        │
                                        ▼
                         ┌───────────────────────────┐
                         │  api_experiments()         │
                         │                            │
                         │  Same filter pipeline      │
                         │  as web search             │
                         │  + Pagination (limit/      │
                         │    offset)                  │
                         │  + JSON serialization      │
                         └──────────────┬────────────┘
                                        │
                                        ▼
                         ┌───────────────────────────┐
                         │  JsonResponse              │
                         │  {                         │
                         │    "count": N,             │
                         │    "results": [...]        │
                         │  }                         │
                         └───────────────────────────┘
```

---

## 4. URL Routing Map

| URL Pattern | View Function | Method | Auth | Description |
|-------------|--------------|--------|------|-------------|
| `/` | `home_page` | GET | Public | Homepage with statistics, ESKAPE cards, recent entries |
| `/database/` | `database_search_page` | GET | Public | Search and filter interface |
| `/database/download/` | `download_data` | GET | Public | Download page and CSV export |
| `/about/` | `about_page` | GET | Public | About page with methodology |
| `/data-entry/` | `data_entry_view` | GET/POST | Login | Data entry form |
| `/api/v1/experiments/` | `api_experiments` | GET | Public | JSON API for experiments |
| `/api/v1/statistics/` | `api_statistics` | GET | Public | JSON API for statistics |
| `/api/docs/` | `api_docs` | GET | Public | API documentation page |
| `/accounts/login/` | LoginView | GET/POST | Public | Authentication |
| `/accounts/logout/` | LogoutView | POST | Login | Sign out |

---

## 5. Key Algorithms

### 5.1 FIC Index Auto-Calculation

```python
def auto_calculate_fic(mic_phyto_alone, mic_abx_alone,
                       mic_phyto_in_combo, mic_abx_in_combo):
    """
    FIC = (MIC_phyto_combo / MIC_phyto_alone) +
          (MIC_abx_combo / MIC_abx_alone)

    Returns None if any required value is missing or zero.
    Uses Python Decimal arithmetic for precision.
    """
    if all(v is not None and v > 0 for v in values):
        return (mic_phyto_in_combo / mic_phyto_alone) + \
               (mic_abx_in_combo / mic_abx_alone)
    return None
```

### 5.2 Synergy Interpretation

```python
def auto_interpret_fic(fic_index):
    """Standard thresholds per EUCAST/CLSI guidelines."""
    if fic_index <= 0.5:
        return 'Synergy'
    elif fic_index <= 1.0:
        return 'Additive'
    elif fic_index <= 4.0:
        return 'Indifference'
    else:
        return 'Antagonism'
```

### 5.3 Case-Insensitive Entity Resolution

```python
def get_or_create_case_insensitive(model, field_name, value):
    """
    Prevents duplicate entries due to capitalization differences.
    Uses __iexact lookup with IntegrityError fallback for
    race condition safety.

    Example: "vitexin", "Vitexin", "VITEXIN" → single record
    """
```

### 5.4 Pathogen Name Parsing

```python
def parse_pathogen_name(full_name):
    """
    Parses user input into structured taxonomic fields.

    "Pseudomonas aeruginosa MTCC 2488"
    → genus="Pseudomonas", species="aeruginosa", strain="MTCC 2488"

    "Staphylococcus aureus"
    → genus="Staphylococcus", species="aureus", strain=None
    """
```

---

## 6. Data Export Formats

### 6.1 CSV Export Schema

The CSV export includes all fields from the star schema denormalized into a flat table:

| Column | Source Table | Description |
|--------|-------------|-------------|
| Phytochemical | Phytochemical | Compound name |
| PubChem_CID | Phytochemical | PubChem identifier |
| InChI_Key | Phytochemical | Chemical identifier |
| SMILES | Phytochemical | Structure notation |
| Antibiotic | Antibiotic | Antibiotic name |
| DrugBank_ID | Antibiotic | DrugBank identifier |
| Antibiotic_Class | AntibioticClass | Drug class |
| Pathogen_Genus | Pathogen | Genus |
| Pathogen_Species | Pathogen | Species |
| Pathogen_Strain | Pathogen | Strain |
| Gram_Stain | Pathogen | Gram classification |
| MIC_Phyto_Alone | SynergyExperiment | MIC value (alone) |
| MIC_Abx_Alone | SynergyExperiment | MIC value (alone) |
| MIC_Phyto_Combo | SynergyExperiment | MIC value (combination) |
| MIC_Abx_Combo | SynergyExperiment | MIC value (combination) |
| MIC_Units | SynergyExperiment | Units |
| FIC_Index | SynergyExperiment | FIC index value |
| Interpretation | SynergyExperiment | Synergy interpretation |
| Mechanism_of_Action | SynergyExperiment | Observed MOA |
| Notes | SynergyExperiment | Additional notes |
| DOI | Source | Publication DOI |
| PMID | Source | PubMed ID |
| Journal | Source | Journal name |
| Publication_Year | Source | Year |

### 6.2 JSON API Response Schema

```json
{
  "count": "integer — total matching records",
  "limit": "integer — page size",
  "offset": "integer — starting position",
  "results": [
    {
      "id": "integer",
      "phytochemical": {
        "name": "string",
        "pubchem_cid": "integer|null",
        "inchi_key": "string|null",
        "smiles": "string|null",
        "molecular_weight": "string|null"
      },
      "antibiotic": {
        "name": "string",
        "drugbank_id": "string|null",
        "class": "string|null"
      },
      "pathogen": {
        "genus": "string",
        "species": "string",
        "strain": "string|null",
        "gram_stain": "string|null"
      },
      "mic_phyto_alone": "string|null",
      "mic_abx_alone": "string|null",
      "mic_phyto_in_combo": "string|null",
      "mic_abx_in_combo": "string|null",
      "mic_units": "string",
      "fic_index": "string|null",
      "interpretation": "string|null",
      "mechanism_of_action": "string|null",
      "source": {
        "doi": "string|null",
        "pmid": "integer|null",
        "journal": "string|null",
        "year": "integer|null",
        "title": "string|null"
      }
    }
  ]
}
```

---

## 7. Security & Authentication

| Feature | Implementation |
|---------|---------------|
| Authentication | Django's built-in auth system (session-based) |
| Protected views | `@login_required` decorator on data entry |
| CSRF protection | Django middleware + `{% csrf_token %}` in forms |
| SQL injection prevention | Django ORM parameterized queries |
| XSS protection | Django template auto-escaping |
| Clickjacking protection | `X-Frame-Options` middleware |
| Session security | Secure session cookies in production |

---

## 8. Deployment Architecture

```
┌─────────────────────────────────────────────────────┐
│              Docker Compose Stack                    │
│                                                     │
│  ┌─────────┐    ┌──────────┐    ┌───────────────┐  │
│  │  Nginx  │───►│  Django   │───►│  PostgreSQL   │  │
│  │  :80    │    │  Gunicorn │    │  :5432        │  │
│  │         │    │  :8000    │    │               │  │
│  └─────────┘    └──────────┘    └───────────────┘  │
│       │                               │             │
│       ▼                               ▼             │
│  /staticfiles/                  pgdata volume       │
│  (collected)                    (persistent)        │
└─────────────────────────────────────────────────────┘
```

---

## 9. Cross-Reference to External Databases

| Identifier | External Database | Purpose |
|-----------|-------------------|---------|
| PubChem CID | NCBI PubChem | Chemical properties, bioassays, 3D structures |
| InChI Key | IUPAC InChI | Unambiguous compound identification |
| SMILES | — | Computational chemistry, molecular docking |
| DrugBank ID | DrugBank | Drug pharmacology, targets, interactions |
| DOI | CrossRef/DataCite | Publication access and verification |
| PMID | NCBI PubMed | Publication indexing and retrieval |

---

*Document generated for manuscript preparation. Last updated: 2026.*
