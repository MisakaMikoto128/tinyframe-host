# 配置文件 + 手动操作页 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 INFY_POWER 上位机新增启动配置文件（config.json）和手动操作页（19条CAN命令的可交互表格）。

**Architecture:** 新建 `config_manager.py`（只读配置加载）和 `manual_widget.py`（手动操作页），扩展 `REG1K0100A2.py` 补全缺失的13个命令函数和响应解析，`main.py` 做最小集成。数据流完全复用现有100ms定时器 + `CANControllerInfo` 共享对象机制，不引入额外线程。

**Tech Stack:** Python 3.8+, PyQt5, qfluentwidgets, CAN 2.0B (ControlCAN.dll)

---

## 文件变更总览

| 文件 | 操作 | 说明 |
|------|------|------|
| `config.json` | 新建 | 启动配置（首次运行自动生成） |
| `config_manager.py` | 新建 | AppConfig dataclass + ConfigManager |
| `tests/test_config_manager.py` | 新建 | config_manager 单元测试 |
| `REG1K0100A2.py` | 修改 | 新增字段、日志钩子、13个命令函数、响应解析 |
| `manual_widget.py` | 新建 | ManualWidget 完整实现（~380行） |
| `main.py` | 修改 | 加载config、集成ManualWidget导航 |

---

## Task 1: 创建 config_manager.py

**Files:**
- Create: `config_manager.py`
- Create: `tests/test_config_manager.py`

- [ ] **Step 1: 创建 tests 目录**

```bash
mkdir tests
```

- [ ] **Step 2: 写失败测试**

新建 `tests/test_config_manager.py`：

```python
import json
import os
import sys
import tempfile
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def test_load_creates_default_file_when_missing(tmp_path):
    from config_manager import ConfigManager, AppConfig
    cfg_path = tmp_path / "config.json"
    mgr = ConfigManager(config_path=str(cfg_path))
    result = mgr.load()

    assert isinstance(result, AppConfig)
    assert result.device_name == "REG1K0100A2 充电模块"
    assert result.voltage_max == 1000.0
    assert result.voltage_min == 150.0
    assert result.current_max == 100.0
    assert result.current_min == 0.0
    assert cfg_path.exists()


def test_load_reads_existing_file(tmp_path):
    from config_manager import ConfigManager, AppConfig
    cfg_path = tmp_path / "config.json"
    data = {
        "device_name": "测试电源",
        "voltage_max": 750.0,
        "voltage_min": 100.0,
        "current_max": 50.0,
        "current_min": 0.0,
    }
    cfg_path.write_text(json.dumps(data), encoding='utf-8')
    mgr = ConfigManager(config_path=str(cfg_path))
    result = mgr.load()

    assert result.device_name == "测试电源"
    assert result.voltage_max == 750.0
    assert result.current_max == 50.0


def test_load_returns_defaults_on_corrupt_file(tmp_path):
    from config_manager import ConfigManager, AppConfig
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text("not valid json", encoding='utf-8')
    mgr = ConfigManager(config_path=str(cfg_path))
    result = mgr.load()

    assert result.device_name == "REG1K0100A2 充电模块"
```

- [ ] **Step 3: 运行测试确认失败**

```bash
cd C:\Users\liuyu\Desktop\WorkPlace\INFY_POWER
python -m pytest tests/test_config_manager.py -v
```

预期: `ModuleNotFoundError: No module named 'config_manager'`

- [ ] **Step 4: 创建 config_manager.py**

```python
import json
import os
from dataclasses import dataclass, asdict


@dataclass
class AppConfig:
    device_name: str = "REG1K0100A2 充电模块"
    voltage_max: float = 1000.0
    voltage_min: float = 150.0
    current_max: float = 100.0
    current_min: float = 0.0


class ConfigManager:
    def __init__(self, config_path: str = "config.json"):
        self._path = config_path

    def load(self) -> AppConfig:
        if not os.path.exists(self._path):
            default = AppConfig()
            try:
                with open(self._path, 'w', encoding='utf-8') as f:
                    json.dump(asdict(default), f, ensure_ascii=False, indent=2)
            except OSError:
                pass
            return default
        try:
            with open(self._path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return AppConfig(
                device_name=data.get("device_name", AppConfig.device_name),
                voltage_max=float(data.get("voltage_max", AppConfig.voltage_max)),
                voltage_min=float(data.get("voltage_min", AppConfig.voltage_min)),
                current_max=float(data.get("current_max", AppConfig.current_max)),
                current_min=float(data.get("current_min", AppConfig.current_min)),
            )
        except Exception:
            return AppConfig()
```

