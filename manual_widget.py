import time
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QColor, QTextCursor
from PyQt5.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QWidget, QLabel,
    QTableWidgetItem, QHeaderView, QDoubleSpinBox, QSpinBox,
    QComboBox, QTextEdit, QDialog, QFormLayout,
    QDialogButtonBox
)
from qfluentwidgets import (
    TableWidget, PushButton, ComboBox, SubtitleLabel, CaptionLabel, setFont
)
from config_manager import AppConfig
import REG1K0100A2 as reg


# ─── 命令定义表 ───────────────────────────────────────────────
COMMANDS = [
    {'cmd': 0x01, 'type': 'R', 'desc': '系统电压电流（浮点）',       'params': []},
    {'cmd': 0x02, 'type': 'R', 'desc': '系统模块数量',               'params': []},
    {'cmd': 0x03, 'type': 'R', 'desc': '模块N电压电流（浮点）',       'params': []},
    {'cmd': 0x04, 'type': 'R', 'desc': '模块N状态',                  'params': []},
    {'cmd': 0x06, 'type': 'R', 'desc': '模块N三相输入电压',           'params': []},
    {'cmd': 0x08, 'type': 'R', 'desc': '系统电压电流（定点）',        'params': []},
    {'cmd': 0x09, 'type': 'R', 'desc': '模块N电压电流（定点）',       'params': []},
    {'cmd': 0x0A, 'type': 'R', 'desc': '模块参数（电压/电流/功率）',  'params': []},
    {'cmd': 0x0B, 'type': 'R', 'desc': '模块条码',                   'params': []},
    {'cmd': 0x0C, 'type': 'R', 'desc': '外部电压/允许电流',           'params': []},
    {'cmd': 0x0F, 'type': 'W', 'desc': '综合设置',                   'params': [], 'special': 'dialog'},
    {'cmd': 0x13, 'type': 'W', 'desc': 'Walk-In 使能',
     'params': [{'type': 'combo', 'options': ['使能', '禁止'], 'key': 'enable'}]},
    {'cmd': 0x14, 'type': 'W', 'desc': '绿灯闪烁',
     'params': [{'type': 'combo', 'options': ['闪烁', '正常'], 'key': 'blink'}]},
    {'cmd': 0x16, 'type': 'W', 'desc': '设置组号',
     'params': [{'type': 'spin', 'min': 1, 'max': 255, 'default': 1, 'key': 'group'}]},
    {'cmd': 0x19, 'type': 'W', 'desc': '模块休眠',
     'params': [{'type': 'combo', 'options': ['休眠', '不休眠'], 'key': 'sleep'}]},
    {'cmd': 0x1A, 'type': 'W', 'desc': '开关机',
     'params': [{'type': 'combo', 'options': ['开机', '关机'], 'key': 'power'}]},
    {'cmd': 0x1B, 'type': 'W', 'desc': '设置系统输出电压/总电流',
     'params': [
         {'type': 'double', 'label': 'V', 'key': 'volt', 'min': 150.0, 'max': 1000.0, 'default': 320.0},
         {'type': 'double', 'label': 'A', 'key': 'curr', 'min': 0.0,   'max': 6000.0, 'default': 10.0},
     ], 'addr_lock': 0x3F},
    {'cmd': 0x1C, 'type': 'W', 'desc': '设置模块电压/电流',
     'params': [
         {'type': 'double', 'label': 'V', 'key': 'volt', 'min': 150.0, 'max': 1000.0, 'default': 320.0},
         {'type': 'double', 'label': 'A', 'key': 'curr', 'min': 0.0,   'max': 100.0,  'default': 10.0},
     ]},
    {'cmd': 0x1F, 'type': 'W', 'desc': '地址分配方式',
     'params': [{'type': 'combo', 'options': ['自动分配', '拨码方式'], 'key': 'mode'}],
     'addr_lock': 0x3F},
]

