"""业务面板：读设定点 + 心跳 + 实时曲线。"""
from __future__ import annotations

import time

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QFrame, QHBoxLayout, QSplitter, QVBoxLayout
from qfluentwidgets import (BodyLabel, CaptionLabel, CardWidget, ComboBox,
                            DisplayLabel, FluentIcon as FIF, IconInfoBadge,
                            InfoBar, InfoBarPosition, InfoLevel,
                            PrimaryPushButton, StrongBodyLabel, SwitchButton,
                            TitleLabel)

from chart_widget import RealtimeChart
from config_manager import AppConfig
from tinyframe import TFFrame, TinyFrameEngine

_REG_ADDR = 0x10
_REG_COUNT = 4
_REQ_TYPE = 0x01
_RSP_TYPE = 0x02
_POLL_PERIODS_MS = [100, 200, 500, 1000]
_HEARTBEAT_PERIODS_MS = [500, 1000, 2000]
_TIMEOUT_INFOBAR_MIN_INTERVAL_S = 5.0


def _make_card(title: str) -> tuple[CardWidget, DisplayLabel, CaptionLabel]:
    card = CardWidget()
    v = QVBoxLayout(card)
    v.setContentsMargins(14, 10, 14, 10)
    v.setSpacing(2)
    v.addWidget(BodyLabel(title, card))
    value = DisplayLabel("---", card)
    value.setAlignment(Qt.AlignLeft)
    v.addWidget(value)
    sub = CaptionLabel("", card)
    v.addWidget(sub)
    return card, value, sub


