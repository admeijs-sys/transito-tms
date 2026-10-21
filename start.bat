@echo off
title Transito TMS & SDI Facturatie
echo ===================================================
echo   Transito TMS & Italiaanse SDI Facturatie Hub
echo ===================================================
echo Server starten op http://127.0.0.1:8080 ...
start "" http://127.0.0.1:8080
python server.py
pause
