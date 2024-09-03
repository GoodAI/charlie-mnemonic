@echo off
setlocal enabledelayedexpansion

echo Script started
echo Command line: %0 %*

set URL=http://localhost:8002
set HOME=%USERPROFILE%
set CHARLIE_USER_DIR=%HOME%\AppData\Roaming\charlie-mnemonic\users
set UPDATE=false
set REPO_URL=https://github.com/GoodAI/charlie-mnemonic
set BACKUP_FOLDER=%HOME%\charlie_backups\charlie_backup_%date:~-4,4%%date:~-10,2%%date:~-7,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set BACKUP_FOLDER=%BACKUP_FOLDER: =0%
set DOCKER_CPUS=2

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

if "%UPDATE%"=="true" (
    :: Create backup folder and copy all files
    echo Creating backup of existing files...
    if not exist "%HOME%\charlie_backups" mkdir "%HOME%\charlie_backups"
    mkdir "%BACKUP_FOLDER%"
    xcopy /E /I /H /Y . "%BACKUP_FOLDER%"
    echo Backup created in folder: %BACKUP_FOLDER%

    :: Check if this is a git repository
    if not exist .git (
        echo This directory is not a Git repository. Initializing...
        git init
        git remote add origin %REPO_URL%
    )

    echo Fetching latest changes from the repository...
    git fetch origin

    echo Available branches:
    git branch -r

    echo Please enter the branch name:
    set /p BRANCH="Enter the name of the branch you want to switch to (without 'origin/'): "
    echo Branch entered: !BRANCH!

    if not "!BRANCH!"=="" (
        echo Switching to branch !BRANCH!
        git reset --hard origin/!BRANCH!
        git clean -fd
    ) else (
        echo Updating current branch
        git reset --hard origin/HEAD
        git clean -fd
    )

    :: Update submodules if any
    git submodule update --init --recursive

    echo Repository update complete.
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

echo Updating CPU allocation for charlie-mnemonic container...
docker update --cpus %DOCKER_CPUS% charlie-mnemonic
if errorlevel 1 (
    echo Failed to update CPU allocation for charlie-mnemonic container.
    echo Continuing with default allocation...
) else (
    echo Successfully updated CPU allocation for charlie-mnemonic container.
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
if "%UPDATE%"=="true" (
    echo Your original files are preserved in the backup folder: %BACKUP_FOLDER%
)