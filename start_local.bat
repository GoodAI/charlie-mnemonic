@echo off
setlocal enabledelayedexpansion

echo Script started
echo Command line: %0 %*

set URL=http://localhost:8002
set HOME=%USERPROFILE%
set CHARLIE_USER_DIR=%HOME%\AppData\Roaming\charlie-mnemonic\users
set UPDATE=false

echo Variables set

:parse_args
if "%~1"=="" goto end_parse_args
if /i "%~1"=="--update" (
    set UPDATE=true
    shift
    goto parse_args
)
shift
goto parse_args
:end_parse_args

echo Argument parsing complete
echo UPDATE=%UPDATE%

echo Current Directory: %CD%
echo Home Directory: %HOME%
echo Charlie User Directory: %CHARLIE_USER_DIR%

if "%UPDATE%"=="true" (
    echo Fetching remote branches...
    git fetch origin
    echo Available branches:
    git branch -r

    echo Please enter the branch name:
    set /p BRANCH="Enter the full name of the branch you want to switch to (or press Enter to update the current branch): "
    echo Branch entered: !BRANCH!

    if not "!BRANCH!"=="" (
        echo Checking if branch is a remote branch...
        git rev-parse --verify "!BRANCH!" >nul 2>nul
        if "!ERRORLEVEL!"=="0" (
            echo "!BRANCH!" is a valid branch
            echo Creating and switching to a local tracking branch...
            git checkout -b local_branch !BRANCH!
            if not !ERRORLEVEL!==0 (
                echo Failed to switch to branch !BRANCH!
                exit /b !ERRORLEVEL!
            )
        ) else (
            echo "!BRANCH!" is not a valid branch
            exit /b 1
        )
    ) else (
        echo Updating current branch...
        git pull origin
        if not !ERRORLEVEL!==0 (
            echo Failed to update the current branch
            exit /b !ERRORLEVEL!
        )
    )
)

echo Checking if docker is installed
docker --version

if not exist .env (
    echo Creating .env file
    echo CHARLIE_USER_DIR=%CHARLIE_USER_DIR% > .env
)

if not !ERRORLEVEL!==0 (
    echo Failed to find docker, is it installed?
    exit /b !ERRORLEVEL!
)

echo Checking if docker daemon is running
docker info

if not !ERRORLEVEL!==0 (
    echo Docker daemon not running. Please start Docker Desktop.
    exit /b !ERRORLEVEL!
)

echo Removing any existing containers with the same names
docker rm -f charlie-mnemonic psdb charlie-mnemonic-python-env

echo Stopping any existing Docker containers
docker-compose down

if not !ERRORLEVEL!==0 (
    echo Docker Compose down command failed with error level !ERRORLEVEL!.
    exit /b !ERRORLEVEL!
)

echo Starting Charlie Mnemonic using Docker Compose...
echo First run takes a while
docker-compose up --build -d

if not !ERRORLEVEL!==0 (
    echo Docker Compose up command failed with error level !ERRORLEVEL!.
    exit /b !ERRORLEVEL!
)

echo Entering check loop
:check_loop
echo Checking if Charlie Mnemonic started
powershell -Command "(Invoke-WebRequest -Uri %URL% -UseBasicParsing -TimeoutSec 2).StatusCode" 1>nul 2>nul
if !ERRORLEVEL!==0 (
    echo Charlie Mnemonic is up! Opening %URL% in the default browser!
    timeout /t 1 /nobreak >nul
    start %URL%
    docker logs -f charlie-mnemonic
    docker-compose down
) else (
    echo Not available yet. Retrying in 10 seconds...
    timeout /t 10 /nobreak >nul
    goto check_loop
)

echo Script completed
