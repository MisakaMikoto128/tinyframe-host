# TinyFrame 上位机设计文档

**日期**：2026-04-24
**项目目录**：`C:\Users\liuyu\Desktop\WorkPlace\TinyFrameHost`
**对端下位机**：`C:\Users\liuyu\Desktop\WorkPlace\100kW\SEC_F28377D\sec_power`（TMS320F28377D + SCIB/RS485，TinyFrame SLAVE）

---

## 1. 背景与目标

原项目是 REG1K0100A2 充电模块的 CAN 总线上位机，基于 PyQt5 + qfluentwidgets。现在改造成一个 TinyFrame 串口上位机，用来跟 F28377D 下位机通信。

目标：
- 删除所有 CAN / BMS / REG1K0100A2 相关代码。
- 保留 FluentWindow 外壳与 `chart_widget.py` 实时曲线。
- 串口 I/O 走 `QSerialPort.readyRead` 事件驱动。
- TinyFrame 协议栈分两层：纯 Python 逻辑 + Qt 包装。
- 主界面两页：业务面板（读设定点 + 心跳 + 曲线）、协议调试（串口面板 + 帧发送器 + 收发日志）。

## 2. 协议契约（与下位机对齐的事实）

### 2.1 线上帧格式（经下位机修复后）

```
[SOF=0x1B] [ID_HI][ID_LO] [LEN_HI][LEN_LO] [TYPE] [DATA...] [CRC_LO][CRC_HI]
  1 字节    2 字节 (BE)    2 字节 (BE)      1 字节  LEN 字节  2 字节 (LE, CRC16 Modbus)
```

- 物理开销 8 字节；每个 "byte_t（DSP 侧 uint16_t）" 在线上等于 1 个物理字节（低 8 位）。
- CRC16 Modbus 覆盖 `SOF..DATA` 末尾。小端写入（先低字节后高字节）。
- SOF=0x1B，唯一固定值。

### 2.2 帧类型

| TYPE  | 名称             | 方向         | payload 布局                              |
| ----- | ---------------- | ------------ | ----------------------------------------- |
| 0x01  | REG_READ_REQ     | MASTER → SLAVE | `[addr(1B), count(1B)]`                  |
| 0x02  | REG_READ_RSP     | SLAVE → MASTER | `[addr(1B), count(1B), v_mV(4B BE), i_mA(4B BE)]`（10 字节） |
| 0x03  | HEARTBEAT        | MASTER → SLAVE | `[tick_ms(4B BE)]`                       |

**寄存器映射**：当前仅支持 `addr=0x10, count=4`（"读 4 个 16 位寄存器"的语义，物理响应为 10 字节）。返回的 `v_mV`、`i_mA` 是目标电压设定点（毫伏）与目标电流设定点（毫安），值域完整 0..0xFFFFFFFF。

### 2.3 ID 分配规则

- MASTER 发送帧 ID 从 0 开始，每次 `+2`，回绕到 0（保留 `>=0xFFFE` 范围）。
- SLAVE 响应帧回显请求 ID，用于主机端 ID 监听器配对。

### 2.4 超时

- 默认请求响应超时：200 ms（可在设置页调整默认值）。
- 超时由上位机 tick 机制驱动（10 ms 粒度）。

## 3. 架构

