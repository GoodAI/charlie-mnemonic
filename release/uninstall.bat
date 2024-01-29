@echo off
setlocal
set HOME=%USERPROFILE%

echo Stopping and removing Charlie Mnemonic containers...
docker-compose down

echo Removing Docker images for Charlie Mnemonic...
docker rmi goodaidev/charlie-mnemonic:latest
docker rmi postgres:14

echo Removing any stopped containers...
docker container prune -f

echo Cleaning up unused Docker networks...
docker network prune -f

echo Cleaning up unused Docker images...
docker image prune -f

echo Uninstallation complete. User data has been preserved.

endlocal