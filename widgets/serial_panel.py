"""调试页顶部串口连接条（两行布局）。"""
from __future__ import annotations

from typing import Optional

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QFrame, QGridLayout, QHBoxLayout
from qfluentwidgets import (CaptionLabel, ComboBox, FluentIcon as FIF,
                            IconInfoBadge, InfoBar, InfoBarPosition, InfoLevel,
                            SwitchButton)

from config_manager import AppConfig, ConfigManager
from tinyframe import TinyFrameEngine

_BAUDS = [9600, 19200, 38400, 57600, 115200, 230400, 460800]
_STOP_BITS = [1, 2]
_PARITIES = [("none", "None"), ("even", "Even"), ("odd", "Odd")]

_PORT_REFRESH_MS = 200


class SerialPanel(QFrame):
    def __init__(self,
                 engine: TinyFrameEngine,
                 config: AppConfig,
                 config_manager: Optional[ConfigManager] = None,
                 parent=None):
        super().__init__(parent)
        self._engine = engine
        self._config = config
        self._cm = config_manager  # 可能为 None（老调用点未传）

        # ── 第 1 行控件 ──
        self._port_cb = ComboBox(self)
        self._port_cb.setMinimumWidth(260)  # 容纳 "COM8  USB-SERIAL CH340" 这样的文本
        # 用户手动切换时回写 config.default_port；程序性刷新通过 blockSignals 规避
        self._port_cb.currentIndexChanged.connect(self._on_port_changed)

        self._baud_cb = ComboBox(self)
        self._baud_cb.setFixedWidth(100)
        for b in _BAUDS:
            self._baud_cb.addItem(str(b), userData=b)
        self._select_combo_by_data(self._baud_cb, config.default_baud, fallback=115200)
        self._baud_cb.currentIndexChanged.connect(self._on_baud_changed)

        self._toggle = SwitchButton(self)
        self._toggle.setOnText("关闭串口")
        self._toggle.setOffText("打开串口")
        self._toggle.checkedChanged.connect(self._on_toggle)

        self._badge = IconInfoBadge.info(FIF.CONNECT, self)
        self._badge.setLevel(InfoLevel.INFOAMTION)
        self._status_label = CaptionLabel("未连接", self)

        row1 = QHBoxLayout()
        row1.setContentsMargins(0, 0, 0, 0)
        row1.setSpacing(8)
        row1.addWidget(CaptionLabel("端口：", self))
        row1.addWidget(self._port_cb)
        row1.addSpacing(8)
        row1.addWidget(CaptionLabel("波特率：", self))
        row1.addWidget(self._baud_cb)
        row1.addSpacing(16)
        row1.addWidget(self._toggle)
        row1.addSpacing(8)
        row1.addWidget(self._badge)
        row1.addWidget(self._status_label)
        row1.addStretch()

        # ── 第 2 行控件 ──
        self._stop_cb = ComboBox(self)
        self._stop_cb.setFixedWidth(80)
        for sb in _STOP_BITS:
            self._stop_cb.addItem(str(sb), userData=sb)
        self._select_combo_by_data(self._stop_cb, config.default_stop_bits, fallback=1)
        self._stop_cb.currentIndexChanged.connect(self._on_stop_changed)

        self._parity_cb = ComboBox(self)
        self._parity_cb.setFixedWidth(90)
        for key, label in _PARITIES:
            self._parity_cb.addItem(label, userData=key)
        self._select_combo_by_data(self._parity_cb, config.default_parity, fallback="none")
        self._parity_cb.currentIndexChanged.connect(self._on_parity_changed)

        row2 = QHBoxLayout()
        row2.setContentsMargins(0, 0, 0, 0)
        row2.setSpacing(8)
        row2.addWidget(CaptionLabel("停止位：", self))
        row2.addWidget(self._stop_cb)
        row2.addSpacing(16)
        row2.addWidget(CaptionLabel("校验位：", self))
        row2.addWidget(self._parity_cb)
        row2.addStretch()

        # ── 外层两行 ──
        outer = QGridLayout(self)
        outer.setContentsMargins(8, 6, 8, 6)
        outer.setVerticalSpacing(4)
        outer.addLayout(row1, 0, 0)
        outer.addLayout(row2, 1, 0)
        self.setFixedHeight(80)

        engine.connected.connect(self._on_connected)
        engine.disconnected.connect(self._on_disconnected)

        # 后台 200ms 周期刷新端口列表（diff 更新，无变化时不动 UI）
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(_PORT_REFRESH_MS)
        self._refresh_timer.timeout.connect(self._refresh_ports)
        self._refresh_timer.start()
        self._refresh_ports()

    # ── Helpers ──
    @staticmethod
    def _select_combo_by_data(cb: ComboBox, data, fallback) -> None:
        for i in range(cb.count()):
            if cb.itemData(i) == data:
                cb.setCurrentIndex(i)
                return
        for i in range(cb.count()):
            if cb.itemData(i) == fallback:
                cb.setCurrentIndex(i)
                return
        if cb.count() > 0:
            cb.setCurrentIndex(0)

    def _save_config(self) -> None:
        if self._cm is not None:
            self._cm.save(self._config)

    # ── 端口刷新（diff） ──
    def _refresh_ports(self) -> None:
        new_ports = TinyFrameEngine.list_ports()  # [(name, desc), ...]
        current_names = [self._port_cb.itemData(i) for i in range(self._port_cb.count())]
        new_names = [n for n, _ in new_ports]
        if current_names == new_names:
            return  # 无变化，不动 UI 避免闪烁和 currentIndex 抖动
        selected = self._port_cb.currentData()
        self._port_cb.blockSignals(True)
        self._port_cb.clear()
        for name, desc in new_ports:
            text = f"{name}  {desc}" if desc else name
            self._port_cb.addItem(text, userData=name)
        # 尝试保留之前的选择
        if selected and selected in new_names:
            self._port_cb.setCurrentIndex(new_names.index(selected))
        elif self._config.default_port and self._config.default_port in new_names:
            self._port_cb.setCurrentIndex(new_names.index(self._config.default_port))
        self._port_cb.blockSignals(False)

    # ── 串口开关 ──
    def _on_toggle(self, checked: bool) -> None:
        if checked:
            port = self._port_cb.currentData()
            baud = self._baud_cb.currentData() or 115200
            stop_bits = self._stop_cb.currentData() or 1
            parity = self._parity_cb.currentData() or "none"
            if not port:
                InfoBar.error("未选择端口", "请先选择一个可用端口", duration=3000,
                              position=InfoBarPosition.TOP, parent=self)
                self._toggle.setChecked(False)
                return
            ok = self._engine.open(
                port,
                baud=baud,
                data_bits=8,
                stop_bits=stop_bits,
                parity=parity,
            )
            if not ok:
                self._toggle.setChecked(False)
        else:
            self._engine.close()

    # ── 配置变更持久化 ──
    def _on_port_changed(self) -> None:
        data = self._port_cb.currentData()
        if isinstance(data, str) and data and data != self._config.default_port:
            self._config.default_port = data
            self._save_config()

    def _on_baud_changed(self) -> None:
        data = self._baud_cb.currentData()
        if isinstance(data, int):
            self._config.default_baud = data
            self._save_config()

    def _on_stop_changed(self) -> None:
        data = self._stop_cb.currentData()
        if isinstance(data, int):
            self._config.default_stop_bits = data
            self._save_config()

    def _on_parity_changed(self) -> None:
        data = self._parity_cb.currentData()
        if isinstance(data, str):
            self._config.default_parity = data
            self._save_config()

    # ── 引擎事件 ──
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
