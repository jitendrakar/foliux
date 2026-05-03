# NPITS GitHub Backup Script
$ErrorActionPreference = "Stop"

$ProjectDir = $PSScriptRoot
$GitPath = "C:\Users\Unifi\AppData\Local\GitHubDesktop\app-3.5.6\resources\app\git\cmd\git.exe"

Write-Host "Starting database dump..."
& python manage.py dumpdata --indent 4 > db_backup.json

if (Test-Path "$ProjectDir\db_backup.json") {
    Write-Host "Database dumped successfully to db_backup.json"
} else {
    Write-Error "Failed to dump database."
    exit 1
}

Write-Host "Staging changes for Git..."
& $GitPath add .

# Check if there are any changes to commit
$Status = & $GitPath status --porcelain
if (-not $Status) {
    Write-Host "No changes to commit."
} else {
    Write-Host "Committing changes..."
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    & $GitPath commit -m "Auto-backup with database: $Timestamp"

    Write-Host "Pushing to GitHub (origin)..."
    & $GitPath push origin main
    
    Write-Host "Pushing to GitHub (foliux)..."
    & $GitPath push foliux main
    
    Write-Host "Successfully pushed to all remotes!"
}
