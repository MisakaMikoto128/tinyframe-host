@echo off
:: ============================================================
:: DCVM Modbus RTU Upper Machine - Build Launcher
:: Usage: build.bat [onefile|folder]
::   onefile  - Compile to a single .exe file  (default)
::   folder   - Compile to a standalone directory
:: ============================================================
cd /d "%~dp0"
python build.py %*
if errorlevel 1 (
    echo.
    echo [ERROR] Build failed. See output above.
    pause
    exit /b 1
)
pause
