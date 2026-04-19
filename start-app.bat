@echo off
setlocal

echo.
echo  ╦  ╦╦╔═╗╦╔═╗╔╗╔   ╦═╗╔═╗╔═╗
echo  ╚╗╔╝║╚═╗║║ ║║║║───╠╦╝║  ╠═╝
echo   ╚╝ ╩╚═╝╩╚═╝╝╚╝   ╩╚═╚═╝╩
echo   Local Agent Control Plane
echo.

:: Get script directory
set "SCRIPT_DIR=%~dp0"

:: Check Python
where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.11+
    pause
    exit /b 1
)

:: Check if venv exists, create if not
if not exist "%SCRIPT_DIR%daemon\.venv" (
    echo [SETUP] Creating Python virtual environment...
    python -m venv "%SCRIPT_DIR%daemon\.venv"
    call "%SCRIPT_DIR%daemon\.venv\Scripts\activate.bat"
    pip install -r "%SCRIPT_DIR%daemon\requirements.txt" -q
) else (
    call "%SCRIPT_DIR%daemon\.venv\Scripts\activate.bat"
)

:: Check Node.js for UI
where node >nul 2>nul
if errorlevel 1 (
    echo [WARNING] Node.js not found. UI will not be available.
    echo [WARNING] Install Node.js to use the web interface.
    goto :start_daemon
)

:: Install UI dependencies if needed
if not exist "%SCRIPT_DIR%ui\node_modules" (
    echo [SETUP] Installing UI dependencies...
    cd /d "%SCRIPT_DIR%ui"
    npm install -q 2>nul
    cd /d "%SCRIPT_DIR%"
)

:: Start UI dev server in a new window
echo [START] Launching UI dev server...
start "Vision-RCP UI" cmd /c "cd /d %SCRIPT_DIR%ui && npm run dev"

:: Start Relay server in a new window (for Remote/Phone access)
echo [START] Launching Relay server...
start "Vision-RCP Relay" cmd /c "call %SCRIPT_DIR%daemon\.venv\Scripts\activate.bat && python -m relay.server"

:: Start timer
set "START_TIME=%TIME%"

:: Start daemon
echo [START] Launching daemon...

:: Calculate and display startup pulse (crude cmd approximation)
echo [PULSE] Batch scripts ready in ~1s
echo.

cd /d "%SCRIPT_DIR%daemon"
python -m src.main --config config.toml

PAUSE
