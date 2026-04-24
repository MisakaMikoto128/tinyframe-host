"""关于页：作者、项目技术路线、TinyFrame 帧格式可视化。"""
from __future__ import annotations

from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont, QPainter, QPen
from PyQt5.QtWidgets import (QFrame, QGridLayout, QHBoxLayout, QLabel,
                             QScrollArea, QSizePolicy, QVBoxLayout, QWidget)
from qfluentwidgets import (AvatarWidget, BodyLabel, CaptionLabel, CardWidget,
                            FluentIcon as FIF, HyperlinkButton, IconWidget,
                            StrongBodyLabel, TitleLabel, isDarkTheme,
                            setFont as qf_setFont)

_AUTHOR_NAME = "刘沅林"
_AUTHOR_SUBTITLE = "嵌入式 & 上位机开发"
_GITHUB_URL = "https://github.com/MisakaMikoto128"
_GITHUB_USER = _GITHUB_URL.rsplit("/", 1)[-1]
_AVATAR_PATH = Path(__file__).resolve().parent.parent / "resource" / "avatar.png"


# ── Catppuccin Mocha × Fluent 配色 ─────────────────────────────────
# 跟 chart_widget.py 现有配色体系一致（蓝/紫/橙/红为主）
_CAT_BLUE     = "#60a5fa"   # SOF
_CAT_CYAN     = "#67e8f9"   # ID
_CAT_PURPLE   = "#c084fc"   # LEN
_CAT_ORANGE   = "#fb923c"   # TYPE
_CAT_YELLOW   = "#fde68a"   # DATA
_CAT_RED      = "#f87171"   # CRC
_CAT_GREEN    = "#86efac"   # 技术栈卡片图标辅色

# ── 数据 ────────────────────────────────────────────────────────────
_FRAME_FIELDS = [
    # label,    size,       color,        sub
    ("SOF",     "1 字节",    _CAT_BLUE,    "0x1B"),
    ("ID",      "2 字节",    _CAT_CYAN,    "大端 BE"),
    ("LEN",     "2 字节",    _CAT_PURPLE,  "大端 BE"),
    ("TYPE",    "1 字节",    _CAT_ORANGE,  "帧类型"),
    ("DATA",    "N 字节",    _CAT_YELLOW,  "载荷"),
    ("CRC16",   "2 字节",    _CAT_RED,     "Modbus LE"),
]

_TECH_CARDS = [
    (FIF.APPLICATION,     "界面",   "PyQt5 5.15",       "qfluentwidgets 1.8\nFluent 2 风格"),
    (FIF.CONNECT,         "串口",   "QtSerialPort",     "readyRead 事件驱动\n10 ms tick"),
    (FIF.CODE,            "协议栈", "纯 Python",        "0 Qt 依赖\n99% 行覆盖 · 33 测试"),
    (FIF.CERTIFICATE,     "校验",   "crcmod",           "CRC16 Modbus 预设"),
    (FIF.DOWNLOAD,        "打包",   "Nuitka",           "follow-imports\n可选代码签名"),
]

_FEATURES = [
    (FIF.SYNC,              "后台自动刷新",    "串口端口列表 200 ms diff 刷新，显示驱动友好名"),
    (FIF.SEND,              "请求-响应配对",   "MASTER 偶数 ID 自增 · 超时自动触发"),
    (FIF.COPY,              "TSV 复制",        "帧表格 Ctrl+C / 右键菜单，直接粘贴到 Excel"),
    (FIF.SPEED_HIGH,        "实时曲线",        "业务面板目标电压/电流，QPainter 自绘 60 s 窗口"),
    (FIF.CARE_RIGHT_SOLID,  "热重连",          "掉线 QTimer 不停，串口重连后自动恢复"),
    (FIF.PIN,               "设置记忆",        "波特率 / 停止位 / 校验位 / 端口 自动持久化"),
]