```
┌────────────────────────────────────────────────────────────┐
│  UI 层 (PyQt5 + qfluentwidgets)                             │
│  ┌─────────────────┐  ┌──────────────────────────────────┐  │
│  │ business_page   │  │ debug_page                       │  │
│  │  - 卡片+曲线    │  │  ├─ serial_panel                 │  │
│  │  - 轮询+心跳    │  │  ├─ frame_sender                 │  │
│  │                 │  │  └─ frame_log_view               │  │
│  └─────────────────┘  └──────────────────────────────────┘  │
│           │                          │                      │
│           └──────────┬───────────────┘                      │
├──────────────────────┼──────────────────────────────────────┤
│  TinyFrameEngine(QObject)            ← tinyframe/engine.py  │
│   - 持有 QSerialPort + QTimer(10ms)                         │
│   - Qt 信号：connected/disconnected/frameReceived/          │
│              frameSent/queryTimeout/rawBytesIn/rawBytesOut/ │
│              crcFailed                                      │
├─────────────────────────────────────────────────────────────┤
│  TinyFrame（纯 Python）               ← tinyframe/protocol.py│
│   - 状态机解析 / 构帧 / CRC / ID 监听 / 超时                │
│   - write_impl 回调、on_any_frame 回调                      │
└─────────────────────────────────────────────────────────────┘
```

**关键约束**：
1. `tinyframe/protocol.py` 零 Qt 依赖，纯标准库 + `crcmod`。
2. `TinyFrameEngine` 是唯一 Qt/串口胶水层。
3. 业务页、调试页都持有同一个 `TinyFrameEngine` 实例（`main.py` 注入）。
4. 串口开关只在调试页暴露；业务页在未连接时禁用发送按钮，并显示提示徽章。

## 4. 组件

### 4.1 `tinyframe/protocol.py`

纯 Python 协议栈。

```python
@dataclass
class TFFrame:
    type: int
    id: int
    data: bytes
    direction: str  # 'tx' / 'rx'

class TinyFrame:
    SOF = 0x1B

    def __init__(self, is_master: bool = True): ...

    # 输入：从串口读到的原始字节
    def accept(self, raw: bytes) -> None: ...

    # 单向发送
    def send(self, type_: int, data: bytes) -> None: ...

    # 请求+响应配对（带超时）。返回分配的 ID。
    def query(self, type_: int, data: bytes,
              on_response: Callable[[TFFrame], None],
              on_timeout: Callable[[int, int], None],
              timeout_ms: int = 200) -> int: ...

    # 超时驱动（engine 每 10 ms 调用）
    def tick(self, elapsed_ms: int) -> None: ...

    def on_type(self, type_: int, cb: Callable[[TFFrame], None]) -> None: ...
    def on_any_frame(self, cb: Callable[[TFFrame], None]) -> None: ...
    def on_crc_failed(self, cb: Callable[[TFFrame], None]) -> None: ...

    # 发送回调（engine 注入）
    write_impl: Callable[[bytes], None]
```

内部：
- 状态机：`IDLE → ID_HI → ID_LO → LEN_HI → LEN_LO → TYPE → DATA → CRC_LO → CRC_HI → IDLE`
- `LEN > TF_MAX_PAYLOAD_RX(64)` 时静默回到 IDLE
- CRC16 Modbus 使用 `crcmod.predefined.mkPredefinedCrcFun('modbus')`
- ID 分配器：MASTER 0/2/4/.../0xFFFE 回绕
- 超时表：`OrderedDict[id, (on_timeout_cb, remaining_ms, type_)]`，每次 `tick(ms)` 递减，≤0 时弹出并调用回调

### 4.2 `tinyframe/engine.py`

`TinyFrameEngine(QObject)`，包装 `TinyFrame` + `QSerialPort`。

```python
class TinyFrameEngine(QObject):
    connected = pyqtSignal(str)           # port_name
    disconnected = pyqtSignal(str)        # reason
    frameReceived = pyqtSignal(object)    # TFFrame
    frameSent = pyqtSignal(object)        # TFFrame
    queryTimeout = pyqtSignal(int, int)   # id, type
    rawBytesIn = pyqtSignal(bytes)
    rawBytesOut = pyqtSignal(bytes)
    crcFailed = pyqtSignal(object)        # TFFrame（尝试解出但 CRC 错）

    def open(self, port_name: str, baud: int = 115200,
             data_bits: int = 8, stop_bits: int = 1,
             parity: str = 'none') -> bool: ...
    def close(self) -> None: ...
    def is_open(self) -> bool: ...

    def query(self, type_: int, data: bytes,
              on_response, on_timeout, timeout_ms: int = 200) -> int: ...
    def send(self, type_: int, data: bytes) -> None: ...
    def send_heartbeat(self, tick_ms: int) -> None: ...

    @staticmethod
    def list_ports() -> list[str]: ...
```

