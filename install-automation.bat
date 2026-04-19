@echo off
:: Vision-RCP Automation Dependency Installer (Administrator)
:: This script force-installs pywinauto and handles the comtypes cache generation.

setlocal
set "SCRIPT_PATH=%~dp0"

:: 1. Check for Administrative Privileges
net session >nul 2>&1
if %errorLevel% == 0 (
    echo [OK] Running with Administrator privileges.
) else (
    echo [INFO] Requesting Administrator privileges...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

echo.
echo ============================================================
echo   Vision-RCP: Desktop Automation Fix
echo ============================================================
echo.

:: 2. Pre-install pywin32 (helps stabilize COM interactions)
echo [1/4] Installing pywin32...
python -m pip install pywin32 --upgrade --no-cache-dir
if %errorLevel% neq 0 (
    echo [WARNING] pywin32 installation failed or already satisfied. Continuing...
)

:: 3. Install core automation libraries
echo [2/4] Installing pywinauto and comtypes...
echo.
echo NOTE: This may take a moment. If it looks stuck, please wait.
echo It is bypassed cache to avoid the previous hang.
echo.
python -m pip install comtypes pywinauto --upgrade --no-cache-dir --timeout 60 --verbose

if %errorLevel% neq 0 (
    echo.
    echo [ERROR] Installation failed. 
    echo Please check if you have an active internet connection or if pip is blocked by a firewall.
    pause
    exit /b
)

:: 4. Cache Warm-up (The CRITICAL step)
echo.
echo [3/4] Warming up comtypes cache (Generating COM definitions)...
python -c "import pywinauto; from pywinauto import Application; print('Cache Warm-up: OK')"

:: 5. Verification
echo.
echo [4/4] Verifying Installation...
python -c "import pywinauto; print('Pywinauto Version:', pywinauto.__version__); print('VERIFICATION SUCCESSFUL!')"

if %errorLevel% == 0 (
    echo.
    echo ============================================================
    echo   SUCCESS: Automation is now enabled!
    echo ============================================================
    echo.
    echo You can now close this window and restart Vision-RCP:
    echo 1. Stop your current start-app.bat
    echo 2. Run ./start-app.bat again
    echo.
) else (
    echo [ERROR] Verification failed. Please share the error message with the agent.
)

pause
