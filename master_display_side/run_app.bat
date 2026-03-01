@echo off
REM Go to folder where this batch file lives
cd /d %~dp0

REM Run main.py in the subfolder using the virtual environment
".venv\Scripts\python.exe" "main.py"

pause