# 设计规格：启动配置文件 + 手动操作页

**日期：** 2026-04-23  
**项目：** INFY_POWER 英飞源电源上位机  
**技术栈：** Python / PyQt5 / qfluentwidgets / CAN 通信

---

## 1. 背景与目标

### 1.1 功能一：启动配置文件

程序每次启动时从 `config.json` 读取电源参数，用于设置主页面控件的取值范围和窗口标题。配置文件只读加载，运行时修改不回写。

### 1.2 功能二：手动操作页

在左侧导航栏新增"手动操作"页面，展示协议 2.3 节全部 19 条 CAN 命令，每行对应一条命令，支持单独发送及"读取全部"批量读取，响应数据内联显示在表格行中，底部附 CAN 报文日志。

---

## 2. 架构方案

采用**方案 B：新建独立文件，最小侵入**。

新增文件：
- `config_manager.py` — 配置加载
- `manual_widget.py` — 手动操作页

修改文件：
- `REG1K0100A2.py` — 补全缺失的命令函数和解析逻辑
- `main.py` — 集成以上模块（最小改动）

不引入额外线程，复用现有 100ms 定时器 + `CANControllerInfo` 数据流。

---

## 3. 配置文件设计

### 3.1 config.json（与 main.py 同目录）

```json
{
  "device_name": "REG1K0100A2 充电模块",
  "voltage_max": 1000.0,
  "voltage_min": 150.0,
  "current_max": 100.0,
  "current_min": 0.0
}
```

文件不存在时自动创建并写入上述默认值。

### 3.2 config_manager.py

```python
@dataclass
class AppConfig:
    device_name: str = "REG1K0100A2 充电模块"
    voltage_max: float = 1000.0
    voltage_min: float = 150.0
    current_max: float = 100.0
    current_min: float = 0.0

class ConfigManager:
    CONFIG_PATH = "config.json"

    def load(self) -> AppConfig:
        # 若文件不存在，写入默认值并返回默认 AppConfig
        # 读取 JSON，字段映射到 AppConfig
        # 任何解析异常均返回默认 AppConfig（不崩溃）
```

### 3.3 main.py 集成点

1. `Window.__init__()` 最先调用 `ConfigManager().load()` 得到 `config`
2. 将 `config` 传入 `MainWindow(config=config)` 和 `ManualWidget(config=config, ...)`
3. `MainWindow.__init__()` 中：
   - `self.DoubleSpinBox_Volt.setRange(config.voltage_min, config.voltage_max)`
   - `self.DoubleSpinBox_Curr.setRange(config.current_min, config.current_max)`
4. `Window.initWindow()` 中：
   - `self.setWindowTitle(config.device_name)`

---

## 4. 手动操作页设计

### 4.1 导航集成

```python
# main.py — Window.initNavigation()
self.manualInterface = ManualWidget(
    can_device=self.homeInterface.can_device,
    canController_info=self.homeInterface.canController_info,
    parent=self
)
self.addSubInterface(self.manualInterface, FIF.COMMAND_PROMPT, '手动操作')
```

### 4.2 页面布局（3层垂直结构）

```
┌──────────────────────────────────────────────────────────┐
│  目标地址: [0x00 ▼]  设备号: [0x0A ▼]      [⬇ 读取全部]  │  ← 顶部工具栏
├──────────────────────────────────────────────────────────┤
│  CMD   类型  说明              参数输入    响应数据   操作  │
│  0x01  读    系统电压电流…     —          500V 15A  [发送] │
│  0x02  读    系统模块数量      —          模块数:3   [发送] │
│  ...（全部 19 条命令）                                     │
│  0x0F  设    综合设置          工作模式…  —          [配置…]│
│  0x1C  设    设置电压/电流     [320]V [10]A  320V 10A✓ [发送]│
├──────────────────────────────────────────────────────────┤
│  📋 CAN 报文日志                                  [清空]   │  ← 底部日志
│  ⬆ TX  02 84 00 F0  00 00 00 00 00 00 00 00  读取模块0状态│
│  ⬇ RX  02 84 F0 00  00 00 02 00 1B 00 40 00  组:2 温:27℃ │
└──────────────────────────────────────────────────────────┘
```

