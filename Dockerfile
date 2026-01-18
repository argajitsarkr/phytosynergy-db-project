# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set environment variables for Python
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory inside the container
WORKDIR /app

# Install system dependencies that might be needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the project files into the container
COPY . /app/

# Expose the port Gunicorn will run on
EXPOSE 8000

# The command to run when the container starts
# We add --no-input to collectstatic for non-interactive environments
CMD sh -c "python manage.py collectstatic --no-input && gunicorn phytosynergy_project.wsgi:application --bind 0.0.0.0:8000"