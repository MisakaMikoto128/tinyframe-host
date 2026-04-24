"""调试页底部：收发日志（帧视图 + 原始 HEX 视图 + 过滤/暂停）。"""
from __future__ import annotations

import time
from collections import deque

from PyQt5.QtCore import QEvent, Qt
from PyQt5.QtGui import QBrush, QColor, QFont, QKeySequence
from PyQt5.QtWidgets import (QAction, QApplication, QFrame, QHBoxLayout,
                             QHeaderView, QMenu, QStackedWidget,
                             QTableWidgetItem, QVBoxLayout)
from qfluentwidgets import (CaptionLabel, ComboBox, FluentIcon as FIF, InfoBar,
                            InfoBarPosition, MessageBox, Pivot, TableWidget,
                            TextEdit, ToolButton)

from tinyframe import TFFrame, TinyFrameEngine

_MAX_TABLE_ROWS = 5000
_MAX_PAUSE_BUFFER = 10000
_MAX_HEX_BLOCKS = 10000  # QTextEdit 的 maximumBlockCount，每块一行

_COLOR_TX = QColor("#3b82f6")
_COLOR_RX = QColor("#22c55e")
_COLOR_ERROR = QColor("#ef4444")
_COLOR_WARN = QColor("#f59e0b")


class FrameLogView(QFrame):
    def __init__(self, engine: TinyFrameEngine, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._paused = False
        self._buffer: deque = deque(maxlen=_MAX_PAUSE_BUFFER)
        self._dropped_while_paused = 0
        self._crc_err_count = 0
        self._timeout_count = 0

        # 工具条
        self._pivot = Pivot(self)
        self._pivot.addItem(routeKey="frame", text="帧视图")
        self._pivot.addItem(routeKey="raw", text="原始 HEX")
        self._pivot.setCurrentItem("frame")
        self._pivot.currentItemChanged.connect(self._on_pivot_changed)

        self._filter_cb = ComboBox(self)
        self._filter_cb.addItem("全部 TYPE")
        self._filter_cb.setFixedWidth(130)
        self._known_types: set[int] = set()
        self._filter_cb.currentIndexChanged.connect(self._refresh_table_filter)

        self._pause_btn = ToolButton(FIF.PAUSE, self)
        self._pause_btn.setToolTip("暂停/恢复")
        self._pause_btn.clicked.connect(self._toggle_pause)

        self._clear_btn = ToolButton(FIF.DELETE, self)
        self._clear_btn.setToolTip("清空日志")
        self._clear_btn.clicked.connect(self._on_clear)

        self._crc_lbl = CaptionLabel("CRC错误: 0", self)
        self._timeout_lbl = CaptionLabel("超时: 0", self)
        self._drop_lbl = CaptionLabel("已丢弃: 0", self)

        toolbar = QHBoxLayout()
        toolbar.addWidget(self._pivot)
        toolbar.addSpacing(12)
        toolbar.addWidget(self._filter_cb)
        toolbar.addSpacing(8)
        toolbar.addWidget(self._pause_btn)
        toolbar.addWidget(self._clear_btn)
        toolbar.addStretch()
        toolbar.addWidget(self._crc_lbl)
        toolbar.addSpacing(8)
        toolbar.addWidget(self._timeout_lbl)
        toolbar.addSpacing(8)
        toolbar.addWidget(self._drop_lbl)

        # 帧视图表格
        self._table = TableWidget(self)
        self._table.setColumnCount(7)
        self._table.setHorizontalHeaderLabels(
            ["时间", "方向", "TYPE", "ID", "LEN", "CRC", "payload HEX"])
        self._table.setEditTriggers(TableWidget.NoEditTriggers)
        self._table.verticalHeader().hide()
        self._table.horizontalHeader().setSectionResizeMode(6, QHeaderView.Stretch)
        mono = QFont("Consolas", 9)
        self._table.setFont(mono)

        # 允许按单元格选中、拖选多行多列；Ctrl+C 或右键菜单复制为 TSV
        self._table.setSelectionBehavior(TableWidget.SelectItems)
        self._table.setSelectionMode(TableWidget.ExtendedSelection)
        self._table.installEventFilter(self)
        self._table.setContextMenuPolicy(Qt.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._on_table_context_menu)

        # 原始 HEX 视图
        self._hex_view = TextEdit(self)
        self._hex_view.setReadOnly(True)
        self._hex_view.setFont(mono)
        self._hex_view.document().setMaximumBlockCount(_MAX_HEX_BLOCKS)

        self._stack = QStackedWidget(self)
        self._stack.addWidget(self._table)
        self._stack.addWidget(self._hex_view)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 10)
        layout.setSpacing(6)
        layout.addLayout(toolbar)
        layout.addWidget(self._stack, 1)

        # 订阅 engine 信号
        engine.frameReceived.connect(lambda f: self._on_event("frame", f))
        engine.frameSent.connect(lambda f: self._on_event("frame", f))
        engine.queryTimeout.connect(self._on_timeout)
        engine.crcFailed.connect(self._on_crc_failed)
        engine.rawBytesIn.connect(lambda b: self._on_event("raw_in", b))
        engine.rawBytesOut.connect(lambda b: self._on_event("raw_out", b))

    # ---- Pivot 切换 ----
    def _on_pivot_changed(self, key: str) -> None:
        self._stack.setCurrentIndex(0 if key == "frame" else 1)

    # ---- 暂停 / 清空 ----
    def _toggle_pause(self) -> None:
        self._paused = not self._paused
        self._pause_btn.setIcon(FIF.PLAY if self._paused else FIF.PAUSE)
        if not self._paused:
            self._table.setUpdatesEnabled(False)
            try:
                while self._buffer:
                    kind, payload = self._buffer.popleft()
                    self._apply(kind, payload)
            finally:
                self._table.setUpdatesEnabled(True)
                self._table.scrollToBottom()
            if self._dropped_while_paused:
                self._drop_lbl.setText(f"已丢弃: {self._dropped_while_paused}")

    def _on_clear(self) -> None:
        w = MessageBox("确认清空", "将清空表格、原始 HEX 视图以及所有计数器。", self.window())
        if not w.exec():
            return
        self._table.setRowCount(0)
        self._hex_view.clear()
        self._known_types.clear()
        self._filter_cb.clear()
        self._filter_cb.addItem("全部 TYPE")
        self._buffer.clear()
        self._dropped_while_paused = 0
        self._crc_err_count = 0
        self._timeout_count = 0
        self._crc_lbl.setText("CRC错误: 0")
        self._timeout_lbl.setText("超时: 0")
        self._drop_lbl.setText("已丢弃: 0")

    # ---- 事件接入 ----
    def _register_type(self, type_: int) -> None:
        if type_ in self._known_types:
            return
        self._known_types.add(type_)
        self._filter_cb.addItem(f"TYPE=0x{type_:02X}", userData=type_)

    def _on_event(self, kind: str, payload) -> None:
        if kind == "frame" and isinstance(payload, TFFrame):
            self._register_type(payload.type)

        if self._paused:
            if len(self._buffer) >= _MAX_PAUSE_BUFFER:
                self._dropped_while_paused += 1
                if self._dropped_while_paused == 1:
                    InfoBar.warning("暂停缓冲区已满",
                                    "恢复日志以清空缓冲，期间事件将被丢弃",
                                    duration=5000,
                                    position=InfoBarPosition.TOP, parent=self)
                return
            self._buffer.append((kind, payload))
            return
        self._apply(kind, payload)

    def _apply(self, kind: str, payload) -> None:
        if kind == "frame":
            self._append_frame(payload)
        elif kind == "raw_in":
            self._append_hex("IN", payload)
        elif kind == "raw_out":
            self._append_hex("OUT", payload)

    def _on_timeout(self, id_: int, type_: int) -> None:
        self._timeout_count += 1
        self._timeout_lbl.setText(f"超时: {self._timeout_count}")
        if self._paused:
            self._buffer.append(("timeout", (id_, type_)))
            return
        self._append_special("TIMEOUT", f"ID={id_:#06x} TYPE={type_:#04x}", _COLOR_ERROR)

    def _on_crc_failed(self, frame: TFFrame) -> None:
        self._crc_err_count += 1
        self._crc_lbl.setText(f"CRC错误: {self._crc_err_count}")
        if self._paused:
            self._buffer.append(("crc_fail", frame))
            return
        self._append_special("CRC_FAIL",
                             f"TYPE={frame.type:#04x} ID={frame.id:#06x} DATA={frame.data.hex(' ')}",
                             _COLOR_ERROR)

    # ---- 表格追加 ----
    def _append_frame(self, frame: TFFrame) -> None:
        filter_type = self._filter_cb.currentData()
        if filter_type is not None and filter_type != frame.type:
            return

        row = self._table.rowCount()
        if row >= _MAX_TABLE_ROWS:
            self._table.removeRow(0)
            row -= 1
        self._table.insertRow(row)

        ts = self._now_ts()
        direction = "TX" if frame.direction == "tx" else "RX"
        color = _COLOR_TX if frame.direction == "tx" else _COLOR_RX
        items = [
            ts,
            direction,
            f"0x{frame.type:02X}",
            f"0x{frame.id:04X}",
            str(len(frame.data)),
            "OK",
            frame.data.hex(" "),
        ]
        for col, text in enumerate(items):
            it = QTableWidgetItem(text)
            it.setForeground(QBrush(color))
            self._table.setItem(row, col, it)
        self._table.scrollToBottom()

    def _append_special(self, tag: str, detail: str, color: QColor) -> None:
        row = self._table.rowCount()
        if row >= _MAX_TABLE_ROWS:
            self._table.removeRow(0)
            row -= 1
        self._table.insertRow(row)
        ts = self._now_ts()
        items = [ts, tag, "", "", "", tag, detail]
        for col, text in enumerate(items):
            it = QTableWidgetItem(text)
            it.setForeground(QBrush(color))
            self._table.setItem(row, col, it)
        self._table.scrollToBottom()

    def _append_hex(self, tag: str, data: bytes) -> None:
        ts = time.strftime("%H:%M:%S")
        hex_str = data.hex(" ")
        self._hex_view.append(f"[{ts}] {tag}: {hex_str}")

    @staticmethod
    def _now_ts() -> str:
        now = time.time()
        return time.strftime("%H:%M:%S", time.localtime(now)) + f".{int((now % 1) * 1000):03d}"

    # ---- 过滤 ----
    def _refresh_table_filter(self) -> None:
        filter_type = self._filter_cb.currentData()
        for row in range(self._table.rowCount()):
            type_item = self._table.item(row, 2)
            if type_item is None:
                continue
            txt = type_item.text()
            if not txt.startswith("0x"):
                # 特殊行（CRC_FAIL / TIMEOUT）不过滤
                self._table.setRowHidden(row, False)
                continue
            row_type = int(txt, 16)
            self._table.setRowHidden(row, filter_type is not None and row_type != filter_type)

    # ---- 复制 ----
    def eventFilter(self, obj, event) -> bool:
        if obj is self._table and event.type() == QEvent.KeyPress:
            if event.matches(QKeySequence.Copy):
                self._copy_selection()
                return True
        return super().eventFilter(obj, event)

    def _on_table_context_menu(self, pos) -> None:
        menu = QMenu(self._table)
        copy_action = QAction("复制 (Ctrl+C)", menu)
        copy_action.setEnabled(bool(self._table.selectedRanges()))
        copy_action.triggered.connect(self._copy_selection)
        menu.addAction(copy_action)
        menu.exec_(self._table.viewport().mapToGlobal(pos))

    def _copy_selection(self) -> None:
        """把当前选中的表格区域拼成 TSV 塞到剪贴板。多个不连续区域按行合并。"""
        ranges = self._table.selectedRanges()
        if not ranges:
            return
        # 汇总选中的所有 (row, col)；按行聚合，按列升序排列
        rows: dict[int, dict[int, str]] = {}
        for r in ranges:
            for row in range(r.topRow(), r.bottomRow() + 1):
                if self._table.isRowHidden(row):
                    continue
                for col in range(r.leftColumn(), r.rightColumn() + 1):
                    item = self._table.item(row, col)
                    text = item.text() if item is not None else ""
                    rows.setdefault(row, {})[col] = text
        if not rows:
            return
        lines = []
        for row in sorted(rows):
            cols = rows[row]
            # 按选中列升序拼接；中间空列用空字符串占位保持对齐
            min_c, max_c = min(cols), max(cols)
            line = "\t".join(cols.get(c, "") for c in range(min_c, max_c + 1))
            lines.append(line)
        QApplication.clipboard().setText("\n".join(lines))
