# NPITS Full Backup Script (Including Git History)
$ErrorActionPreference = "Stop"

$ProjectDir = "c:\inetpub\wwwroot\NPITS"
$BackupDir = Join-Path $ProjectDir "backups"
$Timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm"
$ZipName = "NPITS_FULL_backup_$Timestamp.zip"
$ZipPath = Join-Path $BackupDir $ZipName

Write-Host "Starting FULL backup of $ProjectDir to $ZipPath..."

# Ensure the backups directory exists
if (-not (Test-Path $BackupDir)) {
    New-Item -ItemType Directory -Path $BackupDir | Out-Null
}

# Define items to exclude
$Excludes = @(
    "backups",
    "__pycache__",
    ".gemini",
    "venv",
    "staticfiles",
    "wfastcgi.log"
)

# Use Resolve-Path to get absolute paths for filtering
$Children = Get-ChildItem -Path $ProjectDir -Exclude $Excludes

Write-Host "Compressing files (including .git)..."
Compress-Archive -Path $Children.FullName -DestinationPath $ZipPath -Force

Write-Host "Full backup completed successfully: $ZipPath"
