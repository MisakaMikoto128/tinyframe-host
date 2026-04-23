@echo off
chcp 65001 > nul
echo ============================================================
echo    REG1K0100A2 充电模块上位机  Nuitka DEBUG 打包
echo    * CMD 窗口保持可见，方便查看启动报错
echo    * 禁用 LTO 和 -OO，保留调试信息，编译更快
echo ============================================================
echo.

REM ── 切换到脚本所在目录 ──────────────────────────────────────
cd /d "%~dp0"

REM ── 检查 Python ─────────────────────────────────────────────
python --version > nul 2>&1
if errorlevel 1 (
    echo [ERROR] 未找到 Python，请确认已添加到 PATH。
    pause & exit /b 1
)

REM ── 激活虚拟环境 ────────────────────────────────────────────
if exist .venv\Scripts\activate.bat (
    echo [INFO]  激活虚拟环境 .venv ...
    call .venv\Scripts\activate.bat
) else if exist venv\Scripts\activate.bat (
    echo [INFO]  激活虚拟环境 venv ...
    call venv\Scripts\activate.bat
) else (
    echo [WARN]  未找到虚拟环境，使用系统 Python。
)

REM ── 检查 / 安装 Nuitka ──────────────────────────────────────
python -c "import nuitka" > nul 2>&1
if errorlevel 1 (
    echo [INFO]  安装 Nuitka ...
    pip install nuitka
    if errorlevel 1 ( echo [ERROR] Nuitka 安装失败！ & pause & exit /b 1 )
)

REM ── 编译器缓存目录（与正式版共享，加快二次编译）─────────────
set NUITKA_CACHE_DIR_DOWNLOADS=.build_cache\nuitka_downloads
set NUITKA_CACHE_DIR_CCACHE=.build_cache\nuitka_ccache
set NUITKA_CACHE_DIR_CLCACHE=.build_cache\nuitka_clcache
set NUITKA_CACHE_DIR_BYTECODE=.build_cache\nuitka_bytecode
set NUITKA_CACHE_DIR_DLL_DEPENDENCIES=.build_cache\nuitka_dll_dep

set PYTHONUNBUFFERED=1
set start_time=%time%
echo.
echo [INFO]  开始 DEBUG 打包... %start_time%
echo [INFO]  输出目录：release\main.dist\
echo.

python -m nuitka ^
    --msvc=latest ^
    --standalone ^
    --assume-yes-for-downloads ^
    --follow-imports ^
    --windows-console-mode=attach ^
    --windows-icon-from-ico=img\star.ico ^
    --windows-company-name="INFYPOWER" ^
    --windows-product-name="REG1K0100A2 充电模块上位机 [DEBUG]" ^
    --windows-file-version=0.0.0.1 ^
    --windows-product-version=0.0.0.1 ^
    --windows-file-description="REG1K0100A2 充电模块上位机 DEBUG" ^
    --python-flag=no_site ^
    --enable-plugin=pyqt5 ^
    --enable-plugin=multiprocessing ^
    --enable-plugin=anti-bloat ^
    --include-package=qfluentwidgets ^
    --include-package-data=qfluentwidgets ^
    --include-package=qframelesswindow ^
    --include-package=qframelesswindow.titlebar ^
    --include-package-data=qframelesswindow ^
    --include-data-files=ControlCAN.dll=ControlCAN.dll ^
    --include-data-dir=img=img ^
    --include-data-dir=resource=resource ^
    --nofollow-import-to=setuptools,pip,wheel ^
    --nofollow-import-to=pytest,docutils,unittest ^
    --nofollow-import-to=matplotlib,scipy,pandas,openpyxl ^
    --nofollow-import-to=numba,llvmlite ^
    --nofollow-import-to=pyqtgraph,OpenGL ^
    --nofollow-import-to=numpy ^
    --nofollow-import-to=PyQt5.Qt3DAnimation ^
    --nofollow-import-to=PyQt5.Qt3DCore ^
    --nofollow-import-to=PyQt5.Qt3DExtras ^
    --nofollow-import-to=PyQt5.Qt3DInput ^
    --nofollow-import-to=PyQt5.Qt3DLogic ^
    --nofollow-import-to=PyQt5.Qt3DRender ^
    --nofollow-import-to=PyQt5.QtBluetooth ^
    --nofollow-import-to=PyQt5.QtDesigner ^
    --nofollow-import-to=PyQt5.QtHelp ^
    --nofollow-import-to=PyQt5.QtLocation ^
    --nofollow-import-to=PyQt5.QtMultimedia ^
    --nofollow-import-to=PyQt5.QtMultimediaWidgets ^
    --nofollow-import-to=PyQt5.QtNfc ^
    --nofollow-import-to=PyQt5.QtPositioning ^
    --nofollow-import-to=PyQt5.QtQml ^
    --nofollow-import-to=PyQt5.QtQuick ^
    --nofollow-import-to=PyQt5.QtRemoteObjects ^
    --nofollow-import-to=PyQt5.QtSensors ^
    --nofollow-import-to=PyQt5.QtSerialPort ^
    --nofollow-import-to=PyQt5.QtSql ^
    --nofollow-import-to=PyQt5.QtTest ^
    --nofollow-import-to=PyQt5.QtWebChannel ^
    --nofollow-import-to=PyQt5.QtWebEngine ^
    --nofollow-import-to=PyQt5.QtWebEngineCore ^
    --nofollow-import-to=PyQt5.QtWebEngineWidgets ^
    --nofollow-import-to=PyQt5.QtWebSockets ^
    --nofollow-import-to=PyQt5.QtXml ^
    --nofollow-import-to=*.tests ^
    --nofollow-import-to=*.test ^
    --nofollow-import-to=*.testing ^
    --output-filename=INFY_POWER_debug.exe ^
    --output-dir=release ^
    main.py

echo.
echo [INFO]  DEBUG 打包结束 %time%（开始 %start_time%）

if errorlevel 1 (
    echo [ERROR] 打包失败！
    pause & exit /b 1
)

REM ── 复制 config.json ────────────────────────────────────────
if exist config.json (
    copy /y config.json release\main.dist\config.json > nul
    echo [INFO]  已复制 config.json
)

echo.
echo ============================================================
echo  DEBUG 打包成功！
echo  执行 release\main.dist\INFY_POWER_debug.exe
echo  启动时 CMD 窗口会保持可见，print / traceback 均可看到。
echo ============================================================
pause