- [ ] **Step 5: 运行测试确认通过**

```bash
python -m pytest tests/test_config_manager.py -v
```

预期: `3 passed`

- [ ] **Step 6: 提交**

```bash
git add config_manager.py tests/test_config_manager.py
git commit -m "feat: 添加 ConfigManager 启动配置加载"
```

---

## Task 2: 将 config 集成进 main.py

**Files:**
- Modify: `main.py`

- [ ] **Step 1: 在 main.py 顶部添加 import**

在 `main.py` 第1行的 `import sys` 之后添加：

```python
from config_manager import ConfigManager, AppConfig
```

- [ ] **Step 2: 修改 MainWindow.__init__ 接受 config 参数**

将 `main.py:26` 的：

```python
class MainWindow(QFrame, Ui_Form):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        # loadUi('FluentQtTest.ui', self)  # Load the UI file
        self.setupUi(self)

        setThemeColor('#28afe9')
```

替换为：

```python
class MainWindow(QFrame, Ui_Form):
    def __init__(self, config: AppConfig = None, parent=None):
        super().__init__(parent=parent)

        self.setupUi(self)
        self._config = config or AppConfig()

        setThemeColor('#28afe9')
```

- [ ] **Step 3: 在 MainWindow.__init__ 中用 config 设置 SpinBox 范围**

找到 `main.py` 中：

```python
        self.DoubleSpinBox_Volt.setValue(320)
        self.DoubleSpinBox_Curr.setValue(10)
```

替换为：

```python
        self.DoubleSpinBox_Volt.setRange(self._config.voltage_min, self._config.voltage_max)
        self.DoubleSpinBox_Volt.setValue(min(320, self._config.voltage_max))
        self.DoubleSpinBox_Curr.setRange(self._config.current_min, self._config.current_max)
        self.DoubleSpinBox_Curr.setValue(min(10, self._config.current_max))
```

- [ ] **Step 4: 在 Window.__init__ 中加载 config 并传给 MainWindow**

将 `main.py` 中 `Window.__init__` 的：

```python
    def __init__(self):
        super().__init__()

        # create sub interface
        self.homeInterface = MainWindow(self)
```

替换为：

```python
    def __init__(self):
        super().__init__()

        self._config = ConfigManager().load()

        # create sub interface
        self.homeInterface = MainWindow(config=self._config, parent=self)
```

- [ ] **Step 5: 在 initWindow 中用 config 设置窗口标题**

将 `main.py` 的 `initWindow` 中：

```python
        self.setWindowTitle('REG1K0100A2 充电模块上位机')
```

替换为：

```python
        self.setWindowTitle(self._config.device_name)
```

- [ ] **Step 6: 验证**

运行 `python main.py`，确认：
- 窗口标题显示 config.json 中的 `device_name`（首次运行自动生成 config.json）
- 主页面电压 SpinBox 范围与 config 一致

- [ ] **Step 7: 提交**

```bash
git add main.py
git commit -m "feat: 从 config.json 加载设备名称和电压电流范围"
```

---

## Task 3: 扩展 REG1K0100A2.py — 新增字段与日志钩子

**Files:**
- Modify: `REG1K0100A2.py`

- [ ] **Step 1: 在文件顶部添加 import struct**

在 `REG1K0100A2.py` 第1行 `import HDL_CAN` 之前插入：

```python
import struct
```

- [ ] **Step 2: 在 CANControllerInfo 类末尾添加新字段**

找到 `REG1K0100A2.py:41` 的 `Temperature = 0`，在其后添加：

