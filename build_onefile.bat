@echo off
:: ============================================================
:: DCVM - Build as single .exe file  (onefile mode)
:: Output: release\v<version>\DCVM_v<version>.exe
:: ============================================================
cd /d "%~dp0"
python build.py onefile
if errorlevel 1 (
    echo.
    echo [ERROR] Build failed. See output above.
    pause
    exit /b 1
)
pause
