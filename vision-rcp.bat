@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%"
set "PYTHON_EXE=%PROJECT_ROOT%daemon\.venv\Scripts\python.exe"

if not exist "%PYTHON_EXE%" (
    echo [!] Error: Virtual environment not found in %PROJECT_ROOT%daemon\.venv
    echo [!] Please run: powershell -File "%PROJECT_ROOT%install.ps1"
    exit /b 1
)

:: Run from daemon folder so python -m src.cli works
pushd "%PROJECT_ROOT%daemon"
"%PYTHON_EXE%" -m src.cli %*
popd