### 4.3 命令行配置表（全部 19 条）

| CMD  | 类型 | 说明 | 参数输入控件 | 地址限制 |
|------|------|------|------------|---------|
| 0x01 | 读 | 系统电压电流（浮点） | — | — |
| 0x02 | 读 | 系统模块数量 | — | — |
| 0x03 | 读 | 模块N电压电流（浮点） | — | — |
| 0x04 | 读 | 模块N状态 | — | — |
| 0x06 | 读 | 模块N三相输入电压 | — | — |
| 0x08 | 读 | 系统电压电流（定点） | — | — |
| 0x09 | 读 | 模块N电压电流（定点） | — | — |
| 0x0A | 读 | 模块参数（电压/电流/功率限值） | — | — |
| 0x0B | 读 | 模块条码 | — | — |
| 0x0C | 读 | 外部电压/允许电流 | — | — |
| 0x0F | 设 | 综合设置 | 弹窗（4个子功能） | — |
| 0x13 | 设 | Walk-In 使能 | 下拉：使能/禁止 | — |
| 0x14 | 设 | 绿灯闪烁 | 下拉：闪烁/正常 | — |
| 0x16 | 设 | 设置组号 | SpinBox (1–255) | — |
| 0x19 | 设 | 模块休眠 | 下拉：休眠/不休眠 | — |
| 0x1A | 设 | 开关机 | 下拉：开机/关机 | — |
| 0x1B | 设 | 设置系统输出电压/总电流 | DoubleSpinBox V + A | 广播自动锁 0x3F |
| 0x1C | 设 | 设置模块电压/电流 | DoubleSpinBox V + A | — |
| 0x1F | 设 | 地址分配方式 | 下拉：自动/拨码 | 广播自动锁 0x3F |

**广播自动锁**：0x1B、0x1F 在 device=0x0A 时协议要求 dstAddr=0x3F，地址选择器对这两行禁用。0x1A 支持点对点，跟随全局地址选择器。

### 4.4 按钮样式规则

- 读命令"发送"按钮：蓝色背景
- 设命令"发送"按钮：红色背景  
- 0x0F"配置..."按钮：紫色背景
- "读取全部"按钮：绿色背景（顶部工具栏）

### 4.5 0x0F 综合设置弹窗

使用 qfluentwidgets `MessageBox` 或自定义 `QDialog`，包含4个选项：

| 子功能 | 控件 | 选项 |
|--------|------|------|
| 工作模式 | ComboBox | DCDC / MPPT / 输入恒压 |
| 降噪模式 | ComboBox | 功率优先 / 降噪 / 静音 |
| 高低压模式 | ComboBox | 低压 / 高压 / 自动切换 |
| 液冷温度 | 3个 SpinBox | 进水口℃ / 出水口℃ / 环温℃ |

点击"发送"分别调用对应的 `REGx_SetComprehensive(sub_cmd, value)`。

### 4.6 ManualWidget 类结构

```python
class ManualWidget(QFrame):
    def __init__(self, can_device, canController_info, config, parent=None)
    def _build_toolbar(self) -> QWidget
    def _build_table(self) -> TableWidget
    def _build_log(self) -> QWidget
    def _send_command(self, cmd_code: int)
    def _read_all(self)
    def _refresh_responses(self)   # 150ms 定时器回调
    def _append_log(self, direction: str, identifier: int, data: bytes, desc: str)
    def _open_0F_dialog(self)
    def _get_target_addr(self, cmd_code: int) -> int  # 广播锁逻辑
```

### 4.7 响应数据刷新机制

- `ManualWidget` 持有 `canController_info` 的引用（与主窗口共享同一对象）
- 150ms 定时器调用 `_refresh_responses()`
- 该方法读取 `canController_info` 各字段，按 CMD 映射更新表格"响应数据"列
- CAN 报文日志通过在 `REGx_MsgSend` 和 `REGx_CAN_ReceviceCallback` 添加回调钩子更新

