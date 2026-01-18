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

### Step 2: Configure Environment Variables
The docker-compose.yml file requires you to set passwords and a secret key. You must configure these before launching.
Change the placeholders directly in the docker-compose.yml file for POSTGRES_PASSWORD, DATABASE_URL, and DJANGO_SECRET_KEY.
Ensure DEBUG=0 for a production environment.

### Step 3: Build and Launch the Application
Use Docker Compose to build the images and start the containers.
code
Bash
# This command will build the Django image, download Postgres & Nginx,
# and start all three services in the background.
sudo docker-compose up --build -d

### Step 4: Post-Deployment Database Setup
The first time you launch, you must initialize the database inside the running containers.
Run Migrations: Create the database tables.
code
Bash
sudo docker-compose exec web python manage.py migrate
Create Superuser: Create your administrator account to access the Django Admin.
code
Bash
sudo docker-compose exec web python manage.py createsuperuser

### Step 5: Accessing the Application
* Your application is now live!
* Website: http://<your_server_ip>
* Admin Panel: http://<your_server_ip>/admin
## Managing the Application
To check the status of your containers: sudo docker-compose ps
To view logs: sudo docker-compose logs -f
To stop the application: sudo docker-compose down
To update the application: Pull the latest code (git pull origin main) and then rebuild and restart (sudo docker-compose up --build -d)