# cmd_code -> 格式化响应字符串的函数（接收 CANControllerInfo 实例）
RESPONSE_FORMATTERS = {
    0x01: lambda ci: f"{ci.SystemVolt:.2f} V  {ci.SystemCurr:.2f} A",
    0x02: lambda ci: f"模块数: {ci.ModuleCount}",
    0x03: lambda ci: f"{ci.ModuleVoltFloat:.2f} V  {ci.ModuleCurrFloat:.2f} A",
    0x04: lambda ci: f"温度: {ci.Temperature} ℃",
    0x06: lambda ci: f"AB:{ci.AC_AB_Volt:.1f}V  BC:{ci.AC_BC_Volt:.1f}V  CA:{ci.AC_CA_Volt:.1f}V",
    0x08: lambda ci: f"{ci.SystemVolt:.2f} V  {ci.SystemCurr:.2f} A",
    0x09: lambda ci: f"{ci.DC_Output_Volt:.2f} V  {ci.DC_Output_Curr:.2f} A",
    0x0A: lambda ci: f"最大:{ci.ParamVoltMax:.0f}V / {ci.ParamCurrMax:.1f}A  额定:{ci.ParamPower:.0f}W",
    0x0B: lambda ci: ci.Barcode if ci.Barcode else "—",
    0x0C: lambda ci: f"外部:{ci.ExternalVolt:.1f}V  允许:{ci.AllowedCurr:.1f}A",
}

# 地址选项（索引 → 地址值）
_ADDR_VALUES = list(range(16)) + [0x3F]


