# PhytoSynergyDB: A Curated Database of Phytochemical-Antibiotic Synergy

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![Django Version](https://img.shields.io/badge/django-5.2-green.svg)](https://www.djangoproject.com/)
[![Database](https://img.shields.io/badge/database-PostgreSQL-blue.svg)](https://www.postgresql.org/)

PhytoSynergyDB is a specialized, open-source, and curated database dedicated to synergistic interactions between phytochemicals and conventional antibiotics against ESKAPE pathogens. This platform aims to accelerate antimicrobial resistance (AMR) research by providing a centralized, structured, and searchable repository of high-quality experimental data.

**Live Application:** `http://your_server_ip_or_domain.com` (Coming Soon)

---

### Key Features

*   **Curated Data:** All data is manually extracted from peer-reviewed scientific literature.
*   **Structured Schema:** Detailed information on phytochemicals, antibiotics, pathogens, MIC/FIC values, and mechanisms of action.
*   **Advanced Search:** A modern, multi-faceted search interface to filter and explore the database.
*   **Built for Science:** Designed to be a citable, reliable resource for researchers, students, and clinicians.
*   **Dockerized Deployment:** The entire application stack is containerized for robust, reproducible, and isolated deployment.

### Technology Stack

*   **Backend:** Django & Python
*   **Database:** PostgreSQL
*   **Frontend:** HTML, CSS, Bootstrap 5
*   **Deployment:** Docker, Docker Compose, Nginx, Gunicorn

### Quick Start (for Deployment)

For a complete guide on deploying this application, please see the [**Deployment Guide**](DEPLOYMENT.md).

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/argajitsarkr/phytosynergy-db-project.git
    cd phytosynergy-db-project
    ```
2.  **Configure Environment:** Create and configure the `.env` file as described in the deployment guide.
3.  **Launch with Docker:**
    ```bash
    docker-compose up --build -d
    ```

### How to Cite

If you use PhytoSynergyDB in your research, please cite our upcoming publication:
> *(Your Paper's Citation Will Go Here Once Published)*

### Documentation

*   [**Development & Architecture Guide**](DEVELOPMENT.md): Learn how the code works and how to contribute.
*   [**Deployment Guide**](DEPLOYMENT.md): A step-by-step guide to hosting the application.
*   [**Data Curation Protocol**](CURATION.md): The official SOP for data collection and validation.