```python
    Temperature = 0

    # 0x01 / 0x08 系统电压电流
    SystemVolt = 0.0
    SystemCurr = 0.0
    # 0x02 模块数量
    ModuleCount = 0
    # 0x03 模块电压电流（浮点）
    ModuleVoltFloat = 0.0
    ModuleCurrFloat = 0.0
    # 0x0A 模块参数
    ParamVoltMax = 0.0
    ParamVoltMin = 0.0
    ParamCurrMax = 0.0
    ParamPower = 0.0
    # 0x0B 条码
    Barcode = ""
    # 0x0C 外部电压/允许电流
    ExternalVolt = 0.0
    AllowedCurr = 0.0
```

- [ ] **Step 3: 在 g_candevice 全局变量旁添加日志回调全局变量**

找到 `REG1K0100A2.py:44` 的 `g_candevice = None`，在其后插入：

```python
g_candevice = None
g_log_callback = None  # 由 ManualWidget 注册，签名: (direction: str, identifier: int, data: bytes, desc: str)
```

- [ ] **Step 4: 在 REGx_MsgSend 末尾触发日志回调**

找到 `REGx_MsgSend` 函数中的 `return g_candevice.send_data_ch1(Identifier, TxData)`，在 `return` 之前插入：

```python
    if g_log_callback:
        g_log_callback('TX', Identifier, bytes(TxData), "")
    return g_candevice.send_data_ch1(Identifier, TxData)
```

- [ ] **Step 5: 在 REGx_CAN_ReceviceCallback 末尾（解析完成后）触发日志回调**

在 `REGx_CAN_ReceviceCallback` 函数的 `if (response.dstAddr == ...):` 判断块之前插入：

```python
    if g_log_callback:
        g_log_callback('RX', Identifier, bytes(RxData), "")
```

- [ ] **Step 6: 提交**

```bash
git add REG1K0100A2.py
git commit -m "feat: 扩展 CANControllerInfo 新增字段，添加 CAN 日志回调钩子"
```

---

## Task 4: 扩展 REG1K0100A2.py — 新增读命令函数与响应解析

**Files:**
- Modify: `REG1K0100A2.py`

- [ ] **Step 1: 在 REGx_ReadOutputSetRequest 函数之后添加7个新读命令函数**

在 `REG1K0100A2.py` 中 `REGx_ReadOutputSetRequest` 函数结束后，添加以下内容：

```python
def REGx_ReadSystemVoltCurrFloat(dstAddr):
    request = REGx_Msg_t()
    request.errorCode = REGx_ERROR_CODE.NORMAL
    request.deviceCode = REGx_DEVICE_CODE.SINGLE
    request.cmdCode = 0x01
    request.dstAddr = dstAddr
    request.srcAddr = REGx_MASTER_ADDR
    request.data = bytearray(8)
    REGx_MsgSend(request)
    return 0


def REGx_ReadModuleCount(dstAddr):
    request = REGx_Msg_t()
    request.errorCode = REGx_ERROR_CODE.NORMAL
    request.deviceCode = REGx_DEVICE_CODE.SINGLE
    request.cmdCode = 0x02
    request.dstAddr = dstAddr
    request.srcAddr = REGx_MASTER_ADDR
    request.data = bytearray(8)
    REGx_MsgSend(request)
    return 0


def REGx_ReadModuleVoltCurrFloat(dstAddr):
    request = REGx_Msg_t()
    request.errorCode = REGx_ERROR_CODE.NORMAL
    request.deviceCode = REGx_DEVICE_CODE.SINGLE
    request.cmdCode = 0x03
    request.dstAddr = dstAddr
    request.srcAddr = REGx_MASTER_ADDR
    request.data = bytearray(8)
    REGx_MsgSend(request)
    return 0


def REGx_ReadSystemVoltCurrFixed(dstAddr):
    request = REGx_Msg_t()
    request.errorCode = REGx_ERROR_CODE.NORMAL
    request.deviceCode = REGx_DEVICE_CODE.SINGLE
    request.cmdCode = 0x08
    request.dstAddr = dstAddr
    request.srcAddr = REGx_MASTER_ADDR
    request.data = bytearray(8)
    REGx_MsgSend(request)
    return 0


def REGx_ReadModuleParams(dstAddr):
    request = REGx_Msg_t()
    request.errorCode = REGx_ERROR_CODE.NORMAL
    request.deviceCode = REGx_DEVICE_CODE.SINGLE
    request.cmdCode = 0x0A
    request.dstAddr = dstAddr
    request.srcAddr = REGx_MASTER_ADDR
    request.data = bytearray(8)
    REGx_MsgSend(request)
    return 0


def REGx_ReadBarcode(dstAddr):
    request = REGx_Msg_t()
    request.errorCode = REGx_ERROR_CODE.NORMAL
    request.deviceCode = REGx_DEVICE_CODE.SINGLE
    request.cmdCode = 0x0B
    request.dstAddr = dstAddr
    request.srcAddr = REGx_MASTER_ADDR
    request.data = bytearray(8)
    REGx_MsgSend(request)
    return 0


def REGx_ReadExternalVoltCurr(dstAddr):
    request = REGx_Msg_t()
    request.errorCode = REGx_ERROR_CODE.NORMAL
    request.deviceCode = REGx_DEVICE_CODE.SINGLE
    request.cmdCode = 0x0C
    request.dstAddr = dstAddr
    request.srcAddr = REGx_MASTER_ADDR
    request.data = bytearray(8)
    REGx_MsgSend(request)
    return 0
```