# ── 自定义小部件 ────────────────────────────────────────────────────
class _FrameFieldBox(QFrame):
    """帧结构可视化：一个彩色块，上标字段名 + 下标字节数 + 小字说明。"""

    def __init__(self, label: str, size: str, color_hex: str, sub: str, parent=None):
        super().__init__(parent)
        self._color = QColor(color_hex)
        self.setMinimumHeight(92)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        v = QVBoxLayout(self)
        v.setContentsMargins(10, 8, 10, 8)
        v.setSpacing(2)

        name = QLabel(label, self)
        fname = QFont("Consolas", 12)
        fname.setBold(True)
        name.setFont(fname)
        name.setAlignment(Qt.AlignCenter)
        name.setStyleSheet("color: white;")

        size_lbl = QLabel(size, self)
        size_lbl.setFont(QFont("Microsoft YaHei", 9))
        size_lbl.setAlignment(Qt.AlignCenter)
        size_lbl.setStyleSheet("color: rgba(255,255,255,0.85);")

        sub_lbl = QLabel(sub, self)
        sub_lbl.setFont(QFont("Microsoft YaHei", 8))
        sub_lbl.setAlignment(Qt.AlignCenter)
        sub_lbl.setStyleSheet("color: rgba(255,255,255,0.7);")

        v.addStretch()
        v.addWidget(name)
        v.addWidget(size_lbl)
        v.addWidget(sub_lbl)
        v.addStretch()

    def paintEvent(self, _ev):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(self._color)
        painter.drawRoundedRect(self.rect(), 8, 8)
        # 右侧细分隔线（除最后一个），模拟 "字段之间拼接"
        painter.setPen(QPen(QColor(255, 255, 255, 90), 1))
        painter.drawLine(self.width() - 1, 10, self.width() - 1, self.height() - 10)
        painter.end()


class _TechCard(QFrame):
    """技术路线小卡：上方彩色图标圆 + 标题（主技术） + 副标题"""

    def __init__(self, icon, category: str, title: str, detail: str, parent=None):
        super().__init__(parent)
        self.setMinimumSize(152, 140)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setStyleSheet(
            "_TechCard { "
            "  background: rgba(120,120,140,0.06); "
            "  border: 1px solid rgba(120,120,140,0.15); "
            "  border-radius: 10px; "
            "}"
        )

        v = QVBoxLayout(self)
        v.setContentsMargins(14, 12, 14, 12)
        v.setSpacing(6)

        row = QHBoxLayout()
        row.setSpacing(8)
        ic = IconWidget(icon, self)
        ic.setFixedSize(22, 22)
        row.addWidget(ic)
        cat = CaptionLabel(category, self)
        row.addWidget(cat)
        row.addStretch()
        v.addLayout(row)

        title_lbl = StrongBodyLabel(title, self)
        v.addWidget(title_lbl)

        detail_lbl = CaptionLabel(detail, self)
        detail_lbl.setWordWrap(True)
        v.addWidget(detail_lbl)
        v.addStretch()


class _FeatureRow(QWidget):
    """功能亮点条目：图标 + 标题 + 说明。"""

    def __init__(self, icon, title: str, detail: str, parent=None):
        super().__init__(parent)
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(12)

        ic = IconWidget(icon, self)
        ic.setFixedSize(26, 26)
        h.addWidget(ic, 0, Qt.AlignTop)

        v = QVBoxLayout()
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(2)
        t = StrongBodyLabel(title, self)
        d = CaptionLabel(detail, self)
        d.setWordWrap(True)
        v.addWidget(t)
        v.addWidget(d)
        h.addLayout(v, 1)


def _section_card(title: str, body: QWidget) -> CardWidget:
    card = CardWidget()
    v = QVBoxLayout(card)
    v.setContentsMargins(22, 18, 22, 18)
    v.setSpacing(14)
    header = StrongBodyLabel(title, card)
    header_f = QFont("Microsoft YaHei", 12)
    header_f.setBold(True)
    header.setFont(header_f)
    v.addWidget(header)
    v.addWidget(body)
    return card


