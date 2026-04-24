"""调试页中部：手动帧发送器。"""
from __future__ import annotations

from PyQt5.QtWidgets import QButtonGroup, QFrame, QGridLayout, QHBoxLayout
from qfluentwidgets import (BodyLabel, InfoBar, InfoBarPosition, LineEdit,
                            PrimaryPushButton, RadioButton, SpinBox,
                            StrongBodyLabel)

from tinyframe import TinyFrameEngine


class FrameSender(QFrame):
    def __init__(self, engine: TinyFrameEngine, default_timeout_ms: int = 200,
                 parent=None):
        super().__init__(parent)
        self._engine = engine

        title = StrongBodyLabel("手动帧发送器", self)

        self._type_edit = LineEdit(self)
        self._type_edit.setPlaceholderText("例如 0x01")
        self._type_edit.setText("0x01")
        self._type_edit.setFixedWidth(120)

        self._payload_edit = LineEdit(self)
        self._payload_edit.setPlaceholderText("HEX，如 10 04 或 1004")
        self._payload_edit.setText("10 04")

        self._mode_send = RadioButton("Send (单向)", self)
        self._mode_query = RadioButton("Query (带响应)", self)
        self._mode_query.setChecked(True)
        self._mode_group = QButtonGroup(self)
        self._mode_group.addButton(self._mode_send)
        self._mode_group.addButton(self._mode_query)

        self._timeout_sb = SpinBox(self)
        self._timeout_sb.setRange(50, 10000)
        self._timeout_sb.setValue(default_timeout_ms)
        self._timeout_sb.setSuffix(" ms")

        self._send_btn = PrimaryPushButton("发送", self)
        self._send_btn.clicked.connect(self._on_send)

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(6)
        grid.addWidget(BodyLabel("TYPE:"), 0, 0)
        grid.addWidget(self._type_edit, 0, 1)
        grid.addWidget(BodyLabel("payload HEX:"), 0, 2)
        grid.addWidget(self._payload_edit, 0, 3, 1, 3)

        mode_row = QHBoxLayout()
        mode_row.setSpacing(12)
        mode_row.addWidget(self._mode_send)
        mode_row.addWidget(self._mode_query)
        mode_row.addWidget(BodyLabel("超时:"))
        mode_row.addWidget(self._timeout_sb)
        mode_row.addStretch()
        mode_row.addWidget(self._send_btn)

        outer = QGridLayout(self)
        outer.setContentsMargins(10, 8, 10, 8)
        outer.addWidget(title, 0, 0)
        outer.addLayout(grid, 1, 0)
        outer.addLayout(mode_row, 2, 0)

    def _parse_type(self) -> int | None:
        text = self._type_edit.text().strip()
        try:
            value = int(text, 16) if text.lower().startswith("0x") else int(text, 16)
        except ValueError:
            InfoBar.error("TYPE 非法", "TYPE 必须是 0x00..0xFF 的十六进制",
                          duration=3000, position=InfoBarPosition.TOP, parent=self)
            return None
        if not 0 <= value <= 0xFF:
            InfoBar.error("TYPE 超范围", "TYPE 必须是 0x00..0xFF",
                          duration=3000, position=InfoBarPosition.TOP, parent=self)
            return None
        return value

    def _parse_payload(self) -> bytes | None:
        text = self._payload_edit.text().strip().replace(" ", "").replace(",", "")
        if text == "":
            return b""
        try:
            data = bytes.fromhex(text)
        except ValueError:
            InfoBar.error("payload 格式错误", "只能是十六进制字符",
                          duration=3000, position=InfoBarPosition.TOP, parent=self)
            return None
        if len(data) > 64:
            InfoBar.error("payload 超长", f"最大 64 字节，实际 {len(data)}",
                          duration=3000, position=InfoBarPosition.TOP, parent=self)
            return None
        return data

    def _on_send(self) -> None:
        if not self._engine.is_open():
            InfoBar.warning("串口未打开", "请先在顶部连接串口",
                            duration=3000, position=InfoBarPosition.TOP, parent=self)
            return
        type_ = self._parse_type()
        if type_ is None:
            return
        payload = self._parse_payload()
        if payload is None:
            return

        if self._mode_send.isChecked():
            self._engine.send(type_, payload)
        else:
            self._engine.query(type_, payload,
                               on_response=lambda f: None,
                               on_timeout=lambda i, t: None,
                               timeout_ms=self._timeout_sb.value())
