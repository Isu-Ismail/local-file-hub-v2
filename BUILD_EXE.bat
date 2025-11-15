@echo off
echo ============================
echo  Building LocalHub v2
echo ============================

REM ---- CLEAN OLD BUILD ----
rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul
del LocalHubV2.spec 2>nul

REM ---- RUN PYINSTALLER ----
pyinstaller ^
    --noconfirm ^
    --onefile ^
    --noconsole ^
    --name LocalHubV2 ^
    --add-data "assets;assets" ^
    --add-data "core;core" ^
    --add-data "temp_uploads;temp_uploads" ^
    --hidden-import flet ^
    --hidden-import flask ^
    --hidden-import flask_socketio ^
    --hidden-import engineio ^
    --hidden-import eventlet ^
    --hidden-import eventlet.wsgi ^
    --hidden-import werkzeug ^
    --hidden-import config ^
    --hidden-import pyperclip ^
    main.py

echo.
echo =================================
echo       BUILD COMPLETED
echo =================================
pause