class BusinessPage(QFrame):
    def __init__(self, engine: TinyFrameEngine, config: AppConfig, parent=None):
        super().__init__(parent)
        self.setObjectName("businessPage")
        self._engine = engine
        self._config = config
        self._last_v_str = "---"
        self._last_i_str = "---"
        self._last_timeout_infobar_ts = 0.0

        # 顶部状态徽章
        self._status_badge = IconInfoBadge.info(FIF.CONNECT, self)
        self._status_text = CaptionLabel("串口未连接 — 请到协议调试页连接", self)
        status_row = QHBoxLayout()
        status_row.setContentsMargins(12, 8, 12, 4)
        status_row.addWidget(self._status_badge)
        status_row.addWidget(self._status_text)
        status_row.addStretch()

        # 左侧曲线
        self._chart = RealtimeChart(
            volt_max=config.chart_volt_max,
            curr_max=config.chart_curr_max,
            show_power=False,
            parent=self,
        )

        # 右侧控制面板
        self._v_card, self._v_value, self._v_sub = _make_card("目标电压 (V)")
        self._i_card, self._i_value, self._i_sub = _make_card("目标电流 (A)")

        self._read_btn = PrimaryPushButton("读取一次", self)
        self._read_btn.setIcon(FIF.SYNC)
        self._read_btn.clicked.connect(self._read_once)

        self._poll_switch = SwitchButton(self)
        self._poll_switch.setOnText("自动轮询 开")
        self._poll_switch.setOffText("自动轮询 关")
        self._poll_cb = ComboBox(self)
        for ms in _POLL_PERIODS_MS:
            self._poll_cb.addItem(f"{ms} ms", userData=ms)
        # 若 config 值不在列表里，回退到 500 ms 避免 setCurrentText 的 silent no-op
        _poll_default = config.default_poll_ms if config.default_poll_ms in _POLL_PERIODS_MS else 500
        self._poll_cb.setCurrentIndex(_POLL_PERIODS_MS.index(_poll_default))
        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._read_once)
        self._poll_switch.checkedChanged.connect(self._on_poll_switch)
        self._poll_cb.currentIndexChanged.connect(self._on_poll_period_changed)

        self._hb_switch = SwitchButton(self)
        self._hb_switch.setOnText("心跳 开")
        self._hb_switch.setOffText("心跳 关")
        self._hb_cb = ComboBox(self)
        for ms in _HEARTBEAT_PERIODS_MS:
            self._hb_cb.addItem(f"{ms} ms", userData=ms)
        _hb_default = config.default_heartbeat_ms if config.default_heartbeat_ms in _HEARTBEAT_PERIODS_MS else 1000
        self._hb_cb.setCurrentIndex(_HEARTBEAT_PERIODS_MS.index(_hb_default))
        self._hb_timer = QTimer(self)
        self._hb_timer.timeout.connect(self._send_heartbeat)
        self._hb_switch.checkedChanged.connect(self._on_hb_switch)
        self._hb_cb.currentIndexChanged.connect(self._on_hb_period_changed)

        self._last_update_lbl = CaptionLabel("上次更新: 从未", self)

        poll_row = QHBoxLayout()
        poll_row.setSpacing(8)
        poll_row.addWidget(self._poll_switch)
        poll_row.addWidget(self._poll_cb)
        poll_row.addStretch()

        hb_row = QHBoxLayout()
        hb_row.setSpacing(8)
        hb_row.addWidget(self._hb_switch)
        hb_row.addWidget(self._hb_cb)
        hb_row.addStretch()

        right = QFrame(self)
        right_v = QVBoxLayout(right)
        right_v.setContentsMargins(12, 8, 12, 12)
        right_v.setSpacing(10)
        right_v.addWidget(TitleLabel("设定点", right))
        right_v.addWidget(self._v_card)
        right_v.addWidget(self._i_card)
        right_v.addWidget(self._read_btn)
        right_v.addWidget(StrongBodyLabel("自动轮询", right))
        right_v.addLayout(poll_row)
        right_v.addWidget(StrongBodyLabel("心跳", right))
        right_v.addLayout(hb_row)
        right_v.addStretch()
        right_v.addWidget(self._last_update_lbl)

        splitter = QSplitter(Qt.Horizontal, self)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(self._chart)
        splitter.addWidget(right)
        splitter.setSizes([640, 360])

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addLayout(status_row)
        outer.addWidget(splitter, 1)

        engine.connected.connect(self._on_connected)
        engine.disconnected.connect(self._on_disconnected)

        self._apply_enabled_state()

    # ---- 连接状态 ----
    def _on_connected(self, port: str) -> None:
        self._status_badge.setLevel(InfoLevel.SUCCESS)
        self._status_text.setText(f"已连接 — {port} @ {self._config.default_baud}")
        self._apply_enabled_state()

    def _on_disconnected(self, reason: str) -> None:
        self._status_badge.setLevel(InfoLevel.ERROR)
        self._status_text.setText(f"串口未连接 — {reason}")
        self._apply_enabled_state()

    def _apply_enabled_state(self) -> None:
        open_ = self._engine.is_open()
        # 发送按钮根据连接状态启用/禁用；轮询/心跳开关可以自由切（关闭时 QTimer 仍会触发但 engine 会静默丢弃）
        self._read_btn.setEnabled(open_)

    # ---- 轮询 / 心跳开关 ----
    def _on_poll_switch(self, checked: bool) -> None:
        if checked:
            self._poll_timer.start(self._poll_cb.currentData())
        else:
            self._poll_timer.stop()

    def _on_poll_period_changed(self) -> None:
        if self._poll_switch.isChecked():
            self._poll_timer.start(self._poll_cb.currentData())

    def _on_hb_switch(self, checked: bool) -> None:
        if checked:
            self._hb_timer.start(self._hb_cb.currentData())
        else:
            self._hb_timer.stop()

    def _on_hb_period_changed(self) -> None:
        if self._hb_switch.isChecked():
            self._hb_timer.start(self._hb_cb.currentData())

    # ---- 具体请求 ----
    def _read_once(self) -> None:
        if not self._engine.is_open():
            return
        payload = bytes([_REG_ADDR, _REG_COUNT])
        self._engine.query(
            _REQ_TYPE, payload,
            on_response=self._on_setpoint_response,
            on_timeout=self._on_setpoint_timeout,
            timeout_ms=self._config.default_timeout_ms,
        )

    def _send_heartbeat(self) -> None:
        if not self._engine.is_open():
            return
        tick_ms = int(time.monotonic() * 1000) & 0xFFFFFFFF
        self._engine.send_heartbeat(tick_ms)

    # ---- 响应处理 ----
    def _on_setpoint_response(self, frame: TFFrame) -> None:
        if frame.type != _RSP_TYPE:
            return
        data = frame.data
        if len(data) != 10:
            InfoBar.error("响应格式错误", f"期望 10 字节，实际 {len(data)}",
                          duration=3000, position=InfoBarPosition.TOP, parent=self)
            return
        if data[0] != _REG_ADDR or data[1] != _REG_COUNT:
            InfoBar.error("响应地址不匹配",
                          f"期望 addr=0x{_REG_ADDR:02X} count={_REG_COUNT}，实际 addr=0x{data[0]:02X} count={data[1]}",
                          duration=3000, position=InfoBarPosition.TOP, parent=self)
            return
        v_mV = int.from_bytes(data[2:6], "big")
        i_mA = int.from_bytes(data[6:10], "big")
        voltage = v_mV / 1000.0
        current = i_mA / 1000.0
        self._last_v_str = f"{voltage:.3f}"
        self._last_i_str = f"{current:.3f}"
        self._v_value.setText(f"{self._last_v_str}")
        self._i_value.setText(f"{self._last_i_str}")
        self._v_sub.setText(f"{v_mV} mV")
        self._i_sub.setText(f"{i_mA} mA")
        self._chart.push(voltage, current, 0.0)
        self._last_update_lbl.setText("上次更新: " + time.strftime("%H:%M:%S"))

    def _on_setpoint_timeout(self, id_: int, type_: int) -> None:
        self._v_value.setText("TIMEOUT")
        self._i_value.setText("TIMEOUT")
        self._v_sub.setText(f"上次: {self._last_v_str} V")
        self._i_sub.setText(f"上次: {self._last_i_str} A")
        now = time.monotonic()
        if now - self._last_timeout_infobar_ts >= _TIMEOUT_INFOBAR_MIN_INTERVAL_S:
            self._last_timeout_infobar_ts = now
            InfoBar.warning("响应超时", "读取设定点未收到响应",
                            duration=3000, position=InfoBarPosition.TOP, parent=self)
