from collections import deque

from PyQt5.QtCore import Qt, QRect, QRectF
from PyQt5.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PyQt5.QtWidgets import (QFrame, QHBoxLayout, QLabel, QSizePolicy,
                              QVBoxLayout, QWidget)
from qfluentwidgets import (CaptionLabel, CheckBox, StrongBodyLabel,
                             isDarkTheme)

# ─── 曲线配色（Catppuccin Mocha）──────────────────────────────
_VOLT_HEX  = '#60a5fa'   # 蓝
_CURR_HEX  = '#4ade80'   # 绿
_PWR_HEX   = '#fb923c'   # 橙


class _LegendItem(QWidget):
    """彩色线段指示 + CheckBox 的图例条目。"""

    def __init__(self, label: str, color_hex: str, parent=None):
        super().__init__(parent)
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(6)

        dot = QLabel()
        dot.setFixedSize(18, 3)
        dot.setStyleSheet(f'background:{color_hex};border-radius:1px;')

        self._cb = CheckBox(label)
        self._cb.setChecked(True)

        h.addWidget(dot)
        h.addWidget(self._cb)

    @property
    def checked(self) -> bool:
        return self._cb.isChecked()

    def set_value_text(self, text: str):
        self._cb.setText(text)

    def connect_toggle(self, slot):
        self._cb.stateChanged.connect(slot)


