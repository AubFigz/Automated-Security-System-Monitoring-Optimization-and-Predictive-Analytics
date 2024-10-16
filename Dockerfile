# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set environment variables
ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1
ENV CI=true  # Set environment variable for CI

# Set the working directory
WORKDIR /app

# Install system dependencies (Git, curl, cron, etc.)
RUN apt-get update && apt-get install -y \
    cron \
    libpq-dev gcc \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements.txt to the container
COPY requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install testing and CI/CD dependencies (pytest, pytest-cov for test coverage)
RUN pip install pytest pytest-cov

# Copy the rest of the application code
COPY . /app

# Setup the cron job for automation (Phase 4)
COPY ./crontab /etc/cron.d/security-system-cron
RUN chmod 0644 /etc/cron.d/security-system-cron
RUN crontab /etc/cron.d/security-system-cron

# Make sure the cron service runs in the background
RUN touch /var/log/cron.log

# Expose necessary ports for Prometheus, Grafana, and Dash web app
EXPOSE 8000 8050 9090 3000

# Run tests as part of the CI/CD pipeline
RUN pytest --cov=./

# Start the cron service and the app itself
CMD cron && python3 system_health_monitor.py
