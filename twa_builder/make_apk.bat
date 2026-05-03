@echo off
echo ======================================================
echo FOLIUX Android APK Generator (Unsigned)
echo ======================================================
echo.
echo Requirements:
echo 1. Node.js installed
echo 2. Java JDK 11 installed
echo.
echo Checking for Bubblewrap...
call npm install -g @bubblewrap/cli
echo.
echo Initializing Android Project (Wait for it to finish)...
echo If it asks to "Continue anyway?", type 'y' and press Enter.
call bubblewrap init --manifest twa-manifest.json
echo.
echo Building APK...
call bubblewrap build
echo.
echo ======================================================
echo If successful, your APK will be in the 'build' folder.
echo ======================================================
pause
