@echo off
title Wallpaper Engine MPKG to MP4 Extractor - by brony0710
cd /d "%~dp0"

echo ============================================================
echo   Wallpaper Engine MPKG to MP4 Converter
echo   Created by brony0710 - https://github.com/brony0710
echo   License: MIT License
echo ============================================================
echo.

where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python is not installed or not in PATH!
    echo Please install Python and ensure Add Python to PATH is checked.
    echo.
    pause
    exit /b 1
)

python -c "import customtkinter, PIL" >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [INFO] Installing required dependencies: CustomTkinter, Pillow...
    pip install -r requirements.txt
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Failed to install dependencies.
        pause
        exit /b 1
    )
)

echo [INFO] Launching Wallpaper Engine Extractor...
python main.py
if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Program exited with an error.
    pause
)
