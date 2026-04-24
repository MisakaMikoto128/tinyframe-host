"""调试页顶部串口连接条。"""
from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QFrame, QHBoxLayout
from qfluentwidgets import (CaptionLabel, ComboBox, FluentIcon as FIF,
                            IconInfoBadge, InfoBar, InfoBarPosition, InfoLevel,
                            SwitchButton, ToolButton)

from tinyframe import TinyFrameEngine

_BAUDS = [9600, 19200, 38400, 57600, 115200, 230400, 460800]


class SerialPanel(QFrame):
    def __init__(self, engine: TinyFrameEngine, default_baud: int = 115200,
                 parent=None):
        super().__init__(parent)
        self._engine = engine

        self._port_cb = ComboBox(self)
        self._port_cb.setFixedWidth(140)
        self._refresh_btn = ToolButton(FIF.SYNC, self)
        self._refresh_btn.setToolTip("刷新端口列表")
        self._refresh_btn.setFixedSize(28, 28)
        self._refresh_btn.clicked.connect(self._refresh_ports)

        self._baud_cb = ComboBox(self)
        self._baud_cb.setFixedWidth(100)
        for b in _BAUDS:
            self._baud_cb.addItem(str(b))
        self._baud_cb.setCurrentText(str(default_baud if default_baud in _BAUDS else 115200))

        self._toggle = SwitchButton(self)
        self._toggle.setOnText("关闭串口")
        self._toggle.setOffText("打开串口")
        self._toggle.checkedChanged.connect(self._on_toggle)

        self._badge = IconInfoBadge.info(FIF.CONNECT, self)
        self._badge.setLevel(InfoLevel.INFOAMTION)
        self._status_label = CaptionLabel("未连接", self)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(8)
        layout.addWidget(CaptionLabel("端口：", self))
        layout.addWidget(self._port_cb)
        layout.addWidget(self._refresh_btn)
        layout.addSpacing(8)
        layout.addWidget(CaptionLabel("波特率：", self))
        layout.addWidget(self._baud_cb)
        layout.addSpacing(16)
        layout.addWidget(self._toggle)
        layout.addSpacing(8)
        layout.addWidget(self._badge)
        layout.addWidget(self._status_label)
        layout.addStretch()
        self.setFixedHeight(44)

        engine.connected.connect(self._on_connected)
        engine.disconnected.connect(self._on_disconnected)

        self._refresh_ports()

    def _refresh_ports(self) -> None:
        current = self._port_cb.currentText()
        self._port_cb.clear()
        ports = TinyFrameEngine.list_ports()
        for p in ports:
            self._port_cb.addItem(p)
        if current in ports:
            self._port_cb.setCurrentText(current)

    def _on_toggle(self, checked: bool) -> None:
        if checked:
            port = self._port_cb.currentText().strip()
            baud = int(self._baud_cb.currentText())
            if not port:
                InfoBar.error("未选择端口", "请先选择一个可用端口", duration=3000,
                              position=InfoBarPosition.TOP, parent=self)
                self._toggle.setChecked(False)
                return
            ok = self._engine.open(port, baud=baud)
            if not ok:
                self._toggle.setChecked(False)
        else:
            self._engine.close()

    def _on_connected(self, port: str, baud: int) -> None:
        self._badge.setLevel(InfoLevel.SUCCESS)
        self._status_label.setText(f"{port} @ {baud}")
        if not self._toggle.isChecked():
            self._toggle.blockSignals(True)
            self._toggle.setChecked(True)
            self._toggle.blockSignals(False)

    def _on_disconnected(self, reason: str) -> None:
        self._badge.setLevel(InfoLevel.ERROR)
        self._status_label.setText(f"未连接：{reason}")
        if self._toggle.isChecked():
            self._toggle.blockSignals(True)
            self._toggle.setChecked(False)
            self._toggle.blockSignals(False)
        InfoBar.error("串口错误", reason, duration=5000,
                      position=InfoBarPosition.TOP, parent=self)
