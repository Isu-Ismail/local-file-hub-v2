@echo off
TITLE Building Local Hub v2 (Compressed)
CLS

ECHO ========================================================
ECHO   Local Hub v2 Builder (High Compression)
ECHO ========================================================
ECHO.

:: 1. Check for UPX (Required for compression)
IF NOT EXIST "upx.exe" (
    ECHO [WARNING] upx.exe not found!
    ECHO Download UPX from https://github.com/upx/upx/releases
    ECHO and place 'upx.exe' in this folder to reduce file size by ~50%%.
    PAUSE
)

IF NOT EXIST "icon.ico" (
    ECHO [ERROR] icon.ico not found!
    PAUSE
    EXIT /B
)

ECHO   Cleaning up...
RMDIR /S /Q "build" 2>NUL
RMDIR /S /Q "dist" 2>NUL
DEL /F /Q "*.spec" 2>NUL

ECHO.
ECHO   Starting PyInstaller...
ECHO ========================================================

:: --- BUILD COMMAND ---
:: --upx-dir ".": Uses the upx.exe in the current folder
:: --exclude-module: Removes unused heavy libraries

python -m PyInstaller ^
    --noconfirm ^
    --onefile ^
    --windowed ^
    --clean ^
    --name "LocalHub_v2" ^
    --icon "icon.ico" ^
    --upx-dir "." ^
    --add-data "assets;assets" ^
    --hidden-import "engineio.async_drivers.threading" ^
    --hidden-import "flet" ^
    --hidden-import "eventlet" ^
    --hidden-import "PIL" ^
    --exclude-module "tkinter" ^
    --exclude-module "matplotlib" ^
    --exclude-module "numpy" ^
    --exclude-module "pandas" ^
    --exclude-module "scipy" ^
    main.py

ECHO.
ECHO ========================================================
IF EXIST "dist\LocalHub_v2.exe" (
    ECHO   SUCCESS! 
    ECHO   Compressed Core EXE created: dist\LocalHub_v2.exe
) ELSE (
    ECHO   BUILD FAILED.
)
ECHO ========================================================
ECHO.
PAUSE