内部：
- 构造时创建 `TinyFrame(is_master=True)`，`write_impl = lambda b: self._serial.write(b)` + `rawBytesOut.emit(b)`
- `QSerialPort.readyRead` → `self._tf.accept(self._serial.readAll().data())`，同时发 `rawBytesIn`
- `QSerialPort.errorOccurred` → 发 `disconnected`
- `QTimer(10ms)` 持续调 `self._tf.tick(10)`
- `TinyFrame.on_any_frame` 注册成 `self.frameReceived.emit(frame)`
- 未连接时 `send/query` 静默失败（不构帧，不阻塞）

### 4.3 `widgets/serial_panel.py`

调试页顶部串口连接条（固定高度，不在 splitter 里）。

元素：
- `ComboBox` 端口（+ `ToolButton(FIF.SYNC)` 刷新）
- `ComboBox` 波特率（9600/19200/38400/57600/115200/230400/460800，默认 115200）
- `SwitchButton` 打开/关闭
- `IconInfoBadge` 状态灯 + `CaptionLabel` 状态文字

构造签名：`SerialPanel(engine: TinyFrameEngine, parent=None)`

### 4.4 `widgets/frame_sender.py`

调试页中部手工帧发送器。

元素：
- `LineEdit` TYPE（16 进制）
- `LineEdit` payload HEX（支持空格分隔）
- `RadioButton` Send / Query
- `SpinBox` 超时 ms（Query 模式可编辑，50..10000）
- `PrimaryPushButton` 发送

容错：非法 HEX 输入弹 `InfoBar.error`，不发送。

### 4.5 `widgets/frame_log_view.py`

调试页底部收发日志。

- 工具条：`Pivot`（帧视图 / 原始 HEX）、`ComboBox` TYPE 过滤、`ToolButton` 暂停 / 清空、右侧三个 `CaptionLabel`（CRC错误 / 超时 / 已丢弃计数）
- 帧视图：`TableWidget`，列 = 时间 / 方向 / TYPE / ID / LEN / CRC状态 / payload HEX；TX 蓝、RX 绿、超时或错误红
- 原始 HEX 视图：`TextEdit`，经典 hex dump 格式

资源保护：
- 表格行数上限 5000（`removeRow(0)` 丢最早）
- 原始 HEX 视图 `QTextEdit.document().setMaximumBlockCount(...)` 限 1 MB
- 暂停缓冲区上限 10000 条，溢出时 `InfoBar.warning` 并丢弃新事件
- 点"清空"弹 `MessageBox` 二次确认

### 4.6 `widgets/debug_page.py`

顶层容器。布局：

```
QVBoxLayout:
  SerialPanel (固定高度)
  QSplitter(Vertical):
    FrameSender
    FrameLogView
```

### 4.7 `widgets/business_page.py`

业务面板。

- 顶部状态徽章（串口未连时红 + "请到协议调试页连接"；已连时绿 + 端口+波特率）
- 水平 `QSplitter`：
  - 左：`RealtimeChart(volt_max=config.chart_volt_max, curr_max=config.chart_curr_max, show_power=False)`（`show_power=False` 时内部跳过功率绘制，`pwr_max` 走构造函数默认值、不使用）
  - 右：`QVBoxLayout`
    - `CardWidget` 目标电压（大字 `DisplayLabel`，默认 `--- V`，超时变灰显示 `TIMEOUT` + 副标题 `上次: N.NNN V`）
    - `CardWidget` 目标电流（同上）
    - `PrimaryPushButton` 手动读取一次
    - `SwitchButton` 自动轮询 + `ComboBox` 周期（100/200/500/1000 ms，默认 500）
    - 分隔线
    - `SwitchButton` 心跳 + `ComboBox` 周期（500/1000/2000 ms，默认 1000）
    - `CaptionLabel` 上次更新时间

