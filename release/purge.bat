@echo off
setlocal
set HOME=%USERPROFILE%
set CHARLIE_MNEMONIC_USER_DIR=%HOME%\AppData\Roaming\charlie-mnemonic\users
echo Warning, this will purge all Charlie Mnemonic data, are you sure you want to continue?

pause


docker-compose --project-name charlie-mnemonic-windows down
docker volume rm charlie-mnemonic-windows_postgres-data

if exist "%CHARLIE_MNEMONIC_USER_DIR%" (
    rmdir /s /q "%CHARLIE_MNEMONIC_USER_DIR%"
    echo Directory deleted.
) else (
    echo Directory not found.
)

endlocal