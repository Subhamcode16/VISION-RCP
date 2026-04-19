# Vision-RCP: Automation Recovery Script
# This script force-cleans the environment and installs dependencies.

$ErrorActionPreference = "Stop"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "   Vision-RCP: Automation Recovery Process" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# 1. Kill potentially hanging processes
Write-Host "`n[1/5] Cleaning up stuck processes..." -ForegroundColor Yellow
$procNames = @("python", "pip")
foreach ($name in $procNames) {
    try {
        Get-Process $name -ErrorAction SilentlyContinue | Stop-Process -Force
        Write-Host "   - Stopped $name processes."
    } catch {
        # Ignore if none found
    }
}

# 2. Upgrade Pip and Setuptools
Write-Host "`n[2/5] Upgrading environment tools (pip, setuptools)..." -ForegroundColor Yellow
python -m pip install --upgrade pip setuptools --timeout 60

# 3. Install core pywin32
Write-Host "`n[3/5] Installing pywin32 (Force Upgrade)..." -ForegroundColor Yellow
python -m pip install pywin32 --upgrade --no-cache-dir --timeout 120 --verbose

# 4. Trigger Post-Install registration (Critical for COM/Registry)
Write-Host "`n[4/5] Registering Windows COM servers..." -ForegroundColor Yellow
$pyPath = python -c "import sys; print(sys.executable)"
$scriptsPath = Join-Path (Split-Path $pyPath) "Scripts"
$postInstall = Join-Path $scriptsPath "pywin32_postinstall.py"

if (Test-Path $postInstall) {
    python $postInstall -install
    Write-Host "   - COM Registration Successful." -ForegroundColor Green
} else {
    Write-Host "   [WARNING] Could not find pywin32_postinstall.py at $postInstall." -ForegroundColor Red
    Write-Host "   Trying fallback..."
    python -m pip install pywin32 --force-reinstall
}

# 5. Install pywinauto and comtypes
Write-Host "`n[5/5] Finalizing Automation Stack..." -ForegroundColor Yellow
python -m pip install pywinauto comtypes --upgrade --no-cache-dir --timeout 60

Write-Host "`n============================================================" -ForegroundColor Green
Write-Host "   SUCCESS: Recovery Complete!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host "Please close this window and run start-app.bat."
