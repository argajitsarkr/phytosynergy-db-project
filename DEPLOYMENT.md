# PhytoSynergyDB: Deployment Guide

This guide provides step-by-step instructions for deploying the PhytoSynergyDB application on a production server. The application is designed to run in a containerized environment using Docker and Docker Compose.

### Prerequisites

*   A server running a modern Linux distribution (e.g., Ubuntu 22.04 LTS).
*   **Docker** and **Docker Compose** installed on the server.
*   **Git** installed on the server.
*   Firewall configured to allow traffic on port `80` (HTTP).

### Step 1: Clone the Repository

Clone the project from GitHub into your desired directory on the server.

```bash
git clone https://github.com/argajitsarkr/phytosynergy-db-project.git phytosynergy-project
cd phytosynergy-project