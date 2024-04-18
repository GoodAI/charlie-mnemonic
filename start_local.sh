#!/bin/bash

# This takes the current user's home directory and sets the CHARLIE_USER_DIR to be in the .local/share/charlie-mnemonic/users directory
# note when running as root, the $HOME variable will be /root, so the CHARLIE_USER_DIR will be /root/.local/share/charlie-mnemonic/users
export HOME=${HOME:-$(eval echo ~$USER)}
export CHARLIE_USER_DIR=${HOME}/.local/share/charlie-mnemonic/users

# Set URL
URL="http://localhost:8002"

if [ ! -f .env ]; then
    echo "Creating .env file..."
    touch .env
fi

echo "Checking if docker is installed..."
docker --version || { echo "Failed to find docker, is it installed?"; exit 1; }

echo "Checking if docker daemon is running..."
docker info || { echo "Docker Compose failed with error level $?, is docker desktop running?"; exit 1; }

echo "Starting Charlie Mnemonic using Docker Compose..."
echo "First run takes a while"
docker-compose up --build || { echo "Docker Compose failed with error level $?."; exit 1; }

# Check loop
while true; do
    echo "Checking if Charlie Mnemonic started"
    if curl --output /dev/null --silent --head --fail "$URL"; then
        echo "Charlie Mnemonic is up! Opening $URL in the default browser..."
        sleep 1
        xdg-open "$URL"
        docker logs -f charlie-mnemonic
        docker-compose down
        exit 0
    else
        echo "Not available yet. Retrying in 5 seconds..."
        sleep 5
    fi
    
    # Check if the Docker container is still running
    if [ $(docker ps -q -f name=charlie-mnemonic | wc -l) -eq 0 ]; then
        echo "Charlie Mnemonic has been stopped."
        exit 0
    fi
done