- [ ] **Step 2: 在 REGx_CAN_ReceviceCallback 的 else: pass 之前，补全新响应解析分支**

找到 `REGx_CAN_ReceviceCallback` 函数中的：

```python
        else:
            pass
```

替换为：

```python
        elif response.cmdCode == 0x01:
            canController_info.SystemVolt = struct.unpack('>f', bytes(response.data[0:4]))[0]
            canController_info.SystemCurr = struct.unpack('>f', bytes(response.data[4:8]))[0]
        elif response.cmdCode == 0x02:
            canController_info.ModuleCount = response.data[2]
        elif response.cmdCode == 0x03:
            canController_info.ModuleVoltFloat = struct.unpack('>f', bytes(response.data[0:4]))[0]
            canController_info.ModuleCurrFloat = struct.unpack('>f', bytes(response.data[4:8]))[0]
        elif response.cmdCode == 0x08:
            canController_info.SystemVolt = ((response.data[0] << 24) | (response.data[1] << 16) |
                                             (response.data[2] << 8) | response.data[3]) / 1000.0
            canController_info.SystemCurr = ((response.data[4] << 24) | (response.data[5] << 16) |
                                             (response.data[6] << 8) | response.data[7]) / 1000.0
        elif response.cmdCode == 0x0A:
            canController_info.ParamVoltMax = float((response.data[0] << 8) | response.data[1])
            canController_info.ParamVoltMin = float((response.data[2] << 8) | response.data[3])
            canController_info.ParamCurrMax = ((response.data[4] << 8) | response.data[5]) * 0.1
            canController_info.ParamPower = ((response.data[6] << 8) | response.data[7]) * 10.0
        elif response.cmdCode == 0x0B:
            canController_info.Barcode = ' '.join(f'{b:02X}' for b in response.data)
        elif response.cmdCode == 0x0C:
            canController_info.ExternalVolt = ((response.data[0] << 8) | response.data[1]) * 0.1
            canController_info.AllowedCurr = ((response.data[2] << 8) | response.data[3]) * 0.1
        else:
            pass
```

- [ ] **Step 3: 提交**

```bash
git add REG1K0100A2.py
git commit -m "feat: 添加 7 个读命令函数及对应响应解析（0x01/02/03/08/0A/0B/0C）"
```

---

## Task 5: 扩展 REG1K0100A2.py — 新增设命令函数

**Files:**
- Modify: `REG1K0100A2.py`

- [ ] **Step 1: 在 REGx_CloseOutput 函数之后添加7个新设命令函数**

在 `REG1K0100A2.py` 的 `REGx_CloseOutput` 函数结束后，添加：

