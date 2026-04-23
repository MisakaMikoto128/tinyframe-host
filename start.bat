@echo off
chcp 65001 >nul
cd /d "%~dp0"

:: Check if virtual environment exists
if not exist ".venv\Scripts\python.exe" (
    echo "[INFO] First startup, creating virtual environment..."
    python -m venv .venv
    if errorlevel 1 (
        echo "[ERROR] Failed to create virtual environment, please ensure Python 3.11+ is installed"
        pause
        exit /b 1
    )
    echo "[INFO] Installing dependencies (first time may take 2-5 minutes)..."
    .venv\Scripts\pip install -r requirements.txt
    if errorlevel 1 (
        echo "[ERROR] Dependency installation failed, please check network connection"
        pause
        exit /b 1
    )
    echo "[INFO] Environment setup completed"
)

echo "[INFO] Starting INFY_POWER host application..."
.venv\Scripts\python main.py
if errorlevel 1 (
    echo "[ERROR] Program exited abnormally, error code: %errorlevel%"
    pause
)