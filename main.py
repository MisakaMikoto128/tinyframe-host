import sys
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QAction, QApplication, QMenu, QSystemTrayIcon
from qfluentwidgets import (FluentIcon as FIF, FluentWindow,
                            NavigationItemPosition, setThemeColor)

from config_manager import ConfigManager
from tinyframe import TinyFrameEngine
from widgets.business_page import BusinessPage
from widgets.debug_page import DebugPage
from widgets.settings_page import SettingsPage

_ICON_DIR = Path(__file__).resolve().parent / "img"


class MainWindow(FluentWindow):
    def __init__(self):
        super().__init__()
        self._cm = ConfigManager()
        self._config = self._cm.load()

        setThemeColor("#28afe9")

        self._engine = TinyFrameEngine(self)

        self.businessPage = BusinessPage(self._engine, self._config, self)
        self.businessPage.setObjectName("businessPage")
        self.debugPage = DebugPage(self._engine, self._config, self)
        self.debugPage.setObjectName("debugPage")
        self.settingsPage = SettingsPage(self._config, self._cm, self)
        self.settingsPage.setObjectName("settingsPage")

        self._init_navigation()
        self._init_window()
        self._init_tray()

    def _init_navigation(self) -> None:
        self.addSubInterface(self.businessPage, FIF.HOME, "业务面板")
        self.addSubInterface(self.debugPage, FIF.DEVELOPER_TOOLS, "协议调试")
        self.navigationInterface.addSeparator()
        self.addSubInterface(self.settingsPage, FIF.SETTING, "设置",
                             NavigationItemPosition.BOTTOM)
        self.navigationInterface.setAcrylicEnabled(True)

    def _init_window(self) -> None:
        self.setWindowTitle(self._config.device_name)
        self.setWindowIcon(QIcon(str(_ICON_DIR / "star.png")))
        self.resize(1100, 720)
        desktop = QApplication.desktop().availableGeometry()
        self.move(desktop.width() // 2 - self.width() // 2,
                  desktop.height() // 2 - self.height() // 2)
        self.setWindowState(Qt.WindowMaximized)

    def _init_tray(self) -> None:
        exit_action = QAction(QIcon(str(_ICON_DIR / "sp-exit.png")), "Exit", self)
        exit_action.triggered.connect(self.close)
        tray_menu = QMenu(self)
        tray_menu.addAction(exit_action)
        self._tray_icon = QSystemTrayIcon(self)
        self._tray_icon.setIcon(QIcon(str(_ICON_DIR / "star.png")))
        self._tray_icon.setContextMenu(tray_menu)
        self._tray_icon.show()

    def closeEvent(self, event) -> None:
        self._engine.close()
        event.accept()


if __name__ == "__main__":
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())
