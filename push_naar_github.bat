@echo off
title Upload Transito naar GitHub
echo ========================================================
echo   Transito TMS - Upload naar GitHub (Backup & Sync)
echo ========================================================
echo.
cd /d "%~dp0"

echo Bestanden uploaden naar https://github.com/admeijs-sys/transito-tms...
git push origin main

echo.
echo ========================================================
if %errorlevel% equ 0 (
    echo  GELUKT! Alle bestanden en updates staan nu veilig op GitHub!
) else (
    echo  Er trad een fout op of inloggen is nog niet voltooid.
)
echo ========================================================
pause
