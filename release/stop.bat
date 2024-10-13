@echo off
setlocal
set URL=http://localhost:8002
set HOME=%USERPROFILE%
set CHARLIE_MNEMONIC_USER_DIR=%HOME%\AppData\Roaming\charlie-mnemonic\users

echo Stopping Charlie Mnemonic using Docker Compose...
docker compose --project-name charlie-mnemonic-windows down

endlocal