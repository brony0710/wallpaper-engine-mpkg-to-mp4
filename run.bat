@echo off
title Wallpaper Engine MPKG to MP4 Extractor
cd /d "%~dp0"

echo ============================================================
echo   Wallpaper Engine MPKG to MP4 Converter
echo   License: MIT License (Open Source)
echo   Status: 100%% Safe ^& Clean
echo ============================================================
echo.

:: Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not added to PATH!
    echo Please install Python from https://www.python.org/ (check "Add Python to PATH").
    echo.
    pause
    exit /b 1
)

:: Check dependencies
python -c "import customtkinter, PIL" >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Installing required dependencies (CustomTkinter, Pillow)...
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install dependencies. Please check your internet connection.
        pause
        exit /b 1
    )
)

echo [INFO] Launching CustomTkinter GUI...
start "" pythonw main.py

exit /b 0
