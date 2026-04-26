@echo off
SETLOCAL EnableDelayedExpansion
title Vision-RCP Remote Bridge [SIDE QUEST]

echo ============================================================
echo   V I S I O N - R C P   R E M O T E   B R I D G E
echo ============================================================
echo.
echo [STATUS] Cleaning up existing processes...

:: Kill existing Python, Node, and Cloudflared instances to prevent conflicts
taskkill /F /IM node.exe /T 2>nul
taskkill /F /IM python.exe /T 2>nul
taskkill /F /IM cloudflared.exe /T 2>nul

echo [STATUS] Starting Remote Bootloader...
echo [INFO] This will establish a secure tunnel for mobile access.
echo [INFO] Dashboard: https://vision-rcp-ui.vercel.app/
echo.

:: Set terminal to UTF-8 for QR code support
chcp 65001 >nul

:: Run the python bootloader
python remote_boot.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Remote Bridge failed to start.
    echo [HINT] Ensure cloudflared is installed and in your PATH.
    pause
)

ENDLOCAL