```python
def REGx_SetComprehensive(dstAddr, sub_cmd_hi: int, sub_cmd_lo: int, value: int):
    request = REGx_Msg_t()
    request.errorCode = REGx_ERROR_CODE.NORMAL
    request.deviceCode = REGx_DEVICE_CODE.SINGLE
    request.cmdCode = 0x0F
    request.dstAddr = dstAddr
    request.srcAddr = REGx_MASTER_ADDR
    request.data = bytearray(8)
    request.data[0] = sub_cmd_hi & 0xFF
    request.data[1] = sub_cmd_lo & 0xFF
    request.data[7] = value & 0xFF
    REGx_MsgSend(request)
    return 0


def REGx_SetWalkIn(dstAddr, enable: bool):
    request = REGx_Msg_t()
    request.errorCode = REGx_ERROR_CODE.NORMAL
    request.deviceCode = REGx_DEVICE_CODE.SINGLE
    request.cmdCode = 0x13
    request.dstAddr = dstAddr
    request.srcAddr = REGx_MASTER_ADDR
    request.data = bytearray(8)
    request.data[0] = 0x01 if enable else 0x00
    REGx_MsgSend(request)
    return 0


def REGx_SetGreenLED(dstAddr, blink: bool):
    request = REGx_Msg_t()
    request.errorCode = REGx_ERROR_CODE.NORMAL
    request.deviceCode = REGx_DEVICE_CODE.SINGLE
    request.cmdCode = 0x14
    request.dstAddr = dstAddr
    request.srcAddr = REGx_MASTER_ADDR
    request.data = bytearray(8)
    request.data[0] = 0x01 if blink else 0x00
    REGx_MsgSend(request)
    return 0


def REGx_SetGroupNumber(dstAddr, group: int):
    request = REGx_Msg_t()
    request.errorCode = REGx_ERROR_CODE.NORMAL
    request.deviceCode = REGx_DEVICE_CODE.SINGLE
    request.cmdCode = 0x16
    request.dstAddr = dstAddr
    request.srcAddr = REGx_MASTER_ADDR
    request.data = bytearray(8)
    request.data[0] = group & 0xFF
    REGx_MsgSend(request)
    return 0


def REGx_SetSleep(dstAddr, sleep: bool):
    request = REGx_Msg_t()
    request.errorCode = REGx_ERROR_CODE.NORMAL
    request.deviceCode = REGx_DEVICE_CODE.SINGLE
    request.cmdCode = 0x19
    request.dstAddr = dstAddr
    request.srcAddr = REGx_MASTER_ADDR
    request.data = bytearray(8)
    request.data[0] = 0x01 if sleep else 0x00
    REGx_MsgSend(request)
    return 0


def REGx_SetSystemOutput(dstAddr, volt: float, total_curr: float):
    volt = max(REGx_OUTPUT_DC_VOLT_MIN, min(volt, REGx_OUTPUT_DC_VOLT_MAX))
    total_curr = max(0.0, total_curr)
    request = REGx_Msg_t()
    request.errorCode = REGx_ERROR_CODE.NORMAL
    request.deviceCode = REGx_DEVICE_CODE.SINGLE
    request.cmdCode = 0x1B
    request.dstAddr = dstAddr
    request.srcAddr = REGx_MASTER_ADDR
    voltSetValue = int(volt * 1000)
    currSetValue = int(total_curr * 1000)
    request.data[0] = (voltSetValue >> 24) & 0xFF
    request.data[1] = (voltSetValue >> 16) & 0xFF
    request.data[2] = (voltSetValue >> 8) & 0xFF
    request.data[3] = voltSetValue & 0xFF
    request.data[4] = (currSetValue >> 24) & 0xFF
    request.data[5] = (currSetValue >> 16) & 0xFF
    request.data[6] = (currSetValue >> 8) & 0xFF
    request.data[7] = currSetValue & 0xFF
    REGx_MsgSend(request)
    return 0


def REGx_SetAddressMode(dstAddr, dip_switch: bool):
    request = REGx_Msg_t()
    request.errorCode = REGx_ERROR_CODE.NORMAL
    request.deviceCode = REGx_DEVICE_CODE.SINGLE
    request.cmdCode = 0x1F
    request.dstAddr = dstAddr
    request.srcAddr = REGx_MASTER_ADDR
    request.data = bytearray(8)
    request.data[0] = 0x01 if dip_switch else 0x00
    REGx_MsgSend(request)
    return 0
```

