**(Create a new file named `DEVELOPMENT.md`)**

This explains the architecture and how to make changes.

```markdown
# PhytoSynergyDB: Development & Architecture Guide

This document explains the project's architecture, the development workflow, and how the frontend and backend are connected.

### Local Development Setup

To make changes to the application, you must set up a local development environment on your personal computer.

1.  **Prerequisites:** Python 3.12+, PostgreSQL.
2.  **Clone Repository:** `git clone https://github.com/argajitsarkr/phytosynergy-db-project.git`
3.  **Install Dependencies:** `pip install -r requirements.txt`
4.  **Database Setup:** Create a local PostgreSQL database named `phytosynergy_db`.
5.  **Configure `settings.py`:** Your local `settings.py` file has a section to connect to your local database if a `DATABASE_URL` environment variable is not found.
6.  **Run Local Server:** Use the development server for testing: `py manage.py runserver`.

### The Development Cycle: How to Make Changes

**Never edit code directly on the production server.**

1.  **Develop Locally:** Make all code changes (Python, HTML, CSS) on your local machine.
2.  **Test Locally:** Run the local server (`py manage.py runserver`) and test your changes thoroughly in your browser at `http://127.0.0.1:8000`.
3.  **Commit to Git:** Once you are satisfied, commit your changes with a clear message.
    ```bash
    git add .
    git commit -m "Feature: Added a new chart to the results page"
    ```
4.  **Push to GitHub:** Push your commit to the central repository.
    ```bash
    git push origin main
    ```
5.  **Deploy:** The production server can now be updated by pulling these changes (`git pull`) and restarting the Docker containers.

### Architecture: How Frontend and Backend Connect

The project uses the **Django MVT (Model-View-Template)** architecture.

1.  **Model (`models.py`): The Data Blueprint.**
    *   Python classes that define the structure of our database tables (e.g., `Phytochemical`).
    *   This is Django's **ORM (Object-Relational Mapper)**, which translates Python code into SQL.

2.  **View (`views.py`): The Brains.**
    *   A Python function that receives a user's web request.
    *   It uses the Models to perform database operations (e.g., `SynergyExperiment.objects.filter(...)`).
    *   It prepares the data and sends it to a template.

3.  **Template (`.html` files): The Skeleton.**
    *   An HTML file that receives data from the view.
    *   It uses template tags (`{{ }}` and `{% %}`) to dynamically display the data and render the final webpage.

**Example Flow for a Search Request:**
1.  **User** visits `/database/` and submits a search.
2.  **URL Router (`urls.py`)** directs the request to the `database_search_page` view.
3.  **The View (`views.py`)** gets the search query, uses the `SynergyExperiment` model to filter the database, and gets a list of results.
4.  **The View** passes this list of results to the `database_search.html` template.
5.  **The Template** loops through the results, rendering an HTML "card" for each one.
6.  The final, complete **HTML page** is sent back to the user's browser.

**Static Files (CSS, Images):**
*   Custom styles and images are stored in the `synergy_data/static/` directory.
*   During production deployment, the `collectstatic` command gathers all static files into a single volume that the **Nginx** web server can serve efficiently.