@echo off
:: ============================================================
:: DCVM - Build as standalone folder  (folder mode)
:: Output: release\v<version>\DCVM_v<version>_folder\
:: ============================================================
cd /d "%~dp0"
python build.py folder
if errorlevel 1 (
    echo.
    echo [ERROR] Build failed. See output above.
    pause
    exit /b 1
)
pause
