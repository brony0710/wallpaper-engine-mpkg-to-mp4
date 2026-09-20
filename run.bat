@echo off
title Wallpaper Engine MPKG to MP4 Extractor
cd /d "%~dp0"

echo ============================================================
echo   Wallpaper Engine MPKG to MP4 Converter
echo   Lisensi: MIT License (Open Source)
echo   Status: 100%% Aman ^& Bersih dari Virus
echo ============================================================
echo.

:: Cek Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python belum terinstall atau belum masuk PATH!
    echo Silakan install Python dari https://www.python.org/ (centang "Add Python to PATH").
    echo.
    pause
    exit /b 1
)

:: Cek dependensi
python -c "import customtkinter" >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Menginstall modul yang dibutuhkan (CustomTkinter)...
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo [ERROR] Gagal menginstall dependensi. Periksa koneksi internet Anda.
        pause
        exit /b 1
    )
)

echo [INFO] Membuka Antarmuka Grafis (CustomTkinter GUI)...
start "" pythonw main.py

exit /b 0