行为：
- 轮询开关打开 → `QTimer` 按周期调 `engine.query(0x01, bytes([0x10, 0x04]), on_resp, on_timeout, default_timeout_ms)`
- 心跳开关打开 → `QTimer` 按周期调 `engine.send_heartbeat(now_ms)`
- 响应处理：`data[0..1]` 回显校验，`data[2..5]` 大端 u32 → `v_mV`，`data[6..9]` 大端 u32 → `i_mA`，除 1000 转 V/A，更新卡片 + 曲线
- 超时处理：卡片变灰 + `TIMEOUT`；曲线跳过；`InfoBar.warning` 节流（5 秒内最多 1 次）
- 串口未连接：发送按钮禁用、顶部徽章红
- 串口掉线：轮询 / 心跳 QTimer **不停**（允许热重连，重连后自动恢复）

### 4.8 `widgets/settings_page.py`

设置页。

- `SwitchButton` 深色/浅色（保留现有行为）
- `SpinBox` 默认超时 (ms)（50..10000，默认 200）
- `ComboBox` 默认波特率（列同 `SerialPanel`）

编辑后存 `config.json`，下次启动生效（不热更新）。

### 4.9 `main.py`

`FluentWindow` 主入口。

```python
class MainWindow(FluentWindow):
    def __init__(self):
        super().__init__()
        self._config = ConfigManager().load()
        self._engine = TinyFrameEngine(self)

        self.businessPage = BusinessPage(self._engine, self._config, self)
        self.debugPage    = DebugPage(self._engine, self._config, self)
        self.settingsPage = SettingsPage(self._config, self)

        self.addSubInterface(self.businessPage, FIF.HOME, '业务面板')
        self.addSubInterface(self.debugPage,    FIF.DEVELOPER_TOOLS, '协议调试')
        self.addSubInterface(self.settingsPage, FIF.SETTING, '设置',
                             NavigationItemPosition.BOTTOM)
```

删除所有 CAN / REG1K0100A2 / BMS 相关 import 和代码。保留托盘图标、窗口图标、初始最大化等已有行为。

### 4.10 `config_manager.py` / `config.json`

```python
@dataclass
class AppConfig:
    device_name: str = "TinyFrame 上位机"
    default_port: str = ""
    default_baud: int = 115200
    default_timeout_ms: int = 200
    default_poll_ms: int = 500
    default_heartbeat_ms: int = 1000
    chart_volt_max: float = 1000.0
    chart_curr_max: float = 200.0
```

### 4.11 `chart_widget.py` 改造

在 `RealtimeChart.__init__` 加参数 `show_power: bool = True`（默认 True 保持向后兼容）。

- `show_power=False` 时：`paintEvent` 跳过右轴刻度与功率面积图；构建 UI 时不添加功率图例行；`push()` 的第三个参数仍接收但被忽略。

## 5. 数据流

### 5.1 业务页：读取设定点

1. 用户点击"读取一次"或轮询 QTimer 触发
2. `engine.query(0x01, bytes([0x10, 0x04]), on_resp, on_timeout, config.default_timeout_ms)`（payload 2 字节：addr 低字节 + count 低字节；下位机仅读取 payload 前 2 byte_t）
3. `TinyFrame` 分配 ID（偶数），构帧：`1B | ID_HI ID_LO | 00 02 | 01 | 10 04 | CRC_LO CRC_HI`（10 字节）
4. `write_impl` → `QSerialPort.write`；发 `rawBytesOut` / `frameSent` 信号；调试页日志显示 TX 行
5. 下位机响应到达：`QSerialPort.readyRead` → `TinyFrame.accept` → ID 监听器命中 → 触发 `on_resp(frame)`
6. 业务页解析：`addr, count = data[0], data[1]`；`v_mV = int.from_bytes(data[2:6], 'big')`；`i_mA = int.from_bytes(data[6:10], 'big')`
7. 更新卡片（`f"{v_mV/1000:.3f} V"`）、曲线 `chart.push(v_mV/1000, i_mA/1000, 0.0)`、上次更新时间

