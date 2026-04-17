# package_project.ps1
# This script creates a clean ZIP archive of the project for manual deployment.

$ProjectName = "feemanagement_production_bundle"
$ZipFile = "$PSScriptRoot\$ProjectName.zip"
$StagingDir = "$PSScriptRoot\staging_temp"

Write-Host "📦 Starting final project packaging..." -ForegroundColor Cyan

# Remove old zip and staging
if (Test-Path $ZipFile) { Remove-Item $ZipFile -Force }
if (Test-Path $StagingDir) { Remove-Item $StagingDir -Recurse -Force }
New-Item -ItemType Directory -Path $StagingDir | Out-Null

Write-Host "📂 Copying files to staging..." -ForegroundColor Yellow

# Use Robocopy for fast, reliable filtered copying
# /XF excludes files, /XD excludes directories, /S copies subdirs
& robocopy "$PSScriptRoot" "$StagingDir" /S /XF "*.zip" "*.pyc" ".env" "db.sqlite3" "package_project.ps1" /XD ".git" "venv" ".venv" "__pycache__" ".gemini" "brain" "staticfiles" ".agents" ".agent" | Out-Null

Write-Host "🤐 Compressing staging folder..." -ForegroundColor Yellow
Compress-Archive -Path "$StagingDir\*" -DestinationPath $ZipFile

# Cleanup staging
Remove-Item $StagingDir -Recurse -Force

Write-Host "✅ Final deployment bundle created: $ZipFile" -ForegroundColor Green
Write-Host "🚀 Everything is saved and ready for upload!" -ForegroundColor Green
