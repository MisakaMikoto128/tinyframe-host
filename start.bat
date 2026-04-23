@echo off
chcp 65001 >nul
cd /d "%~dp0"

:: 检查虚拟环境是否存在
if not exist ".venv\Scripts\python.exe" (
    echo [信息] 首次启动，正在创建虚拟环境...
    python -m venv .venv
    if errorlevel 1 (
        echo [错误] 创建虚拟环境失败，请确认已安装 Python 3.11+
        pause
        exit /b 1
    )
    echo [信息] 正在安装依赖包（首次约需 2-5 分钟）...
    .venv\Scripts\pip install -r requirements.txt
    if errorlevel 1 (
        echo [错误] 安装依赖失败，请检查网络连接
        pause
        exit /b 1
    )
    echo [信息] 环境准备完成
)

echo [信息] 启动 INFY_POWER 上位机...
.venv\Scripts\python main.py
if errorlevel 1 (
    echo [错误] 程序异常退出，错误码: %errorlevel%
    pause
)
