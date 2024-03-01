@echo off
setlocal
set URL=http://localhost:8002
set HOME=%USERPROFILE%
set CHARLIE_MNEMONIC_USER_DIR=%HOME%\AppData\Roaming\charlie-mnemonic\users
if not exist "%CHARLIE_MNEMONIC_USER_DIR%" mkdir "%CHARLIE_MNEMONIC_USER_DIR%"

echo Checking if docker is installed
docker --version > NUL 2>&1

if not %ERRORLEVEL% == 0 (
    echo Failed to find docker, is it installed?
    exit /b %ERRORLEVEL%
)


echo Checking if docker daemon is running
docker info > NUL 2>&1

if not %ERRORLEVEL% == 0 (
    echo Docker Compose failed with error level %ERRORLEVEL%, is docker desktop running?
    exit /b %ERRORLEVEL%
)


echo Starting Charlie Mnemonic using Docker Compose...
echo First run takes a while
docker-compose --project-name charlie-mnemonic-windows up --detach

rem Check the error level of the docker-compose command
if not %ERRORLEVEL% == 0 (
    echo Docker Compose failed with error level %ERRORLEVEL%.
    exit /b %ERRORLEVEL%
)

:CheckLoop
echo Checking if the Charlie Mnemonic started
powershell -Command "(Invoke-WebRequest -Uri %URL% -UseBasicParsing -TimeoutSec 2).StatusCode" 1>nul 2>nul
if %errorlevel%==0 (
    echo Charlie Mnemonic is up! Opening %URL% in the default browser!
    timeout /t 1 /nobreak >nul
    start %URL%
    docker logs -f charlie-mnemonic
	docker-compose --project-name charlie-mnemonic-windows down
) else (
    echo Not available yet. Retrying in 5 seconds...
    timeout /t 5 /nobreak >nul
    goto CheckLoop
)

endlocal