---

## 5. REG1K0100A2.py 扩展

### 5.1 CANControllerInfo 新增字段

```python
class CANControllerInfo:
    # 现有字段（保持不变）...

    # 新增
    SystemVolt: float = 0.0       # 0x01 / 0x08
    SystemCurr: float = 0.0
    ModuleCount: int = 0          # 0x02
    ModuleVoltFloat: float = 0.0  # 0x03
    ModuleCurrFloat: float = 0.0
    ParamVoltMax: float = 0.0     # 0x0A
    ParamVoltMin: float = 0.0
    ParamCurrMax: float = 0.0
    ParamPower: float = 0.0
    Barcode: str = ""             # 0x0B
    ExternalVolt: float = 0.0    # 0x0C
    AllowedCurr: float = 0.0
```

### 5.2 新增命令函数（读）

```
REGx_ReadSystemVoltCurrFloat(dstAddr)   # 0x01
REGx_ReadModuleCount(dstAddr)           # 0x02
REGx_ReadModuleVoltCurrFloat(dstAddr)   # 0x03
REGx_ReadSystemVoltCurrFixed(dstAddr)   # 0x08
REGx_ReadModuleParams(dstAddr)          # 0x0A
REGx_ReadBarcode(dstAddr)               # 0x0B
REGx_ReadExternalVoltCurr(dstAddr)      # 0x0C
```

### 5.3 新增命令函数（设）

```
REGx_SetComprehensive(dstAddr, sub_cmd_hi, sub_cmd_lo, value)  # 0x0F
REGx_SetWalkIn(dstAddr, enable: bool)                           # 0x13
REGx_SetGreenLED(dstAddr, blink: bool)                          # 0x14
REGx_SetGroupNumber(dstAddr, group: int)                        # 0x16
REGx_SetSleep(dstAddr, sleep: bool)                             # 0x19
REGx_SetSystemOutput(dstAddr, volt: float, total_curr: float)   # 0x1B
REGx_SetAddressMode(dstAddr, dip_switch: bool)                  # 0x1F
```

### 5.4 REGx_CAN_ReceviceCallback 补全

补全 0x01、0x02、0x03、0x08、0x0A、0x0B、0x0C 的回复解析，写入 `CANControllerInfo` 对应字段。

---

## 6. 日志回调机制

在 `manual_widget.py` 中定义全局回调引用：

```python
# REG1K0100A2.py 中
g_log_callback = None   # 由 ManualWidget 注册

def REGx_MsgSend(msg):
    ...
    if g_log_callback:
        g_log_callback('TX', Identifier, TxData, "")

def REGx_CAN_ReceviceCallback(can_msg, canController_info):
    ...
    if g_log_callback:
        g_log_callback('RX', Identifier, RxData, "")
```

`ManualWidget.__init__()` 中将 `self._append_log` 注册到 `g_log_callback`。

> **注意**：`g_log_callback` 为全局钩子，主页面的周期性轮询帧（0x04、0x06、0x09）也会出现在日志中。这是期望行为，用户可在手动操作页看到完整 CAN 总线流量。

---

## 7. 文件变更汇总

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `config.json` | 新建 | 启动配置文件 |
| `config_manager.py` | 新建 | 配置加载类 |
| `manual_widget.py` | 新建 | 手动操作页（~350行） |
| `REG1K0100A2.py` | 修改 | 补全13个命令函数 + 扩展 CANControllerInfo + 补全回调解析 + 添加日志钩子 |
| `main.py` | 修改 | 加载 config、集成 ManualWidget、更新窗口标题 |

---

## 8. 不在本次范围内

- 配置文件的 UI 编辑界面（本次只读加载）
- 多模块并联的批量轮询（手动页每次只查地址选择器指定的单个模块）
- 0x04 状态位的详细解码展示（仅显示原始解析字段）
