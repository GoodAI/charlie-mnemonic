@echo off
setlocal enabledelayedexpansion

echo Script started
echo Command line: %0 %*

set URL=http://localhost:8002
set HOME=%USERPROFILE%
set CHARLIE_USER_DIR=%HOME%\AppData\Roaming\charlie-mnemonic\users
set UPDATE=false
set REPO_URL=https://github.com/GoodAI/charlie-mnemonic

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

:: Check if this is a git repository
if not exist .git (
    echo This directory is not a Git repository. Initializing...
    git init
    git remote add origin %REPO_URL%
    git fetch origin
    git checkout -b main origin/dev
    if errorlevel 1 (
        echo Failed to initialize repository. Please check your internet connection and try again.
        exit /b 1
    )
)

if "%UPDATE%"=="true" (
    echo Fetching remote branches...
    git fetch origin
    if errorlevel 1 (
        echo Failed to fetch from remote repository. Please check your internet connection and try again.
        exit /b 1
    )
    
    echo Available branches:
    git branch -r

    echo Please enter the branch name:
    set /p BRANCH="Enter the full name of the branch you want to switch to (or press Enter to update the current branch): "
    echo Branch entered: !BRANCH!

    :: Stash any changes
    echo Stashing any local changes...
    git add .
    git stash save "Automatic stash before update"

    if not "!BRANCH!"=="" (
        echo Switching to branch !BRANCH!
        git checkout -B !BRANCH! origin/!BRANCH!
    ) else (
        echo Updating current branch
        git pull origin HEAD
    )

    :: Try to apply stashed changes
    echo Attempting to apply stashed changes...
    git stash pop
    if errorlevel 1 (
        echo Note: There were conflicts when applying your local changes.
        echo Your changes are preserved in the stash. You may need to manually resolve conflicts.
    )
)

echo Checking if docker is installed
docker --version

if not exist .env (
    echo Creating .env file
    echo CHARLIE_USER_DIR=%CHARLIE_USER_DIR% > .env
)

if errorlevel 1 (
    echo Failed to find docker, is it installed?
    exit /b 1
)

echo Checking if docker daemon is running
docker info

if errorlevel 1 (
    echo Docker daemon not running. Please start Docker Desktop.
    exit /b 1
)

echo Removing any existing containers with the same names
docker rm -f charlie-mnemonic psdb charlie-mnemonic-python-env

echo Stopping any existing Docker containers
docker-compose down

if errorlevel 1 (
    echo Docker Compose down command failed.
    exit /b 1
)

echo Starting Charlie Mnemonic using Docker Compose...
echo First run takes a while
docker-compose up --build -d

if errorlevel 1 (
    echo Docker Compose up command failed.
    exit /b 1
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