@echo off
title SmartSoft Setup
echo ============================================
echo   SmartSoft - First Time Setup
echo ============================================
echo.

:: Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.12 or later
    pause
    exit /b 1
)

:: Install dependencies
echo Installing dependencies...
pip install django psycopg2-binary requests sentence-transformers torch transformers accelerate faiss-cpu pypdf pystray pillow python-dotenv --quiet
if %errorlevel% neq 0 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)
echo Dependencies installed.
echo.

:: Run migrations
echo Setting up database...
python manage.py migrate
if %errorlevel% neq 0 (
    echo ERROR: Failed to run migrations
    pause
    exit /b 1
)
echo Database configured.
echo.

:: Create desktop shortcut using a temp Python script
echo Creating desktop shortcut...
python create_shortcut.py
if %errorlevel% neq 0 (
    echo WARNING: Could not create desktop shortcut
)
echo.

echo ============================================
echo   Setup Complete!
echo ============================================
echo.
echo You can now:
echo 1. Double-click "SmartSoft" on your desktop
echo 2. Or run: python launcher.py
echo.
pause
