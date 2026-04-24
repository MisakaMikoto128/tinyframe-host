"""设置页：主题 + 默认超时 + 默认波特率。"""
from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QFrame, QFormLayout, QHBoxLayout, QVBoxLayout
from qfluentwidgets import (BodyLabel, ComboBox, InfoBar, InfoBarPosition,
                            PrimaryPushButton, SpinBox, StrongBodyLabel,
                            SwitchButton, Theme, setTheme, TitleLabel)

from config_manager import AppConfig, ConfigManager

_BAUDS = [9600, 19200, 38400, 57600, 115200, 230400, 460800]


class SettingsPage(QFrame):
    def __init__(self, config: AppConfig, config_manager: ConfigManager, parent=None):
        super().__init__(parent)
        self.setObjectName("settingsPage")
        self._config = config
        self._cm = config_manager

        title = TitleLabel("设置", self)

        self._theme_switch = SwitchButton(self)
        self._theme_switch.setOnText("深色")
        self._theme_switch.setOffText("浅色")
        self._theme_switch.checkedChanged.connect(
            lambda: setTheme(Theme.DARK if self._theme_switch.isChecked() else Theme.LIGHT)
        )

        self._timeout_sb = SpinBox(self)
        self._timeout_sb.setRange(50, 10000)
        self._timeout_sb.setValue(config.default_timeout_ms)
        self._timeout_sb.setSuffix(" ms")

        self._baud_cb = ComboBox(self)
        for b in _BAUDS:
            self._baud_cb.addItem(str(b))
        self._baud_cb.setCurrentText(str(config.default_baud if config.default_baud in _BAUDS else 115200))

        self._save_btn = PrimaryPushButton("保存（下次启动生效）", self)
        self._save_btn.clicked.connect(self._save)

        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(10)
        form.addRow(BodyLabel("主题：", self), self._theme_switch)
        form.addRow(BodyLabel("默认超时：", self), self._timeout_sb)
        form.addRow(BodyLabel("默认波特率：", self), self._baud_cb)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 14, 20, 14)
        outer.addWidget(title)
        outer.addSpacing(8)
        outer.addLayout(form)
        outer.addSpacing(12)
        save_row = QHBoxLayout()
        save_row.addWidget(self._save_btn)
        save_row.addStretch()
        outer.addLayout(save_row)
        outer.addStretch()

    def _save(self) -> None:
        self._config.default_timeout_ms = self._timeout_sb.value()
        self._config.default_baud = int(self._baud_cb.currentText())
        self._cm.save(self._config)
        InfoBar.success("已保存", "下次启动生效",
                        duration=3000, position=InfoBarPosition.TOP, parent=self)