- [ ] **Step 2: 提交**

```bash
git add REG1K0100A2.py
git commit -m "feat: 添加 7 个设命令函数（0x0F/13/14/16/19/1B/1F）"
```

---

## Task 6: 创建 manual_widget.py — 命令定义、工具栏、表格骨架

**Files:**
- Create: `manual_widget.py`

- [ ] **Step 1: 创建 manual_widget.py，写入命令定义常量和类骨架**

新建 `manual_widget.py`：

```python
import time
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QWidget, QLabel,
    QTableWidgetItem, QHeaderView, QDoubleSpinBox, QSpinBox,
    QComboBox, QTextEdit, QSizePolicy, QDialog, QFormLayout,
    QDialogButtonBox
)
from qfluentwidgets import (
    TableWidget, PushButton, ToolButton, ComboBox, DoubleSpinBox,
    SpinBox, SubtitleLabel, CaptionLabel, setFont, FluentIcon as FIF,
    isDarkTheme, ScrollArea
)
from config_manager import AppConfig
import REG1K0100A2 as reg


# ─── 命令定义表 ───────────────────────────────────────────────
# type: 'R'=读, 'W'=设
# params: 每项 {'type': 'combo'|'double'|'spin', ...}
# addr_lock: 非 None 时该命令强制使用此目标地址
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

# cmd_code -> 格式化响应字符串的函数，接收 CANControllerInfo 实例
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
        self._row_widgets = {}    # cmd_code -> {key: widget}
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
```

- [ ] **Step 2: 继续写 _build_toolbar 方法（接在同一文件）**

```python
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

        self.readAllBtn = PushButton('⬇ 读取全部', bar, FIF.DOWNLOAD)
        self.readAllBtn.clicked.connect(self._read_all)
        h.addWidget(self.readAllBtn)

        return bar
```

- [ ] **Step 3: 继续写 _build_table 方法**

```python
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
            self._row_index[cmd_code] = i
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

            # 锁定广播地址行的视觉提示
            if cmd_def.get('addr_lock') is not None:
                for col in [0, 2]:
                    it = self._table.item(i, col)
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

        h.addStretch()
        return container

    def _build_action_button(self, cmd_def: dict) -> PushButton:
        if cmd_def.get('special') == 'dialog':
            btn = PushButton('配置...', icon=FIF.SETTING)
            btn.setStyleSheet(
                'PushButton{background:#2a1f3d;color:#cba6f7;border:1px solid #453a5a;border-radius:4px}')
        elif cmd_def['type'] == 'R':
            btn = PushButton('发送', icon=FIF.SEND)
            btn.setStyleSheet(
                'PushButton{background:#1a3a5c;color:#89b4fa;border:1px solid #2a4a7c;border-radius:4px}')
        else:
            btn = PushButton('发送', icon=FIF.SEND)
            btn.setStyleSheet(
                'PushButton{background:#3d1a1a;color:#f38ba8;border:1px solid #5a2020;border-radius:4px}')
        btn.setFixedSize(68, 28)
        return btn
```

- [ ] **Step 4: 继续写 _build_log 方法**

```python
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
        clear_btn = PushButton('清空', icon=FIF.DELETE)
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
```

- [ ] **Step 5: 验证文件语法无误**

```bash
cd C:\Users\liuyu\Desktop\WorkPlace\INFY_POWER
python -c "import manual_widget; print('OK')"
```

预期输出: `OK`（无报错）

- [ ] **Step 6: 提交**

```bash
git add manual_widget.py
git commit -m "feat: manual_widget.py 骨架 — 命令定义表、工具栏、表格、日志面板"
```

---

## Task 7: manual_widget.py — 命令发送、读取全部、响应刷新

