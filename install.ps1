# install.ps1
Write-Host "`n[ Vision-RCP Production Installer ]" -ForegroundColor Magenta
Write-Host "=================================="

# 1. Environment Checks
Write-Host "[1/5] Checking prerequisites..." -ForegroundColor Cyan

# Check Python
try {
    $pythonVer = python --version 2>&1
    Write-Host "    [OK] Python found: $pythonVer"
} catch {
    Write-Host "    [!] Error: Python not found in PATH." -ForegroundColor Red
    exit 1
}

# Check Node
try {
    $nodeVer = node --version 2>&1
    Write-Host "    [OK] Node.js found: $nodeVer"
} catch {
    Write-Host "    [!] Error: Node.js not found in PATH." -ForegroundColor Red
    exit 1
}

# Check SSH (Mandatory for Pinggy MVP)
try {
    $sshVer = ssh -V 2>&1
    Write-Host "    [OK] OpenSSH found."
} catch {
    Write-Host "    [!] Error: OpenSSH Client not found." -ForegroundColor Red
    Write-Host "        Pinggy requires SSH. Please enable 'OpenSSH Client' in Windows Features" -ForegroundColor Yellow
    Write-Host "        or run: Add-WindowsCapability -Online -Name OpenSSH.Client~~~~0.0.1.0" -ForegroundColor Yellow
    exit 1
}

# 2. Daemon Setup
Write-Host "`n[2/5] Setting up Python environment..." -ForegroundColor Cyan
if (-Not (Test-Path "daemon\.venv")) {
    python -m venv daemon\.venv
    Write-Host "    [OK] Virtual environment created."
}
& ".\daemon\.venv\Scripts\Activate.ps1"
pip install -r daemon\requirements.txt
Write-Host "    [OK] Python dependencies installed."

# 3. UI Setup
Write-Host "`n[3/5] Setting up UI dependencies..." -ForegroundColor Cyan
Set-Location ui
npm install
Set-Location ..
Write-Host "    [OK] UI dependencies installed."

# 4. PATH Registration
Write-Host "`n[4/5] Registering global CLI..." -ForegroundColor Cyan
powershell -ExecutionPolicy Bypass -File .\register-cli.ps1

# 5. Finalize
Write-Host "`n[5/5] Finalizing setup..." -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Magenta
Write-Host "[DONE] Vision-RCP is ready!" -ForegroundColor Green
Write-Host "Start a session from ANY folder using:" -ForegroundColor White
Write-Host "    vision-rcp connect" -ForegroundColor Cyan -NoNewline
Write-Host " (Requires terminal restart)`n"
