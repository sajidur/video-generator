@echo off
rem One-time setup: Python packages, tools, settings, account logins. Double-click to run.
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo  AI Video Factory - setup
echo  ------------------------
where python >nul 2>nul
if errorlevel 1 (
    echo  Python is not installed.
    echo  Install Python 3.11 or newer from https://www.python.org/downloads/
    echo  IMPORTANT: tick "Add python.exe to PATH" in the installer, then run setup.bat again.
    pause
    exit /b 1
)
if not exist venv\Scripts\python.exe (
    echo  Creating the Python environment ...
    python -m venv venv || goto :fail
)
echo  Installing Python packages ...
venv\Scripts\python -m pip install --quiet --upgrade pip
venv\Scripts\python -m pip install --quiet -r requirements.txt || goto :fail
venv\Scripts\python make_video.py --setup
echo.
pause
exit /b 0

:fail
echo.
echo  Setup failed - see the message above.
pause
exit /b 1