### 5.2 业务页：心跳

1. 心跳 QTimer 触发
2. `tick_ms = int(time.monotonic() * 1000) & 0xFFFFFFFF`
3. `engine.send_heartbeat(tick_ms)` → `send(0x03, tick_ms.to_bytes(4, 'big'))`（单向帧，ID=0）
4. 构帧发送，无响应等待

### 5.3 调试页：帧发送器

1. 解析 TYPE / payload HEX（失败弹 `InfoBar.error`）
2. Send 模式 → `engine.send(type_, data)`
3. Query 模式 → `engine.query(type_, data, ...)`，超时后日志行标红

### 5.4 所有收到的帧 → 日志

Engine 广播 `frameReceived` / `frameSent` / `queryTimeout` / `crcFailed` / `rawBytesIn` / `rawBytesOut`，`FrameLogView` 订阅并刷表格/raw 视图。

## 6. 错误处理

### 6.1 串口层

| 场景            | 检测                         | 反馈                                                         |
| --------------- | ---------------------------- | ------------------------------------------------------------ |
| 打开失败        | `QSerialPort.open()` 返回 False | `SerialPanel` 徽章红，`InfoBar.error`；开关弹回 Off            |
| 运行中掉线      | `QSerialPort.errorOccurred` | Engine 自动 `close()`；徽章红；业务页徽章红；**不停止轮询/心跳**（热重连） |

### 6.2 协议解析

| 场景     | 处理                                                         |
| -------- | ------------------------------------------------------------ |
| CRC 错误 | 丢弃帧，状态机复位，发 `crcFailed` 信号，日志红行，计数器 +1 |
| LEN 超限 | 静默丢弃，复位 IDLE，重同步计数器 +1                         |
| SOF 重同步 | 静默丢弃字节，raw HEX 视图仍可见                            |

日志顶部显示 `CRC错误 / 超时 / 已丢弃` 三个小计数，点"清空"按钮一并重置。

### 6.3 业务层

| 场景            | 反馈                                                         |
| --------------- | ------------------------------------------------------------ |
| 请求超时        | 卡片变灰 `TIMEOUT`（副标题保留上次值）；曲线跳过；`InfoBar.warning` 5 秒节流；日志红行 |
| 响应长度不对    | `InfoBar.error("期望 10 字节")`；日志黄行 `PROTOCOL_ERROR`  |
| 响应 addr/count 不匹配 | `InfoBar.error("响应地址不匹配")`；日志黄行          |

### 6.4 用户输入

| 场景             | 反馈                                               |
| ---------------- | -------------------------------------------------- |
| TYPE 非法        | 输入框红框 + `InfoBar.error("TYPE 必须是 0x00..0xFF")` |
| payload HEX 非法 | `InfoBar.error("payload 格式错误 / 超过 64 字节")` |

### 6.5 资源保护

- 日志表格 5000 行上限
- raw HEX 视图 1 MB 上限
- 暂停缓冲区 10000 条上限
- 清空操作需 `MessageBox` 二次确认
- 不做磁盘日志写入（MVP 范围外）

## 7. 测试策略

### 7.1 单元测试（`tests/test_protocol.py`）—— 必做

覆盖 `tinyframe/protocol.py`，纯 `pytest`。目标行覆盖 > 90%。

**构帧**：空 payload、普通 payload 字节黄金样本比对、不同 TYPE/ID/LEN、最大 64 字节边界、超限抛 `ValueError`。