class _ChartCanvas(QWidget):
    """实时折线图绘制区域。"""

    _GRID_ROWS = 4       # 水平网格格数（5条线）
    _Y_LABELS  = ['0%', '25%', '50%', '75%', '100%']
    _LM, _RM, _TM, _BM = 38, 10, 10, 26   # 边距

    def __init__(self, chart: 'RealtimeChart', parent=None):
        super().__init__(parent)
        self._c = chart
        self.setMinimumHeight(160)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    # ── 绘制 ──────────────────────────────────────────────────
    def paintEvent(self, _event):
        dark = isDarkTheme()
        bg      = QColor(28,  28,  45)  if dark else QColor(248, 248, 252)
        grid_c  = QColor(55,  55,  80)  if dark else QColor(210, 210, 225)
        label_c = QColor(120, 120, 160) if dark else QColor(130, 130, 160)
        border_c= QColor(55,  55,  80)  if dark else QColor(200, 200, 215)

        W, H = self.width(), self.height()
        lm, rm, tm, bm = self._LM, self._RM, self._TM, self._BM
        pw = W - lm - rm
        ph = H - tm - bm
        px, py = lm, tm

        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        # 背景 + 圆角边框
        p.fillRect(self.rect(), bg)
        p.setPen(QPen(border_c, 1))
        p.drawRoundedRect(QRectF(.5, .5, W - 1, H - 1), 6, 6)

        font8 = QFont('Consolas', 8)
        p.setFont(font8)

        # 水平网格 + Y 标
        for i in range(self._GRID_ROWS + 1):
            frac = i / self._GRID_ROWS
            y = int(py + ph * (1.0 - frac))
            p.setPen(QPen(grid_c, 1, Qt.DashLine))
            p.drawLine(px, y, px + pw, y)
            p.setPen(label_c)
            p.drawText(0, y - 7, lm - 4, 14,
                       Qt.AlignRight | Qt.AlignVCenter,
                       self._Y_LABELS[i])

        # X 轴时间标注
        ws = self._c.WINDOW_SECONDS
        for frac, lbl in [(0.0, f'-{ws}s'), (0.5, f'-{ws//2}s'), (1.0, '  0s')]:
            x = px + int(frac * pw)
            p.setPen(label_c)
            p.drawText(x - 22, py + ph + 4, 44, 20, Qt.AlignCenter, lbl)

        # 剪裁到绘图区
        p.setClipRect(QRect(px, py, pw, ph))

        c = self._c
        series = [
            (c._volt_data, c._show_volt, _VOLT_HEX, c._volt_max),
            (c._curr_data, c._show_curr, _CURR_HEX, c._curr_max),
            (c._pwr_data,  c._show_pwr,  _PWR_HEX,  c._pwr_max),
        ]

        for data, visible, color_hex, y_max in series:
            if not visible or len(data) < 2:
                continue
            pts = list(data)
            n   = len(pts)
            cap = c._max_points

            path = QPainterPath()
            first = True
            for j, val in enumerate(pts):
                xf = (cap - n + j) / max(cap - 1, 1)
                yf = min(val / y_max, 1.0) if y_max > 0 else 0.0
                xp = px + xf * pw
                yp = py + ph * (1.0 - yf)
                if first:
                    path.moveTo(xp, yp)
                    first = False
                else:
                    path.lineTo(xp, yp)

            p.setPen(QPen(QColor(color_hex), 2,
                          Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.setBrush(Qt.NoBrush)
            p.drawPath(path)

        p.end()


class RealtimeChart(QFrame):
    """实时电压/电流/功率折线图。

    调用 push(volt, curr, power) 追加数据点；图表只保留最近
    WINDOW_SECONDS 秒的数据，不可缩放。
    """

    WINDOW_SECONDS = 60
    _PUSH_MS = 150   # 外部 push 间隔（与 updateTableWidget 定时器一致）

    def __init__(self, volt_max=1000.0, curr_max=100.0, pwr_max=30000.0,
                 parent=None):
        super().__init__(parent)
        cap = max(int(self.WINDOW_SECONDS * 1000 / self._PUSH_MS), 2)
        self._max_points = cap
        self._volt_data  = deque(maxlen=cap)
        self._curr_data  = deque(maxlen=cap)
        self._pwr_data   = deque(maxlen=cap)
        self._volt_max   = volt_max  if volt_max  > 0 else 1000.0
        self._curr_max   = curr_max  if curr_max  > 0 else 100.0
        self._pwr_max    = pwr_max   if pwr_max   > 0 else 30000.0
        self._show_volt  = True
        self._show_curr  = True
        self._show_pwr   = True
        self.setFrameShape(QFrame.NoFrame)
        self._build_ui()

    # ── 公共接口 ──────────────────────────────────────────────
    def push(self, volt: float, curr: float, power: float):
        """追加一个数据点并刷新图表。"""
        self._volt_data.append(float(volt))
        self._curr_data.append(float(curr))
        self._pwr_data.append(float(power))
        self._canvas.update()
        self._volt_item.set_value_text(f'电压  {volt:.1f} V')
        self._curr_item.set_value_text(f'电流  {curr:.2f} A')
        self._pwr_item.set_value_text(f'功率  {power:.0f} W')

    # ── 构建 UI ───────────────────────────────────────────────
    def _build_ui(self):
        vbox = QVBoxLayout(self)
        vbox.setContentsMargins(10, 8, 10, 8)
        vbox.setSpacing(6)

        # 标题行
        hdr = QHBoxLayout()
        hdr.setSpacing(8)
        title = StrongBodyLabel('实时曲线')
        hdr.addWidget(title)
        hdr.addStretch()
        hdr.addWidget(CaptionLabel(f'时间窗口 {self.WINDOW_SECONDS} s'))
        vbox.addLayout(hdr)

        # 图例行
        self._volt_item = _LegendItem('电压  — V',   _VOLT_HEX)
        self._curr_item = _LegendItem('电流  — A',   _CURR_HEX)
        self._pwr_item  = _LegendItem('功率  — W',   _PWR_HEX)

        self._volt_item.connect_toggle(
            lambda s: self._toggle('volt', s == Qt.Checked))
        self._curr_item.connect_toggle(
            lambda s: self._toggle('curr', s == Qt.Checked))
        self._pwr_item.connect_toggle(
            lambda s: self._toggle('pwr',  s == Qt.Checked))

        legend = QHBoxLayout()
        legend.setSpacing(20)
        legend.addWidget(self._volt_item)
        legend.addWidget(self._curr_item)
        legend.addWidget(self._pwr_item)
        legend.addStretch()
        vbox.addLayout(legend)

        # 画布
        self._canvas = _ChartCanvas(self, self)
        vbox.addWidget(self._canvas, stretch=1)

    def _toggle(self, series: str, show: bool):
        if series == 'volt':
            self._show_volt = show
        elif series == 'curr':
            self._show_curr = show
        elif series == 'pwr':
            self._show_pwr = show
        self._canvas.update()