**Files:**
- Modify: `manual_widget.py`

- [ ] **Step 1: 在 ManualWidget 类末尾添加 _get_target_addr 方法**

```python
    def _get_target_addr(self, cmd_code: int) -> int:
        cmd_def = next((c for c in COMMANDS if c['cmd'] == cmd_code), None)
        if cmd_def and cmd_def.get('addr_lock') is not None:
            return cmd_def['addr_lock']
        idx = self.addrCombo.currentIndex()
        return _ADDR_VALUES[idx] if idx < len(_ADDR_VALUES) else 0x00
```

- [ ] **Step 2: 添加 _send_command 方法**

```python
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
```

- [ ] **Step 3: 添加 _read_all 方法**

```python
    def _read_all(self):
        dst = self._get_target_addr(0x01)  # 使用全局地址（读全部时无广播锁命令）
        read_cmds = [0x01, 0x02, 0x03, 0x04, 0x06, 0x08, 0x09, 0x0A, 0x0B, 0x0C]
        for cmd_code in read_cmds:
            self._send_command(cmd_code)
            time.sleep(0.05)  # 50ms 间隔，避免总线拥塞
```

- [ ] **Step 4: 添加 _refresh_responses 方法**

```python
    def _refresh_responses(self):
        for cmd_code, formatter in RESPONSE_FORMATTERS.items():
            lbl = self._response_labels.get(cmd_code)
            if lbl is None:
                continue
            try:
                text = formatter(self._ci)
                lbl.setText(text)
            except Exception:
                pass
```

- [ ] **Step 5: 添加 _append_log 与 _clear_log 方法**

```python
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
            from PyQt5.QtGui import QTextCursor
            cursor = self._log_text.textCursor()
            cursor.movePosition(QTextCursor.Start)
            cursor.select(QTextCursor.BlockUnderCursor)
            cursor.removeSelectedText()
            cursor.deleteChar()
        self._log_text.scrollToBottom()

    def _clear_log(self):
        self._log_text.clear()
```

- [ ] **Step 6: 验证语法**

```bash
python -c "import manual_widget; print('OK')"
```

预期: `OK`

- [ ] **Step 7: 提交**

```bash
git add manual_widget.py
git commit -m "feat: manual_widget — 命令发送、读取全部、响应刷新、日志追加"
```

---

## Task 8: manual_widget.py — 0x0F 综合设置弹窗

**Files:**
- Modify: `manual_widget.py`

- [ ] **Step 1: 在 ManualWidget 类末尾添加 _open_0F_dialog 方法**

```python
    def _open_0F_dialog(self):
        dlg = QDialog(self)
        dlg.setWindowTitle('综合设置 (0x0F)')
        dlg.setMinimumWidth(360)

        form = QFormLayout(dlg)
        form.setLabelAlignment(Qt.AlignRight)
        form.setSpacing(12)
        form.setContentsMargins(20, 20, 20, 20)

        # 工作模式
        work_combo = QComboBox(dlg)
        for txt in ['DCDC', 'MPPT', '输入恒压']:
            work_combo.addItem(txt)
        form.addRow('工作模式:', work_combo)

        # 降噪模式
        noise_combo = QComboBox(dlg)
        for txt in ['功率优先', '降噪模式', '静音模式']:
            noise_combo.addItem(txt)
        form.addRow('降噪模式:', noise_combo)

        # 高低压模式
        volt_combo = QComboBox(dlg)
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

        # 工作模式: sub_cmd 0x11 0x11, value 0xA0/A1/A2
        work_values = [0xA0, 0xA1, 0xA2]
        reg.REGx_SetComprehensive(dst, 0x11, 0x11, work_values[work_combo.currentIndex()])
        time.sleep(0.05)

        # 降噪模式: sub_cmd 0x11 0x13, value 0xA0/A1/A2
        noise_values = [0xA0, 0xA1, 0xA2]
        reg.REGx_SetComprehensive(dst, 0x11, 0x13, noise_values[noise_combo.currentIndex()])
        time.sleep(0.05)

        # 高低压模式: sub_cmd 0x11 0x14, value 0xA0/A1/A2
        volt_values = [0xA0, 0xA1, 0xA2]
        reg.REGx_SetComprehensive(dst, 0x11, 0x14, volt_values[volt_combo.currentIndex()])
        time.sleep(0.05)

        # 液冷温度: sub_cmd 0x13 0x01, data[5]=TIN, [6]=TOUT, [7]=TAMB
        # 复用 REGx_SetComprehensive 传不了3个温度值，直接构造报文
        req = reg.REGx_Msg_t()
        req.errorCode = reg.REGx_ERROR_CODE.NORMAL
        req.deviceCode = reg.REGx_DEVICE_CODE.SINGLE
        req.cmdCode = 0x0F
        req.dstAddr = dst
        req.srcAddr = reg.REGx_MASTER_ADDR
        req.data = bytearray(8)
        req.data[0] = 0x13
        req.data[1] = 0x01
        req.data[5] = tin_spin.value() & 0xFF
        req.data[6] = tout_spin.value() & 0xFF
        req.data[7] = tamb_spin.value() & 0xFF
        reg.REGx_MsgSend(req)
```