class ManualWidget(QFrame):

    OBJECT_NAME = 'ManualInterface'

    def __init__(self, can_device, canController_info, config: AppConfig = None, parent=None):
        super().__init__(parent=parent)
        self.setObjectName(self.OBJECT_NAME)
        self._can_device = can_device
        self._ci = canController_info
        self._config = config or AppConfig()
        self._row_widgets = {}      # cmd_code -> {key: widget}
        self._response_labels = {}  # cmd_code -> QLabel

        self._build_ui()
        reg.g_log_callback = self._append_log

        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._refresh_responses)
        self._refresh_timer.start(150)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        title = SubtitleLabel('手动操作', self)
        setFont(title, 20)
        layout.addWidget(title)

        layout.addWidget(self._build_toolbar())
        layout.addWidget(self._build_table(), stretch=1)
        layout.addWidget(self._build_log())

    def _build_toolbar(self) -> QWidget:
        bar = QWidget(self)
        h = QHBoxLayout(bar)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(10)

        h.addWidget(CaptionLabel('目标地址:', bar))
        self.addrCombo = ComboBox(bar)
        for i in range(16):
            self.addrCombo.addItem(f"0x{i:02X} — 模块 {i}")
        self.addrCombo.addItem("0x3F — 广播")
        self.addrCombo.setCurrentIndex(0)
        self.addrCombo.setFixedWidth(160)
        h.addWidget(self.addrCombo)

        h.addWidget(CaptionLabel('设备号:', bar))
        self.deviceCombo = ComboBox(bar)
        self.deviceCombo.addItem("0x0A — 单模块")
        self.deviceCombo.addItem("0x0B — 组")
        self.deviceCombo.setFixedWidth(140)
        h.addWidget(self.deviceCombo)

        h.addStretch()

        self.readAllBtn = PushButton('⬇ 读取全部', bar)
        self.readAllBtn.clicked.connect(self._read_all)
        h.addWidget(self.readAllBtn)

        return bar

    def _build_table(self) -> QWidget:
        self._table = TableWidget(self)
        self._table.setColumnCount(6)
        self._table.setHorizontalHeaderLabels(['CMD', '类型', '说明', '参数', '响应数据', '操作'])
        self._table.setRowCount(len(COMMANDS))
        self._table.verticalHeader().hide()
        self._table.setEditTriggers(TableWidget.NoEditTriggers)
        self._table.setBorderVisible(True)
        self._table.setBorderRadius(8)
        self._table.setWordWrap(False)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self._table.setColumnWidth(0, 64)
        self._table.setColumnWidth(1, 52)
        self._table.setColumnWidth(3, 220)
        self._table.setColumnWidth(5, 72)

        for i, cmd_def in enumerate(COMMANDS):
            cmd_code = cmd_def['cmd']
            self._row_widgets[cmd_code] = {}

            # 列0: CMD
            item = QTableWidgetItem(f"0x{cmd_code:02X}")
            item.setFont(QFont('Consolas', 10))
            item.setTextAlignment(Qt.AlignCenter)
            self._table.setItem(i, 0, item)

            # 列1: 类型标签
            type_lbl = QLabel('读' if cmd_def['type'] == 'R' else '设', self._table)
            type_lbl.setAlignment(Qt.AlignCenter)
            type_lbl.setFont(QFont('Microsoft YaHei', 9))
            if cmd_def['type'] == 'R':
                type_lbl.setStyleSheet(
                    'QLabel{background:#1a3a5c;color:#89dceb;border-radius:4px;padding:2px 6px}')
            else:
                type_lbl.setStyleSheet(
                    'QLabel{background:#3d1a1a;color:#f38ba8;border-radius:4px;padding:2px 6px}')
            self._table.setCellWidget(i, 1, type_lbl)

            # 列2: 说明
            desc_item = QTableWidgetItem(cmd_def['desc'])
            desc_item.setFont(QFont('Microsoft YaHei', 9))
            self._table.setItem(i, 2, desc_item)

            # 列3: 参数
            param_w = self._build_param_widget(cmd_def, cmd_code)
            self._table.setCellWidget(i, 3, param_w)

            # 列4: 响应数据
            resp_lbl = QLabel('—', self._table)
            resp_lbl.setAlignment(Qt.AlignCenter)
            resp_lbl.setFont(QFont('Consolas', 9))
            self._response_labels[cmd_code] = resp_lbl
            self._table.setCellWidget(i, 4, resp_lbl)

            # 列5: 操作按钮
            btn = self._build_action_button(cmd_def)
            btn.clicked.connect(lambda checked, c=cmd_code: self._send_command(c))
            self._table.setCellWidget(i, 5, btn)

            # 广播锁定行：高亮 CMD 列文字颜色
            if cmd_def.get('addr_lock') is not None:
                it = self._table.item(i, 0)
                if it:
                    it.setForeground(QColor('#fab387'))

        return self._table

    def _build_param_widget(self, cmd_def: dict, cmd_code: int) -> QWidget:
        container = QWidget()
        h = QHBoxLayout(container)
        h.setContentsMargins(4, 2, 4, 2)
        h.setSpacing(4)

        params = cmd_def.get('params', [])
        if not params:
            lbl = QLabel('—')
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet('color: #6c7086')
            h.addWidget(lbl)
            return container

        for p in params:
            if p['type'] == 'combo':
                w = ComboBox(container)
                for opt in p['options']:
                    w.addItem(opt)
                w.setFixedWidth(90)
                h.addWidget(w)
                self._row_widgets[cmd_code][p['key']] = w
            elif p['type'] == 'double':
                w = QDoubleSpinBox(container)
                w.setRange(p['min'], p['max'])
                w.setValue(p['default'])
                w.setDecimals(1)
                w.setFixedWidth(72)
                h.addWidget(w)
                h.addWidget(QLabel(p['label']))
                self._row_widgets[cmd_code][p['key']] = w
            elif p['type'] == 'spin':
                w = QSpinBox(container)
                w.setRange(p['min'], p['max'])
                w.setValue(p['default'])
                w.setFixedWidth(72)
                h.addWidget(w)
                self._row_widgets[cmd_code][p['key']] = w
            else:
                raise ValueError(
                    f"_build_param_widget: 未知参数类型 {p['type']!r}，cmd=0x{cmd_code:02X}")

        h.addStretch()
        return container

    def _build_action_button(self, cmd_def: dict) -> PushButton:
        if cmd_def.get('special') == 'dialog':
            btn = PushButton('配置...')
            btn.setStyleSheet(
                'PushButton{background:#2a1f3d;color:#cba6f7;border:1px solid #453a5a;border-radius:4px}')
        elif cmd_def['type'] == 'R':
            btn = PushButton('发送')
            btn.setStyleSheet(
                'PushButton{background:#1a3a5c;color:#89b4fa;border:1px solid #2a4a7c;border-radius:4px}')
        else:
            btn = PushButton('发送')
            btn.setStyleSheet(
                'PushButton{background:#3d1a1a;color:#f38ba8;border:1px solid #5a2020;border-radius:4px}')
        btn.setFixedSize(68, 28)
        return btn

    def _build_log(self) -> QWidget:
        frame = QFrame(self)
        frame.setFrameShape(QFrame.StyledPanel)
        v = QVBoxLayout(frame)
        v.setContentsMargins(8, 6, 8, 6)
        v.setSpacing(4)

        header = QWidget(frame)
        hh = QHBoxLayout(header)
        hh.setContentsMargins(0, 0, 0, 0)
        hh.addWidget(CaptionLabel('📋 CAN 报文日志', frame))
        hh.addStretch()
        clear_btn = PushButton('清空')
        clear_btn.setFixedSize(64, 24)
        clear_btn.clicked.connect(self._clear_log)
        hh.addWidget(clear_btn)
        v.addWidget(header)

        self._log_text = QTextEdit(frame)
        self._log_text.setReadOnly(True)
        self._log_text.setFixedHeight(100)
        self._log_text.setFont(QFont('Consolas', 9))
        self._log_text.setStyleSheet(
            'QTextEdit{background:#181825;color:#cdd6f4;border:1px solid #313244;border-radius:4px}')
        v.addWidget(self._log_text)

        return frame

    # ─── 占位方法（Task 7 & 8 实现）─────────────────────────
    def _get_target_addr(self, cmd_code: int) -> int:
        cmd_def = next((c for c in COMMANDS if c['cmd'] == cmd_code), None)
        if cmd_def and cmd_def.get('addr_lock') is not None:
            return cmd_def['addr_lock']
        idx = self.addrCombo.currentIndex()
        return _ADDR_VALUES[idx] if idx < len(_ADDR_VALUES) else 0x00

    def _send_command(self, cmd_code: int):
        if cmd_code == 0x0F:
            self._open_0F_dialog()
            return

        dst = self._get_target_addr(cmd_code)
        w = self._row_widgets.get(cmd_code, {})

        READ_DISPATCH = {
            0x01: lambda: reg.REGx_ReadSystemVoltCurrFloat(dst),
            0x02: lambda: reg.REGx_ReadModuleCount(dst),
            0x03: lambda: reg.REGx_ReadModuleVoltCurrFloat(dst),
            0x04: lambda: reg.REGx_ReadStateRequest(dst),
            0x06: lambda: reg.REGx_ReadInputRequest(dst),
            0x08: lambda: reg.REGx_ReadSystemVoltCurrFixed(dst),
            0x09: lambda: reg.REGx_ReadOutputRequest(dst),
            0x0A: lambda: reg.REGx_ReadModuleParams(dst),
            0x0B: lambda: reg.REGx_ReadBarcode(dst),
            0x0C: lambda: reg.REGx_ReadExternalVoltCurr(dst),
        }
        if cmd_code in READ_DISPATCH:
            READ_DISPATCH[cmd_code]()
            return

        if cmd_code == 0x13:
            reg.REGx_SetWalkIn(dst, w['enable'].currentIndex() == 0)
        elif cmd_code == 0x14:
            reg.REGx_SetGreenLED(dst, w['blink'].currentIndex() == 0)
        elif cmd_code == 0x16:
            reg.REGx_SetGroupNumber(dst, w['group'].value())
        elif cmd_code == 0x19:
            reg.REGx_SetSleep(dst, w['sleep'].currentIndex() == 0)
        elif cmd_code == 0x1A:
            if w['power'].currentIndex() == 0:
                reg.REGx_Launch(dst)
            else:
                reg.REGx_CloseOutput(dst)
        elif cmd_code == 0x1B:
            reg.REGx_SetSystemOutput(dst, w['volt'].value(), w['curr'].value())
        elif cmd_code == 0x1C:
            reg.REGx_SetOutput(dst, w['volt'].value(), w['curr'].value())
        elif cmd_code == 0x1F:
            reg.REGx_SetAddressMode(dst, w['mode'].currentIndex() == 1)

    def _read_all(self):
        read_cmds = [0x01, 0x02, 0x03, 0x04, 0x06, 0x08, 0x09, 0x0A, 0x0B, 0x0C]
        for i, cmd_code in enumerate(read_cmds):
            QTimer.singleShot(i * 50, lambda c=cmd_code: self._send_command(c))

    def _refresh_responses(self):
        for cmd_code, formatter in RESPONSE_FORMATTERS.items():
            lbl = self._response_labels.get(cmd_code)
            if lbl is None:
                continue
            try:
                text = formatter(self._ci)
                lbl.setText(text)
            except Exception:
                pass  # 格式化器异常不应中断刷新循环

    def _append_log(self, direction: str, identifier: int, data: bytes, desc: str):
        id_str = (f"{identifier >> 24 & 0xFF:02X} {identifier >> 16 & 0xFF:02X} "
                  f"{identifier >> 8 & 0xFF:02X} {identifier & 0xFF:02X}")
        data_str = ' '.join(f'{b:02X}' for b in data)
        if direction == 'TX':
            color = '#89b4fa'
            arrow = '⬆ TX'
        else:
            color = '#a6e3a1'
            arrow = '⬇ RX'
        line = (f'<span style="color:{color}">{arrow}</span> '
                f'<span style="color:#585b70">{id_str}</span>&nbsp;&nbsp;'
                f'<span style="color:#cdd6f4">{data_str}</span>')
        if desc:
            line += f'&nbsp;&nbsp;<span style="color:#6c7086">{desc}</span>'
        self._log_text.append(line)
        # 限制最多 200 行，避免内存无限增长
        doc = self._log_text.document()
        if doc.blockCount() > 200:
            cursor = self._log_text.textCursor()
            cursor.movePosition(QTextCursor.Start)
            cursor.select(QTextCursor.BlockUnderCursor)
            cursor.removeSelectedText()
            cursor.deleteChar()
        self._log_text.scrollToBottom()

    def _clear_log(self):
        self._log_text.clear()

    def _open_0F_dialog(self):
        dlg = QDialog(self)
        dlg.setWindowTitle('综合设置 (0x0F)')
        dlg.setMinimumWidth(360)

        form = QFormLayout(dlg)
        form.setLabelAlignment(Qt.AlignRight)
        form.setSpacing(12)
        form.setContentsMargins(20, 20, 20, 20)

        # 工作模式
        work_combo = ComboBox(dlg)
        for txt in ['DCDC', 'MPPT', '输入恒压']:
            work_combo.addItem(txt)
        form.addRow('工作模式:', work_combo)

        # 降噪模式
        noise_combo = ComboBox(dlg)
        for txt in ['功率优先', '降噪模式', '静音模式']:
            noise_combo.addItem(txt)
        form.addRow('降噪模式:', noise_combo)

        # 高低压模式
        volt_combo = ComboBox(dlg)
        for txt in ['低压模式', '高压模式', '自动切换']:
            volt_combo.addItem(txt)
        form.addRow('高低压模式:', volt_combo)

        # 液冷温度
        tin_spin = QSpinBox(dlg)
        tin_spin.setRange(-40, 125)
        tin_spin.setValue(25)
        form.addRow('进水口温度 (℃):', tin_spin)

        tout_spin = QSpinBox(dlg)
        tout_spin.setRange(-40, 125)
        tout_spin.setValue(30)
        form.addRow('出水口温度 (℃):', tout_spin)

        tamb_spin = QSpinBox(dlg)
        tamb_spin.setRange(-40, 125)
        tamb_spin.setValue(25)
        form.addRow('环温 (℃):', tamb_spin)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, dlg)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        form.addRow(buttons)

        if dlg.exec_() != QDialog.Accepted:
            return

        dst = self._get_target_addr(0x0F)
        _VALUES = (0xA0, 0xA1, 0xA2)

        try:
            reg.REGx_SetComprehensive(dst, 0x11, 0x11, _VALUES[work_combo.currentIndex()])
            reg.REGx_SetComprehensive(dst, 0x11, 0x13, _VALUES[noise_combo.currentIndex()])
            reg.REGx_SetComprehensive(dst, 0x11, 0x14, _VALUES[volt_combo.currentIndex()])
            reg.REGx_SetLiquidCoolTemp(dst, tin_spin.value(), tout_spin.value(), tamb_spin.value())
        except Exception as e:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(self, '发送失败', f'0x0F 命令发送失败：{e}')
