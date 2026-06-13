@echo off
:: Foliux Daily Database Pull Script
:: This script pulls the latest data from the VPS to your local machine.

echo [%date% %time%] Starting daily pull... >> sync_log.txt

cd /d "G:\My Drive\NETPROFIT\FOLIUX"

:: Run the sync script using the virtual environment python
"G:\My Drive\NETPROFIT\FOLIUX\venv_local\Scripts\python.exe" sync_database.py pull >> sync_log.txt 2>&1

if %ERRORLEVEL% EQU 0 (
    echo [%date% %time%] Sync completed successfully. >> sync_log.txt
) else (
    echo [%date% %time%] Sync FAILED with error code %ERRORLEVEL%. >> sync_log.txt
)
echo -------------------------------------------------- >> sync_log.txt
