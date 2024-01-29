@echo off
echo Stopping current Charlie Mnemonic containers...
docker-compose down

echo Pulling the latest images...
docker-compose pull

echo Containers have been updated. Please start the application again using start.bat.
