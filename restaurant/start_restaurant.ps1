# FOLIUX Restaurant Startup Script

Write-Host "--- FOLIUX Restaurant Project Setup ---" -ForegroundColor Cyan

# Use the parent virtual environment which is already configured
$VENV_PATH = "..\venv_local"

if (!(Test-Path $VENV_PATH)) {
    Write-Host "Standard virtual environment not found at $VENV_PATH. Creating a local virtual environment in 'venv_local'..." -ForegroundColor Yellow
    python -m venv venv_local
    $VENV_PATH = "venv_local"
    & "$VENV_PATH\Scripts\python.exe" -m pip install --upgrade pip
    & "$VENV_PATH\Scripts\python.exe" -m pip install -r ..\requirements.txt
}

# Run django check to verify
Write-Host "Verifying Restaurant project configuration..." -ForegroundColor Yellow
& "$VENV_PATH\Scripts\python.exe" manage.py check
if ($LASTEXITCODE -ne 0) {
    Write-Error "Django check failed. Please review the errors above."
    exit
}

# Start local server on port 8001
Write-Host "Starting FOLIUX Restaurant Project on port 8001..." -ForegroundColor Green
Write-Host "Local URL: http://localhost:8001/restaurant/" -ForegroundColor Green
Write-Host "LAN URL:   http://192.168.1.244:8001/restaurant/" -ForegroundColor Green
& "$VENV_PATH\Scripts\python.exe" manage.py runserver 0.0.0.0:8001
