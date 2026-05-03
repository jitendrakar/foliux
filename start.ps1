# FOLIUX Standardization & Startup Script

Write-Host "--- FOLIUX Project Setup ---" -ForegroundColor Cyan

# 1. Check for Python
if (!(Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Error "Python is not installed or not in PATH. Please install Python to continue."
    exit
}

# Handle Virtual Environment
$VENV_NAME = "venv_local"
if (!(Test-Path $VENV_NAME)) {
    Write-Host "Creating fresh virtual environment in $VENV_NAME..." -ForegroundColor Yellow
    python -m venv $VENV_NAME
} else {
    # Check if it's a Windows venv by looking for Scripts folder
    if (!(Test-Path "$VENV_NAME\Scripts")) {
        Write-Host "Existing $VENV_NAME is invalid. Trying to rename and recreate..." -ForegroundColor Red
        $OldName = "$VENV_NAME" + (Get-Date -Format "yyyyMMddHHmmss")
        Rename-Item -Path $VENV_NAME -NewName $OldName
        python -m venv $VENV_NAME
    }
}

# 3. Activate and Install Requirements
Write-Host "Activating environment and installing dependencies..." -ForegroundColor Yellow
& "$VENV_NAME\Scripts\python.exe" -m pip install --upgrade pip
& "$VENV_NAME\Scripts\python.exe" -m pip install -r requirements.txt

# 4. Run Check
Write-Host "Verifying configuration..." -ForegroundColor Yellow
& "$VENV_NAME\Scripts\python.exe" manage.py check
if ($LASTEXITCODE -ne 0) {
    Write-Error "Django check failed. Please review the errors above."
    exit
}

# 5. Start Project
Write-Host "Starting FOLIUX Project..." -ForegroundColor Green
& "$VENV_NAME\Scripts\python.exe" manage.py runserver 8000
