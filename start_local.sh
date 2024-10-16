#!/bin/bash

# This script sets up and runs the Charlie Mnemonic application using Docker Compose

# Export home directory
export HOME=${HOME:-$(eval echo ~$USER)}
export CHARLIE_USER_DIR=${HOME}/.local/share/charlie-mnemonic/users

# Set URL for health check
URL="http://localhost:8002"

# Check if Docker is installed
echo "Checking if Docker is installed..."
docker --version || { echo "Failed to find Docker. Please install Docker before running this script."; exit 1; }

# Check if Docker daemon is running
echo "Checking if Docker daemon is running..."
docker info || { echo "Docker daemon is not running. Please start Docker before running this script."; exit 1; }

# Ensure that Docker Compose is not already running using the same names
echo "Stopping existing Docker containers to prevent name conflicts..."
docker compose down || true

# Attempt to remove containers explicitly, suppressing errors for non-existing containers
docker rm -f charlie-mnemonic psdb charlie-mnemonic-python-env || true

# Check if required files exist and create if necessary
if [ ! -f .env ]; then
    echo "Creating .env file..."
    touch .env
fi

# Start the application using Docker Compose
echo "Starting Charlie Mnemonic using Docker Compose. First run may take a while..."
docker compose up --build || { echo "Docker Compose failed with error level $?."; exit 1; }

# Monitoring loop to check if the application is running
while true; do
    echo "Checking if Charlie Mnemonic started..."
    if curl --output /dev/null --silent --head --fail "$URL"; then
        echo "Charlie Mnemonic is up! Opening $URL in the default browser..."
        sleep 1
        xdg-open "$URL"
        docker logs -f charlie-mnemonic
        docker compose down
        exit 0
    else
        echo "Charlie Mnemonic is not available yet. Retrying in 5 seconds..."
        sleep 5
    fi

    # Check if the Docker container is still running
    if [ $(docker ps -q -f name=charlie-mnemonic | wc -l) -eq 0 ]; then
        echo "Charlie Mnemonic has stopped unexpectedly."
        exit 0
    fi
done