**解析**：一次性喂完整帧、逐字节流式喂、CRC 错、LEN 超限、前置垃圾字节重同步、payload 内含 0x1B 不误触发、背靠背多帧、半帧后中断再接正常帧。

**ID 监听 + 超时**：ID 分配偶数自增、ID 命中触发 `on_response`、超时触发 `on_timeout(id, type)`、超时后迟到响应不再触发、ID 回绕不崩溃。

**CRC16 Modbus**：已知样本、空数据、单字节。使用 `crcmod.predefined.mkPredefinedCrcFun('modbus')` 对照。

### 7.2 不做集成测试

跳过 `pytest-qt` 依赖与 `test_engine.py`。

### 7.3 手动端到端验收

写入本文档末尾 `附录 A`。

## 8. 文件清理与新增

### 8.1 删除

- `FluentQtTest.py`, `FluentQtTest.ui`
- `manual_widget.py`
- `BMSDataType.py`
- `REG1K0100A2.py`
- `HDL_CAN.py`
- `ControlCAN.dll`

### 8.2 改造

- `main.py`（改成新 `MainWindow`）
- `config_manager.py` / `config.json`（新字段）
- `chart_widget.py`（加 `show_power` 参数）
- `requirements.txt`（加 `crcmod`，不加 `pyserial`）

### 8.3 新增

```
tinyframe/
    __init__.py
    protocol.py
    engine.py
widgets/
    __init__.py
    serial_panel.py
    frame_sender.py
    frame_log_view.py
    debug_page.py
    business_page.py
    settings_page.py
tests/
    test_protocol.py
```

### 8.4 保留不动

- `build.py` / `build_nuitka.bat` / `build.bat` / `build_onefile.bat` / `build_folder.bat` / `make_package.bat` / `start.bat` / `main.spec`
- `build_sign.pfx`
- `img/`, `resource/`, `doc/`

## 9. 非目标（明确不做）

- 日志文件导出 / CSV 保存
- 协议版本协商（TinyFrame 当前只有一套配置）
- 多串口并发
- 加密 / 鉴权
- `pyserial` 接口支持（只用 `QtSerialPort`）
- 业务页额外页面（保持 MVP：业务 + 调试 + 设置，共 3 页）

## 附录 A：手动端到端验收清单

**串口层**
- [ ] 打开不存在的端口 → 徽章红 + `InfoBar` 错误
- [ ] 打开成功 → 徽章绿 + 文字 "COM3 @ 115200"
- [ ] 拔 USB → 徽章红 + "已掉线"
- [ ] 重新插 USB 并点开关 → 重连成功
- [ ] 未连接状态下业务页发送按钮禁用，顶部徽章红

**业务页**
- [ ] 手动"读取一次"：下位机 set_voltage=123.456V, set_current=10.5A → 卡片显示 "123.456 V" / "10.500 A"
- [ ] 自动轮询 500 ms：曲线连续 60 秒不断点
- [ ] 心跳开关打开：下位机观察到 tick_ms 每秒 +1000 左右
- [ ] 把下位机断电：超时出现，卡片 `TIMEOUT`，上电后自动恢复

**调试页**
- [ ] 手工 Send：`TYPE=0x03 payload="12 34 56 78"` → 日志显示 TX 帧
- [ ] 手工 Query：`TYPE=0x01 payload="10 04"` → 200 ms 内显示 RX 响应
- [ ] 非法 HEX `"12 3G"` → `InfoBar.error`，不发送
- [ ] raw HEX 视图：能看到 SOF=1B 和每个字段
- [ ] TYPE 过滤：只选 0x02 → 只显示响应帧
- [ ] 暂停 → 日志冻结；恢复 → flush 缓冲
- [ ] 点"清空"弹 `MessageBox` 二次确认

**资源保护**
- [ ] 连续跑 30 分钟轮询 + 心跳，任务管理器观察内存不增长
- [ ] 连续跑到 5000 条日志后，最早的行被丢弃，无崩溃
