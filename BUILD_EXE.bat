@echo off
TITLE Building Local Hub v2 (Core Only)
CLS

ECHO ========================================================
ECHO   Step 1: Building Python Core
ECHO   (Excluding Ngrok to keep it lightweight)
ECHO ========================================================

:: Clean up
RMDIR /S /Q "build" 2>NUL
RMDIR /S /Q "dist" 2>NUL
DEL /F /Q "*.spec" 2>NUL

:: Build Command
:: REMOVED: --add-binary "ngrok.exe;." (We will let NSIS handle this)
:: KEPT: --add-data "assets;assets" (Keep HTML inside so user can't break UI)

python -m PyInstaller ^
    --noconfirm ^
    --onefile ^
    --windowed ^
    --clean ^
    --name "LocalHub_v2" ^
    --icon "icon.png" ^
    --add-data "assets;assets" ^
    --hidden-import "engineio.async_drivers.threading" ^
    --hidden-import "flet" ^
    --hidden-import "eventlet" ^
    --hidden-import "pystray" ^
    --hidden-import "PIL" ^
    main.py

ECHO.
ECHO ========================================================
ECHO   Python Build Complete.
ECHO   Now we are ready for NSIS Installer.
ECHO ========================================================
ECHO.
PAUSE