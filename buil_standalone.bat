@echo off
title Building LocalHubV2 with Nuitka...

set PYTHON="C:\Users\ismail\AppData\Local\Programs\Python\Python311\python.exe"

%PYTHON% -m nuitka ^
    main.py ^
    --standalone ^
    --windows-disable-console ^
    --windows-icon-from-ico=icon.ico ^
    --include-module=pyperclip ^
    --include-package=flet ^
    --include-package=core ^
    --include-package=flask ^
    --include-package=werkzeug ^
    --include-package=jinja2 ^
    --include-package=itsdangerous ^
    --include-package=watchdog ^
    --include-package=markupsafe ^
    --include-data-dir=assets=assets ^
    --include-data-file=config.py=config.py ^
    --nofollow-import-to=eventlet ^
    --nofollow-import-to=gevent ^
    --nofollow-import-to=gevent-websocket ^
    --nofollow-import-to=flask_socketio ^
    --nofollow-import-to=socketio ^
    --nofollow-import-to=engineio ^
    --jobs=8



echo.
echo ======================================================
echo Build completed!
echo Your app is in: build\main.dist\
echo main.exe + all required DLLs and data files
echo ======================================================
echo.

pause