# ── 主页面 ──────────────────────────────────────────────────────────
class AboutPage(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("aboutPage")

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)

        content = QWidget()
        outer = QVBoxLayout(content)
        outer.setContentsMargins(32, 28, 32, 28)
        outer.setSpacing(18)

        outer.addWidget(self._build_hero())
        outer.addWidget(self._build_tech_card())
        outer.addWidget(self._build_frame_card())
        outer.addWidget(self._build_features_card())
        outer.addStretch()
        outer.addWidget(self._build_footer())

        scroll.setWidget(content)
        wrap = QVBoxLayout(self)
        wrap.setContentsMargins(0, 0, 0, 0)
        wrap.addWidget(scroll)

    # ---- Hero（克制：放大头像、放大名字，保持白卡片） ----
    def _build_hero(self) -> CardWidget:
        card = CardWidget()
        h = QHBoxLayout(card)
        h.setContentsMargins(32, 28, 32, 28)
        h.setSpacing(24)

        avatar = AvatarWidget(str(_AVATAR_PATH))
        avatar.setRadius(72)   # 144 px 圆头像（原 112 -> 144）
        h.addWidget(avatar, 0, Qt.AlignVCenter)

        info = QVBoxLayout()
        info.setSpacing(4)

        name = QLabel(_AUTHOR_NAME, card)
        fname = QFont("Microsoft YaHei", 28)
        fname.setBold(True)
        name.setFont(fname)
        info.addWidget(name)

        subtitle = BodyLabel(_AUTHOR_SUBTITLE, card)
        qf_setFont(subtitle, 14)
        info.addWidget(subtitle)

        info.addSpacing(8)

        link_row = QHBoxLayout()
        link_row.setSpacing(10)
        github_btn = HyperlinkButton(_GITHUB_URL, f"@{_GITHUB_USER}", card)
        github_btn.setIcon(FIF.GITHUB)
        link_row.addWidget(github_btn)

        link_row.addStretch()
        info.addLayout(link_row)

        h.addLayout(info, 1)
        return card

    # ---- 技术路线（一行小卡片） ----
    def _build_tech_card(self) -> CardWidget:
        body = QWidget()
        row = QHBoxLayout(body)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(12)
        for icon, cat, title, detail in _TECH_CARDS:
            row.addWidget(_TechCard(icon, cat, title, detail))
        return _section_card("技术路线", body)

    # ---- TinyFrame 帧格式（彩色可视化） ----
    def _build_frame_card(self) -> CardWidget:
        body = QWidget()
        v = QVBoxLayout(body)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(14)

        # 彩色字段块
        boxes_row = QHBoxLayout()
        boxes_row.setContentsMargins(0, 0, 0, 0)
        boxes_row.setSpacing(6)
        for label, size, color, sub in _FRAME_FIELDS:
            # DATA 字段拉伸突出可变长度
            box = _FrameFieldBox(label, size, color, sub)
            stretch = 3 if label == "DATA" else 1
            boxes_row.addWidget(box, stretch)
        v.addLayout(boxes_row)

        # 上下文说明
        note = BodyLabel(
            "固定开销 <b>8 字节</b> · payload 上限 <b>64 字节</b> · "
            "CRC16 Modbus 覆盖 SOF..DATA",
            body,
        )
        note.setTextFormat(Qt.RichText)
        note.setWordWrap(True)
        v.addWidget(note)

        # 帧类型徽章行
        types_row = QHBoxLayout()
        types_row.setContentsMargins(0, 4, 0, 0)
        types_row.setSpacing(8)
        for type_hex, type_name, type_color in [
            ("0x01", "REG_READ_REQ",  _CAT_BLUE),
            ("0x02", "REG_READ_RSP",  _CAT_GREEN),
            ("0x03", "HEARTBEAT",      _CAT_ORANGE),
        ]:
            chip = self._make_type_chip(type_hex, type_name, type_color, body)
            types_row.addWidget(chip)
        types_row.addStretch()
        v.addLayout(types_row)

        # ID 分配说明
        id_note = CaptionLabel(
            "ID 分配：MASTER 偶数自增（0, 2, 4, …, 0xFFFE 回绕）· 超时默认 200 ms",
            body,
        )
        v.addWidget(id_note)

        return _section_card("TinyFrame 帧格式", body)

    @staticmethod
    def _make_type_chip(hex_str: str, name: str, color_hex: str, parent) -> QFrame:
        chip = QFrame(parent)
        chip.setStyleSheet(
            f"QFrame {{ "
            f"  background: {color_hex}22; "
            f"  border: 1px solid {color_hex}; "
            f"  border-radius: 10px; "
            f"}}"
        )
        h = QHBoxLayout(chip)
        h.setContentsMargins(10, 4, 10, 4)
        h.setSpacing(6)
        dot = QLabel(chip)
        dot.setFixedSize(8, 8)
        dot.setStyleSheet(f"background: {color_hex}; border-radius: 4px;")
        h.addWidget(dot)
        hex_lbl = QLabel(hex_str, chip)
        hex_lbl.setFont(QFont("Consolas", 9, QFont.Bold))
        h.addWidget(hex_lbl)
        name_lbl = QLabel(name, chip)
        name_lbl.setFont(QFont("Consolas", 9))
        h.addWidget(name_lbl)
        return chip

    # ---- 功能亮点（2 列图标网格） ----
    def _build_features_card(self) -> CardWidget:
        body = QWidget()
        grid = QGridLayout(body)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(28)
        grid.setVerticalSpacing(14)
        for i, (icon, title, detail) in enumerate(_FEATURES):
            row = _FeatureRow(icon, title, detail)
            grid.addWidget(row, i // 2, i % 2)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        return _section_card("功能亮点", body)

    # ---- Footer ----
    def _build_footer(self) -> QWidget:
        w = QWidget(self)
        h = QHBoxLayout(w)
        h.setContentsMargins(4, 0, 4, 0)
        copyright_lbl = CaptionLabel(
            f"© {_AUTHOR_NAME} · 基于 TinyFrame by MightyPork · "
            f"{'深色模式' if isDarkTheme() else '浅色模式'}",
            w,
        )
        h.addWidget(copyright_lbl)
        h.addStretch()
        return w
