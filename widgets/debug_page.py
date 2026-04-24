"""协议调试页容器。"""
from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QFrame, QSplitter, QVBoxLayout

from config_manager import AppConfig
from tinyframe import TinyFrameEngine
from widgets.frame_log_view import FrameLogView
from widgets.frame_sender import FrameSender
from widgets.serial_panel import SerialPanel


class DebugPage(QFrame):
    def __init__(self, engine: TinyFrameEngine, config: AppConfig, parent=None):
        super().__init__(parent)
        self.setObjectName("debugPage")

        self._serial_panel = SerialPanel(engine, default_baud=config.default_baud, parent=self)
        self._frame_sender = FrameSender(engine, default_timeout_ms=config.default_timeout_ms,
                                         parent=self)
        self._log_view = FrameLogView(engine, parent=self)

        splitter = QSplitter(Qt.Vertical, self)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(self._frame_sender)
        splitter.addWidget(self._log_view)
        splitter.setSizes([160, 480])

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._serial_panel)
        layout.addWidget(splitter, 1)
