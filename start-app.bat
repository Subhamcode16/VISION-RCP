@echo off
setlocal enabledelayedexpansion

:: ==========================================================
::  V I S I O N - R C P
::  Local Agent Control Plane (Modernized Build)
:: ==========================================================

echo.
echo  [38;5;255m▄   ▄ ▄▄▄▄▄ ▄▄▄▄▄ ▄▄▄▄▄ ▄▄▄▄▄ ▄   ▄  [38;5;240m▄▄▄▄  ▄▄▄▄ ▄▄▄▄ 
echo  [38;5;255m█   █   █   █     █   █ █   █ █▄  █  [38;5;240m█   █ █    █   █
echo  [38;5;255m █ █    █   ▀▀▀▀▄ █   █ █   █ █ █ █  [38;5;240m█▄▄▄▀ █    █▄▄▄▀
echo  [38;5;255m █ █    █       █ █   █ █   █ █  ▀█  [38;5;240m█  █  █    █    
echo  [38;5;255m  █   ▄▄▄▄▄ ▄▄▄▄▄▀ ▀▄▄▄▀ ▀▄▄▄▀ █   █  [38;5;240m█   █ ▀▄▄▄ █    
echo.
echo  [38;5;244mPremium Local Agent Dashboard │ Build v1.1-zinc[0m
echo.

:: Get script directory
set "SCRIPT_DIR=%~dp0"
set "DATA_DIR=%USERPROFILE%\.vision-rcp"

:: --- PORT CONFLICT DETECTION ---
echo [SYSTEM] Cleaning zombie processes...
taskkill /F /IM node.exe /T >nul 2>&1
taskkill /F /IM python.exe /T >nul 2>&1
taskkill /F /IM msedge.exe /FI "WINDOWTITLE eq Vision-RCP*" >nul 2>&1

echo [SYSTEM] Checking for port conflicts...
for %%p in (9077 8080 5173) do (
    for /f "tokens=5" %%a in ('netstat -aon ^| findstr :%%p ^| findstr LISTENING') do (
        echo [WARN] Port %%p is busy by PID %%a. Clearing...
        taskkill /F /PID %%a >nul 2>&1
    )
)

:: --- DEPENDENCY CHECK ---
if "%1"=="setup" (
    echo [SETUP] Force-refreshing all dependencies...
    set "FORCE_SETUP=true"
)

:: Python Setup
if not exist "%SCRIPT_DIR%daemon\.venv" set "FORCE_SETUP=true"
if "!FORCE_SETUP!"=="true" (
    echo [PYTHON] Initializing virtual environment...
    python -m venv "%SCRIPT_DIR%daemon\.venv"
    call "%SCRIPT_DIR%daemon\.venv\Scripts\activate.bat"
    pip install -r "%SCRIPT_DIR%daemon\requirements.txt"
) else (
    call "%SCRIPT_DIR%daemon\.venv\Scripts\activate.bat"
)

:: UI Setup
if not exist "%SCRIPT_DIR%ui\node_modules" set "FORCE_UI_SETUP=true"
if "!FORCE_UI_SETUP!"=="true" (
    echo [NODE] Installing modernized UI dependencies...
    cd /d "%SCRIPT_DIR%ui"
    npm install
    cd /d "%SCRIPT_DIR%"
)

:: --- AUTH SECRET DISCOVERY ---
echo [AUTH] Fetching security token...
set "SECRET_KEY=LOCAL"
if exist "%DATA_DIR%\secret.key" (
    set /p SECRET_KEY=<"%DATA_DIR%\secret.key"
)
:: Trim trailing whitespace/CR if any
set "SECRET_KEY=%SECRET_KEY: =%"

:: --- LAUNCH ---
echo [START] Launching full stack...

:: 1. Start UI Dev Server
start "Vision-RCP UI" cmd /c "cd /d %SCRIPT_DIR%ui && npm run dev"

:: 2. Start Relay Server
start "Vision-RCP Relay" cmd /c "call %SCRIPT_DIR%daemon\.venv\Scripts\activate.bat && python -m relay.server"

:: 3. Launch App Window (Wait for UI to warm up)
echo [WAIT] Waiting for Vite server readiness (Port 5173)...
:WAIT_VITE
timeout /t 1 /nobreak >nul
netstat -aon | findstr :5173 | findstr LISTENING >nul
if errorlevel 1 (
    set /a VITE_WAITED+=1
    if !VITE_WAITED! gtr 15 (
        echo [ERROR] Vite server failed to start in time. Check UI terminal.
        pause
        exit /b 1
    )
    goto WAIT_VITE
)

set "DASHBOARD_URL=http://localhost:5173/?k=%SECRET_KEY%"
echo [BROWSER] Opening Dashboard in App Mode...

:: Try Edge in App Mode first (most compatible on Windows)
start msedge --app="%DASHBOARD_URL%" >nul 2>&1
if errorlevel 1 (
    :: Fallback to standard start
    start "" "%DASHBOARD_URL%"
)

:: 4. Start Daemon (Main Window)
echo [START] Launching Local Daemon...
cd /d "%SCRIPT_DIR%daemon"
python -m src.main --config config.toml

echo.
echo [DONE] Dashboard session active.
pause
