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

:: Create .env file if it doesn't exist
if not exist .env (
    echo Creating .env file
    echo CHARLIE_USER_DIR=%CHARLIE_USER_DIR% > .env
)

:: Check if this is a git repository
if not exist .git (
    echo This directory is not a Git repository. Initializing...
    
    :: Backup the existing start_local.bat
    if exist start_local.bat (
        echo Backing up existing start_local.bat
        move start_local.bat start_local.bat.bak
    )
    
    git init
    git remote add origin %REPO_URL%
    git fetch origin
    
    :: Attempt to checkout, and if it fails, restore the backup
    git checkout -b main origin/dev
    if errorlevel 1 (
        echo Failed to initialize repository. Restoring backup...
        if exist start_local.bat.bak (
            move start_local.bat.bak start_local.bat
        )
        echo Please check your internet connection and try again.
        exit /b 1
    )
    
    :: If checkout was successful, remove the backup
    if exist start_local.bat.bak (
        del start_local.bat.bak
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
    set /p BRANCH="Enter the name of the branch you want to switch to (without 'origin/'): "
    echo Branch entered: !BRANCH!

    :: Force reset to remove all local changes
    echo Resetting local changes...
    git reset --hard

    :: Remove all untracked files and directories
    echo Removing untracked files and directories...
    git clean -fd

    if not "!BRANCH!"=="" (
        echo Switching to branch !BRANCH!
        git checkout -B !BRANCH! origin/!BRANCH! --force
    ) else (
        echo Updating current branch
        git pull origin HEAD --force
    )

    echo Branch update complete.
)

echo Checking if docker is installed
docker --version

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
docker rm -f charlie-mnemonic psdb charlie-mnemonic-python-env 2>nul

echo Stopping any existing Docker containers
docker-compose down 2>nul

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