- [ ] **Step 2: 验证语法**

```bash
python -c "import manual_widget; print('OK')"
```

预期: `OK`

- [ ] **Step 3: 提交**

```bash
git add manual_widget.py
git commit -m "feat: manual_widget — 0x0F 综合设置弹窗（工作模式/降噪/高低压/液冷温度）"
```

---

## Task 9: main.py — 集成 ManualWidget 到导航栏

**Files:**
- Modify: `main.py`

- [ ] **Step 1: 在 main.py 顶部添加 ManualWidget 导入**

在 `from config_manager import ConfigManager, AppConfig` 之后添加：

```python
from manual_widget import ManualWidget
```

- [ ] **Step 2: 在 Window.__init__ 中创建 ManualWidget 实例**

将 `Window.__init__` 中：

```python
        self._config = ConfigManager().load()

        # create sub interface
        self.homeInterface = MainWindow(config=self._config, parent=self)
        self.settingInterface = SettingWidget('Setting Interface', self)
```

替换为：

```python
        self._config = ConfigManager().load()

        # create sub interface
        self.homeInterface = MainWindow(config=self._config, parent=self)
        self.manualInterface = ManualWidget(
            can_device=self.homeInterface.can_device,
            canController_info=self.homeInterface.canController_info,
            config=self._config,
            parent=self,
        )
        self.settingInterface = SettingWidget('Setting Interface', self)
```

- [ ] **Step 3: 在 initNavigation 中注册 ManualWidget**

在 `initNavigation` 方法中，找到：

```python
        self.addSubInterface(self.homeInterface, FIF.HOME, 'Home')

        # Theme切换按钮

        self.navigationInterface.addSeparator()
```

替换为：

```python
        self.addSubInterface(self.homeInterface, FIF.HOME, 'Home')
        self.addSubInterface(self.manualInterface, FIF.EDIT, '手动操作')

        self.navigationInterface.addSeparator()
```

- [ ] **Step 4: 运行应用验证功能**

```bash
python main.py
```

验证清单：
- [ ] 左侧导航出现"手动操作"菜单项
- [ ] 点击"手动操作"进入页面，显示19行命令表格
- [ ] 顶部地址选择器和设备号选择器正常显示
- [ ] 连接 CAN 设备后点击"读取全部"，底部日志出现 TX 报文
- [ ] 收到模块回复后响应数据列自动更新
- [ ] 设置命令行有对应参数输入框（下拉/数值）
- [ ] 点击 0x0F "配置..." 弹出综合设置对话框
- [ ] 启动时窗口标题为 config.json 中的 device_name
- [ ] 主页面电压 SpinBox 范围与 config.json 一致

- [ ] **Step 5: 提交**

```bash
git add main.py
git commit -m "feat: 将手动操作页集成到主导航栏"
```

---

## 完成标志

所有 Task 1–9 的步骤复选框全部勾选，且 Task 9 Step 4 的9条验证清单全部通过。
