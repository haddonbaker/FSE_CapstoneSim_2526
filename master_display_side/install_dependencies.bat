@echo off
cd /d %~dp0

REM -----------------------------
REM Step 1: Check if Python exists
REM -----------------------------
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: Python is not installed or not in your PATH!
    echo Please download and install Python from https://www.python.org/downloads/
    pause
    exit /b
)

REM -----------------------------
REM Step 2: Create virtual environment if missing
REM -----------------------------
if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
    if %ERRORLEVEL% neq 0 (
        echo ERROR: Failed to create virtual environment.
        echo Make sure your Python installation supports venv.
        pause
        exit /b
    )
) else (
    echo Virtual environment already exists.
)

REM -----------------------------
REM Step 3: Upgrade pip
REM -----------------------------
echo Upgrading pip...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to upgrade pip.
    echo Make sure you have an active internet connection and pip installed.
    pause
    exit /b
)

REM -----------------------------
REM Step 4: Install dependencies
REM -----------------------------
echo Installing dependencies from requirements.txt...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to install dependencies.
    echo If the error mentions Git, please install Git from https://git-scm.com/downloads
    pause
    exit /b
)

echo.
echo All dependencies installed successfully!
pause