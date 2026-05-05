@echo off
echo ======================================
echo    Nargan Mapper - Starting Server
echo ======================================

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Install dependencies if needed
echo Checking dependencies...
pip show fastapi >nul 2>&1
if errorlevel 1 (
    echo Installing dependencies...
    pip install -r requirements.txt
)

REM Create necessary directories
if not exist "database" mkdir database
if not exist "cache" mkdir cache
if not exist "exports" mkdir exports

REM Run the application
echo Starting server...
python run.py

pause