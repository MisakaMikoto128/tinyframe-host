# TinyFrame 上位机 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把原 REG1K0100A2 充电模块上位机改造为 TinyFrame 串口上位机，提供业务面板（读设定点 + 心跳 + 实时曲线）、协议调试页（串口控制 + 手动帧发送器 + 收发日志）、设置页。

**Architecture:** 分层解耦 —— `tinyframe/protocol.py` 是零 Qt 依赖的纯逻辑协议栈（状态机、CRC16 Modbus、ID 监听器、超时表），`tinyframe/engine.py` 是 `QObject` 薄包装层，负责桥接 `QSerialPort` 事件与协议栈回调；`widgets/` 下的每个 UI 组件只通过 engine 的 Qt 信号接收事件，不直接接触串口或协议内部。业务层只认 engine；测试层只测 protocol。

**Tech Stack:** Python 3, PyQt5 5.15 + `QtSerialPort`, qfluentwidgets 1.8, `crcmod` (CRC16 Modbus), pytest 9.

**参考文档:** `docs/superpowers/specs/2026-04-24-tinyframe-host-design.md`

---

## 前置说明

- 运行命令时的工作目录：`C:\Users\liuyu\Desktop\WorkPlace\TinyFrameHost`。
- Python 解释器：`.venv\Scripts\python.exe`；测试运行：`.venv\Scripts\python.exe -m pytest ...`。
- Windows + bash shell 环境；路径在 shell 中用正斜杠，在 Python 字符串中用原样即可。
- 所有 `git commit` 使用中文简短消息（跟历史风格一致），并带 Claude Co-Authored 尾。
- spec 里出现过的类名 / 方法名 / 信号名必须与本 plan 保持完全一致。

---

## File Structure

**新增（目录 + 文件）：**

| 路径                               | 责任                                                       |
| ---------------------------------- | ---------------------------------------------------------- |
| `tinyframe/__init__.py`            | 包入口，导出 `TinyFrame`, `TFFrame`, `TinyFrameEngine`     |
| `tinyframe/protocol.py`            | 纯 Python 协议栈（状态机 / 构帧 / CRC / ID / 超时）        |
| `tinyframe/engine.py`              | `TinyFrameEngine(QObject)`：QSerialPort + QTimer + 信号    |
| `widgets/__init__.py`              | 空包标记                                                    |
| `widgets/serial_panel.py`          | 调试页顶部串口连接条                                        |
| `widgets/frame_sender.py`          | 调试页中部手动帧发送器                                      |
| `widgets/frame_log_view.py`        | 调试页底部收发日志（表格 + raw hex）                       |
| `widgets/debug_page.py`            | 调试页顶层容器                                              |
| `widgets/business_page.py`         | 业务面板（卡片 + 曲线 + 轮询 + 心跳）                      |
| `widgets/settings_page.py`         | 设置页（主题 + 默认超时 + 默认波特率）                     |
| `tests/__init__.py`                | pytest 包标记                                               |
| `tests/test_protocol.py`           | `tinyframe/protocol.py` 单元测试                           |

**改造：**

| 路径                | 改动要点                                                    |
| ------------------- | ----------------------------------------------------------- |
| `main.py`           | 全部重写：新 `MainWindow`，注入 engine，装三个页面           |
| `config_manager.py` | `AppConfig` 字段替换为 TinyFrame 版                         |
| `config.json`       | 按新 `AppConfig` 重写                                        |
| `chart_widget.py`   | `__init__` 加 `show_power: bool = True` 参数及绘图分支      |
| `requirements.txt`  | 加 `crcmod`                                                  |

**删除：**

- `FluentQtTest.py`, `FluentQtTest.ui`, `manual_widget.py`, `BMSDataType.py`, `REG1K0100A2.py`, `HDL_CAN.py`, `ControlCAN.dll`

---

## Task 1: 清理旧项目文件

**Files:**
- Delete: `FluentQtTest.py`, `FluentQtTest.ui`, `manual_widget.py`, `BMSDataType.py`, `REG1K0100A2.py`, `HDL_CAN.py`, `ControlCAN.dll`

- [ ] **Step 1: 删除 CAN/BMS/REG 相关源文件**

```bash
rm -f FluentQtTest.py FluentQtTest.ui manual_widget.py BMSDataType.py REG1K0100A2.py HDL_CAN.py ControlCAN.dll
```

- [ ] **Step 2: 确认删除**

```bash
ls FluentQtTest.py manual_widget.py BMSDataType.py REG1K0100A2.py HDL_CAN.py ControlCAN.dll 2>&1
```

Expected: 所有行都显示 `No such file or directory`。

- [ ] **Step 3: 用 Grep 搜索残留引用（不应有结果）**

Run: `grep -rE "FluentQtTest|BMSDataType|REG1K0100A2|HDL_CAN|ControlCAN|manual_widget" --include="*.py" .` (excluding .venv)

Expected: `main.py` 里会有引用（这些是旧 `main.py` 的 import，下一个任务就会重写 `main.py`），除此之外无其他结果。

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "$(cat <<'EOF'
chore: 删除 CAN/BMS/REG1K0100A2 旧业务源文件

为 TinyFrame 串口上位机改造腾出空间。main.py 对这些模块的
引用会在下一次提交中清理。

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: 加依赖 crcmod + 创建必要目录骨架

**Files:**
- Modify: `requirements.txt`
- Create: `tinyframe/__init__.py`, `widgets/__init__.py`, `tests/__init__.py`

- [ ] **Step 1: 在 requirements.txt 末尾添加 crcmod**

编辑 `requirements.txt`，在文件末尾追加一行（保持现有行不变）：

```
crcmod==1.7
```

编辑完的完整内容：

```
PyQt5==5.15.11
PyQt5-sip==12.18.0
PyQt-Fluent-Widgets[full]==1.8.6
PyQt5-Frameless-Window==0.7.3
pywin32==306
pytest==9.0.3
crcmod==1.7
```

- [ ] **Step 2: 用 venv 安装 crcmod**

```bash
.venv/Scripts/python.exe -m pip install crcmod==1.7
```

Expected: 输出 `Successfully installed crcmod-1.7`（或已安装则 `Requirement already satisfied`）。

- [ ] **Step 3: 验证 crcmod 可用 + Modbus 预设存在**

```bash
.venv/Scripts/python.exe -c "import crcmod.predefined; f = crcmod.predefined.mkPredefinedCrcFun('modbus'); print(hex(f(b'\x01\x02\x03')))"
```

Expected: 输出 `0x6161`（CRC16 Modbus 对 `01 02 03` 的结果）。

- [ ] **Step 4: 创建包目录占位 __init__.py**

在 `tinyframe/__init__.py` 写入（空文件即可，以后再导出）：

```python
"""TinyFrame 协议栈（纯 Python 逻辑 + Qt 引擎包装）。"""
```

在 `widgets/__init__.py` 写入：

```python
"""UI 组件。"""
```

在 `tests/__init__.py` 写入空文件（0 字节）。

- [ ] **Step 5: Commit**

```bash
git add requirements.txt tinyframe/__init__.py widgets/__init__.py tests/__init__.py
git commit -m "$(cat <<'EOF'
deps: 添加 crcmod 并创建 tinyframe/widgets/tests 包骨架

crcmod 用于 CRC16 Modbus 计算，配合下位机 TinyFrame 移植版。
包骨架为后续协议栈和 UI 组件预留位置。

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: 定义 TFFrame 数据类 + TinyFrame 类框架（通过导入即通过的最小实现）

**Files:**
- Create: `tinyframe/protocol.py`
- Test: `tests/test_protocol.py`

- [ ] **Step 1: 写导入测试**

创建 `tests/test_protocol.py`：

```python
"""TinyFrame 协议栈单元测试。"""
import pytest
from tinyframe.protocol import TFFrame, TinyFrame


def test_tfframe_is_dataclass_with_expected_fields():
    f = TFFrame(type=0x01, id=0, data=b"\x10\x04", direction="tx")
    assert f.type == 0x01
    assert f.id == 0
    assert f.data == b"\x10\x04"
    assert f.direction == "tx"


def test_tinyframe_sof_constant():
    assert TinyFrame.SOF == 0x1B


def test_tinyframe_init_as_master():
    tf = TinyFrame(is_master=True)
    assert tf._is_master is True


def test_tinyframe_init_as_slave():
    tf = TinyFrame(is_master=False)
    assert tf._is_master is False
```

- [ ] **Step 2: 运行测试，确认 FAIL（模块尚未存在）**

```bash
.venv/Scripts/python.exe -m pytest tests/test_protocol.py -v
```

Expected: FAIL，报 `ModuleNotFoundError: No module named 'tinyframe.protocol'`。

- [ ] **Step 3: 创建 protocol.py 最小骨架**

创建 `tinyframe/protocol.py`：

```python
"""TinyFrame 纯 Python 协议栈。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional


@dataclass
class TFFrame:
    type: int
    id: int
    data: bytes
    direction: str


class TinyFrame:
    SOF = 0x1B

    def __init__(self, is_master: bool = True):
        self._is_master = is_master
```

- [ ] **Step 4: 运行测试，确认 PASS**

```bash
.venv/Scripts/python.exe -m pytest tests/test_protocol.py -v
```

Expected: 4 passed。

- [ ] **Step 5: Commit**

```bash
git add tinyframe/protocol.py tests/test_protocol.py
git commit -m "$(cat <<'EOF'
feat(tinyframe): 定义 TFFrame 与 TinyFrame 类骨架

协议栈第一步：最小可导入的类型定义。后续任务会逐步加上
状态机解析、构帧、CRC、ID 监听、超时。

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: 实现 CRC16 Modbus helper

**Files:**
- Modify: `tinyframe/protocol.py`
- Test: `tests/test_protocol.py`

- [ ] **Step 1: 追加 CRC 测试**

在 `tests/test_protocol.py` 末尾追加：

```python
from tinyframe.protocol import crc16_modbus


def test_crc16_empty():
    assert crc16_modbus(b"") == 0xFFFF


def test_crc16_single_byte():
    # crcmod 对 b"\x01" 的 CRC16 Modbus = 0x807E
    assert crc16_modbus(b"\x01") == 0x807E


def test_crc16_three_bytes():
    # 01 02 03 -> 0x6161
    assert crc16_modbus(b"\x01\x02\x03") == 0x6161


def test_crc16_matches_crcmod_library():
    import crcmod.predefined
    expected = crcmod.predefined.mkPredefinedCrcFun("modbus")
    samples = [b"", b"\x1B", b"\x1B\x00\x00\x00\x00\x03", bytes(range(64))]
    for s in samples:
        assert crc16_modbus(s) == expected(s), f"mismatch for {s!r}"
```

- [ ] **Step 2: 运行测试，确认 FAIL**

```bash
.venv/Scripts/python.exe -m pytest tests/test_protocol.py -v
```

Expected: 4 个新测试 FAIL，报 `ImportError: cannot import name 'crc16_modbus'`。

- [ ] **Step 3: 实现 crc16_modbus**

在 `tinyframe/protocol.py` 顶部 import 段下面、`@dataclass` 上面追加：

```python
import crcmod.predefined

_crc16_modbus_fn = crcmod.predefined.mkPredefinedCrcFun("modbus")


def crc16_modbus(data: bytes) -> int:
    """CRC16 Modbus。空输入返回 0xFFFF（Modbus 初值）。"""
    return _crc16_modbus_fn(data)
```

- [ ] **Step 4: 运行测试，确认 PASS**

```bash
.venv/Scripts/python.exe -m pytest tests/test_protocol.py -v
```

Expected: 8 passed。

- [ ] **Step 5: Commit**

```bash
git add tinyframe/protocol.py tests/test_protocol.py
git commit -m "$(cat <<'EOF'
feat(tinyframe): 接入 crcmod 的 CRC16 Modbus

包装成 crc16_modbus(bytes) -> int，已对照 crcmod 预设验证。
后续构帧和解析会直接使用。

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: 实现 compose（构帧）

**Files:**
- Modify: `tinyframe/protocol.py`
- Test: `tests/test_protocol.py`

- [ ] **Step 1: 追加构帧测试**

在 `tests/test_protocol.py` 末尾追加：

```python
def test_compose_empty_payload():
    tf = TinyFrame(is_master=True)
    # TYPE=0x03, ID=0x0002, payload 空
    frame = tf._compose(type_=0x03, id_=0x0002, data=b"")
    # 预期：1B 00 02 00 00 03 + CRC16_LE
    # CRC 输入 = 1B 00 02 00 00 03
    import crcmod.predefined
    crc = crcmod.predefined.mkPredefinedCrcFun("modbus")(b"\x1B\x00\x02\x00\x00\x03")
    expected = b"\x1B\x00\x02\x00\x00\x03" + bytes([crc & 0xFF, (crc >> 8) & 0xFF])
    assert frame == expected


def test_compose_with_payload():
    tf = TinyFrame(is_master=True)
    # REG_READ_REQ: TYPE=0x01, ID=0x0000, data=[0x10, 0x04]
    frame = tf._compose(type_=0x01, id_=0x0000, data=b"\x10\x04")
    # 1B 00 00 00 02 01 10 04 + CRC16_LE
    import crcmod.predefined
    crc = crcmod.predefined.mkPredefinedCrcFun("modbus")(b"\x1B\x00\x00\x00\x02\x01\x10\x04")
    expected = b"\x1B\x00\x00\x00\x02\x01\x10\x04" + bytes([crc & 0xFF, (crc >> 8) & 0xFF])
    assert frame == expected
    assert len(frame) == 10  # 8 header overhead + 2 payload


def test_compose_max_payload_64():
    tf = TinyFrame(is_master=True)
    data = bytes(range(64))
    frame = tf._compose(type_=0x05, id_=0x00AA, data=data)
    assert len(frame) == 8 + 64


def test_compose_payload_too_large_raises():
    tf = TinyFrame(is_master=True)
    data = bytes(65)
    with pytest.raises(ValueError, match="payload"):
        tf._compose(type_=0x01, id_=0, data=data)


def test_compose_type_out_of_range_raises():
    tf = TinyFrame(is_master=True)
    with pytest.raises(ValueError, match="type"):
        tf._compose(type_=0x100, id_=0, data=b"")


def test_compose_id_out_of_range_raises():
    tf = TinyFrame(is_master=True)
    with pytest.raises(ValueError, match="id"):
        tf._compose(type_=0x01, id_=0x10000, data=b"")
```

- [ ] **Step 2: 运行测试，确认 FAIL**

```bash
.venv/Scripts/python.exe -m pytest tests/test_protocol.py -v
```

Expected: 6 个新测试 FAIL（`_compose` 不存在）。

- [ ] **Step 3: 实现 _compose**

在 `TinyFrame` 类内追加（在 `__init__` 之下）：

```python
    MAX_PAYLOAD = 64

    def _compose(self, type_: int, id_: int, data: bytes) -> bytes:
        if not 0 <= type_ <= 0xFF:
            raise ValueError(f"type 超出 0x00..0xFF: {type_:#x}")
        if not 0 <= id_ <= 0xFFFF:
            raise ValueError(f"id 超出 0x0000..0xFFFF: {id_:#x}")
        if len(data) > self.MAX_PAYLOAD:
            raise ValueError(f"payload 长度 {len(data)} > {self.MAX_PAYLOAD}")

        header = bytes([
            self.SOF,
            (id_ >> 8) & 0xFF, id_ & 0xFF,
            (len(data) >> 8) & 0xFF, len(data) & 0xFF,
            type_ & 0xFF,
        ]) + data
        crc = crc16_modbus(header)
        return header + bytes([crc & 0xFF, (crc >> 8) & 0xFF])
```

- [ ] **Step 4: 运行测试，确认 PASS**

```bash
.venv/Scripts/python.exe -m pytest tests/test_protocol.py -v
```

Expected: 14 passed。

- [ ] **Step 5: Commit**

```bash
git add tinyframe/protocol.py tests/test_protocol.py
git commit -m "$(cat <<'EOF'
feat(tinyframe): 实现 _compose 构帧（SOF+ID+LEN+TYPE+DATA+CRC_LE）

覆盖空 payload、普通 payload、64 字节边界，以及 type/id/payload
范围校验。CRC 字节序为小端（Modbus 标准）。

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: 实现 accept（状态机解析）+ on_any_frame / on_type 监听器

**Files:**
- Modify: `tinyframe/protocol.py`
- Test: `tests/test_protocol.py`

- [ ] **Step 1: 追加解析测试（先加基础场景）**

在 `tests/test_protocol.py` 末尾追加：

```python
def _build_frame(type_: int, id_: int, data: bytes) -> bytes:
    tf = TinyFrame()
    return tf._compose(type_=type_, id_=id_, data=data)


def test_accept_full_frame_triggers_on_any_frame():
    tf = TinyFrame()
    captured = []
    tf.on_any_frame(lambda f: captured.append(f))
    tf.accept(_build_frame(0x02, 0x0000, b"\x10\x04\x00\x00\x00\x01\x00\x00\x00\x02"))
    assert len(captured) == 1
    assert captured[0].type == 0x02
    assert captured[0].id == 0x0000
    assert captured[0].data == b"\x10\x04\x00\x00\x00\x01\x00\x00\x00\x02"
    assert captured[0].direction == "rx"


def test_accept_streamed_byte_by_byte():
    tf = TinyFrame()
    captured = []
    tf.on_any_frame(lambda f: captured.append(f))
    frame = _build_frame(0x03, 0x00AA, b"\x12\x34\x56\x78")
    for b in frame:
        tf.accept(bytes([b]))
    assert len(captured) == 1
    assert captured[0].data == b"\x12\x34\x56\x78"


def test_accept_bad_crc_does_not_trigger():
    tf = TinyFrame()
    captured = []
    tf.on_any_frame(lambda f: captured.append(f))
    frame = _build_frame(0x02, 0, b"\x01") 
    # 翻转最后一字节（CRC_HI）
    bad = frame[:-1] + bytes([frame[-1] ^ 0xFF])
    tf.accept(bad)
    assert captured == []


def test_accept_bad_crc_triggers_on_crc_failed():
    tf = TinyFrame()
    failed = []
    tf.on_crc_failed(lambda f: failed.append(f))
    frame = _build_frame(0x02, 0x55, b"\xAA")
    bad = frame[:-1] + bytes([frame[-1] ^ 0x01])
    tf.accept(bad)
    assert len(failed) == 1
    assert failed[0].type == 0x02
    assert failed[0].id == 0x55


def test_accept_len_over_max_resyncs_silently():
    tf = TinyFrame()
    captured = []
    tf.on_any_frame(lambda f: captured.append(f))
    # 构造 LEN=0x00FF（超过 64），随后接正常帧，验证能重同步
    noise = b"\x1B\x00\x00\x00\xFF\x01"  # LEN=255
    tf.accept(noise)
    good = _build_frame(0x02, 0, b"\x42")
    tf.accept(good)
    assert len(captured) == 1
    assert captured[0].data == b"\x42"


def test_accept_leading_garbage_then_frame():
    tf = TinyFrame()
    captured = []
    tf.on_any_frame(lambda f: captured.append(f))
    tf.accept(b"\x00\xFF\x77\x23")  # 垃圾
    tf.accept(_build_frame(0x02, 0, b"\x01"))
    assert len(captured) == 1


def test_accept_payload_containing_sof_byte():
    tf = TinyFrame()
    captured = []
    tf.on_any_frame(lambda f: captured.append(f))
    tf.accept(_build_frame(0x02, 0, b"\x1B\x1B\x1B"))
    assert len(captured) == 1
    assert captured[0].data == b"\x1B\x1B\x1B"


def test_accept_back_to_back_frames():
    tf = TinyFrame()
    captured = []
    tf.on_any_frame(lambda f: captured.append(f))
    buf = _build_frame(0x02, 0, b"\x01") + _build_frame(0x02, 2, b"\x02") + _build_frame(0x02, 4, b"\x03")
    tf.accept(buf)
    assert len(captured) == 3
    assert [f.data for f in captured] == [b"\x01", b"\x02", b"\x03"]


def test_accept_half_frame_then_new_frame():
    tf = TinyFrame()
    captured = []
    tf.on_any_frame(lambda f: captured.append(f))
    frame = _build_frame(0x02, 0, b"\x01\x02\x03")
    # 喂前一半（不完整）
    tf.accept(frame[:5])
    # 中途收到另一个完整帧（前一半会被抛弃直到下一个 SOF 对齐）
    # 但状态机等 LEN 个字节到齐后才校验 CRC，所以继续喂剩下字节仍可能完成当前"半帧+下一帧前缀"
    # 本用例验证：收到垃圾（= 没对上 CRC）后，下一个完整帧仍能解出。
    tf.accept(b"\xFF\xFF\xFF")  # 污染当前状态机
    tf.accept(_build_frame(0x02, 0, b"\xAB"))
    # 至少能解出 b"\xAB" 这一帧；之前的半帧即使凑出错误 CRC 也只是被丢弃
    assert any(f.data == b"\xAB" for f in captured)


def test_on_type_listener_triggered_for_matching_type_only():
    tf = TinyFrame()
    type_02_captured = []
    type_03_captured = []
    tf.on_type(0x02, lambda f: type_02_captured.append(f))
    tf.on_type(0x03, lambda f: type_03_captured.append(f))
    tf.accept(_build_frame(0x02, 0, b"\xA"))
    tf.accept(_build_frame(0x03, 0, b"\xB"))
    assert len(type_02_captured) == 1 and type_02_captured[0].data == b"\xA"
    assert len(type_03_captured) == 1 and type_03_captured[0].data == b"\xB"
```

- [ ] **Step 2: 运行测试，确认 FAIL**

```bash
.venv/Scripts/python.exe -m pytest tests/test_protocol.py -v
```

Expected: 新增 10 个测试全部 FAIL（`accept` / `on_any_frame` / `on_type` / `on_crc_failed` 都不存在）。

- [ ] **Step 3: 实现状态机 + 监听器注册**

在 `tinyframe/protocol.py` 最上方（`crc16_modbus` 下面）追加枚举：

```python
from enum import IntEnum


class _State(IntEnum):
    IDLE = 0
    ID_HI = 1
    ID_LO = 2
    LEN_HI = 3
    LEN_LO = 4
    TYPE = 5
    DATA = 6
    CRC_LO = 7
    CRC_HI = 8
```

在 `TinyFrame.__init__` 末尾追加内部状态：

```python
        # 解析器状态
        self._state = _State.IDLE
        self._rx_id = 0
        self._rx_len = 0
        self._rx_type = 0
        self._rx_data = bytearray()
        self._rx_crc = 0
        # 校验用缓冲（SOF..DATA 的所有字节，送到 crc16_modbus）
        self._rx_crc_buf = bytearray()

        # 监听器
        self._any_listeners: list[Callable[[TFFrame], None]] = []
        self._type_listeners: dict[int, list[Callable[[TFFrame], None]]] = {}
        self._crc_failed_listeners: list[Callable[[TFFrame], None]] = []
```

在 `TinyFrame` 类中追加方法：

```python
    # ---- 监听器注册 ----
    def on_any_frame(self, cb: Callable[[TFFrame], None]) -> None:
        self._any_listeners.append(cb)

    def on_type(self, type_: int, cb: Callable[[TFFrame], None]) -> None:
        self._type_listeners.setdefault(type_ & 0xFF, []).append(cb)

    def on_crc_failed(self, cb: Callable[[TFFrame], None]) -> None:
        self._crc_failed_listeners.append(cb)

    # ---- 状态机 ----
    def _reset(self) -> None:
        self._state = _State.IDLE
        self._rx_id = 0
        self._rx_len = 0
        self._rx_type = 0
        self._rx_data = bytearray()
        self._rx_crc = 0
        self._rx_crc_buf = bytearray()

    def accept(self, raw: bytes) -> None:
        for byte in raw:
            self._feed(byte)

    def _feed(self, b: int) -> None:
        if self._state == _State.IDLE:
            if b == self.SOF:
                self._rx_crc_buf = bytearray([b])
                self._state = _State.ID_HI
            # 否则丢弃
            return

        self._rx_crc_buf.append(b)

        if self._state == _State.ID_HI:
            self._rx_id = b << 8
            self._state = _State.ID_LO
        elif self._state == _State.ID_LO:
            self._rx_id |= b
            self._state = _State.LEN_HI
        elif self._state == _State.LEN_HI:
            self._rx_len = b << 8
            self._state = _State.LEN_LO
        elif self._state == _State.LEN_LO:
            self._rx_len |= b
            if self._rx_len > self.MAX_PAYLOAD:
                self._reset()
                return
            self._state = _State.TYPE
        elif self._state == _State.TYPE:
            self._rx_type = b
            self._rx_data = bytearray()
            if self._rx_len == 0:
                self._state = _State.CRC_LO
            else:
                self._state = _State.DATA
        elif self._state == _State.DATA:
            self._rx_data.append(b)
            if len(self._rx_data) == self._rx_len:
                self._state = _State.CRC_LO
        elif self._state == _State.CRC_LO:
            # 此字节不在 CRC 覆盖范围内 —— 刚刚添加到 buf，撤回
            self._rx_crc_buf.pop()
            self._rx_crc = b
            self._state = _State.CRC_HI
        elif self._state == _State.CRC_HI:
            self._rx_crc_buf.pop()  # CRC_HI 也不在 CRC 覆盖范围
            self._rx_crc |= b << 8
            calc = crc16_modbus(bytes(self._rx_crc_buf))
            frame = TFFrame(
                type=self._rx_type,
                id=self._rx_id,
                data=bytes(self._rx_data),
                direction="rx",
            )
            if calc == self._rx_crc:
                self._dispatch(frame)
            else:
                for cb in self._crc_failed_listeners:
                    cb(frame)
            self._reset()

    def _dispatch(self, frame: TFFrame) -> None:
        for cb in self._type_listeners.get(frame.type, []):
            cb(frame)
        for cb in self._any_listeners:
            cb(frame)
```

- [ ] **Step 4: 运行测试，确认 PASS**

```bash
.venv/Scripts/python.exe -m pytest tests/test_protocol.py -v
```

Expected: 24 passed。

- [ ] **Step 5: Commit**

```bash
git add tinyframe/protocol.py tests/test_protocol.py
git commit -m "$(cat <<'EOF'
feat(tinyframe): 实现 accept 状态机 + on_any_frame/on_type 监听

状态机覆盖 IDLE→ID_HI→ID_LO→LEN_HI→LEN_LO→TYPE→DATA→
CRC_LO→CRC_HI，LEN 超限静默重同步，CRC 错发 on_crc_failed，
其余成功帧派发给 type 和 any 两类监听器。

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: 实现 send（单向发送）+ write_impl 注入

**Files:**
- Modify: `tinyframe/protocol.py`
- Test: `tests/test_protocol.py`

- [ ] **Step 1: 追加测试**

在 `tests/test_protocol.py` 末尾追加：

```python
def test_send_writes_composed_frame():
    tf = TinyFrame(is_master=True)
    sent = []
    tf.write_impl = lambda b: sent.append(b)
    tf.send(type_=0x03, data=b"\x12\x34\x56\x78")
    assert len(sent) == 1
    # Send 用 id=0（单向帧）
    expected = tf._compose(type_=0x03, id_=0, data=b"\x12\x34\x56\x78")
    assert sent[0] == expected


def test_send_without_write_impl_raises():
    tf = TinyFrame()
    with pytest.raises(RuntimeError, match="write_impl"):
        tf.send(type_=0x03, data=b"")
```

- [ ] **Step 2: 运行测试，确认 FAIL**

```bash
.venv/Scripts/python.exe -m pytest tests/test_protocol.py -v
```

Expected: 新 2 个 FAIL（`send` 不存在或 `write_impl` 未定义）。

- [ ] **Step 3: 添加 send 与 write_impl**

在 `TinyFrame.__init__` 末尾追加：

```python
        # 写出回调（engine 侧注入）
        self.write_impl: Optional[Callable[[bytes], None]] = None
```

在 `TinyFrame` 类中追加：

```python
    def send(self, type_: int, data: bytes) -> None:
        if self.write_impl is None:
            raise RuntimeError("write_impl 未设置，无法发送")
        frame = self._compose(type_=type_, id_=0, data=data)
        self.write_impl(frame)
```

- [ ] **Step 4: 运行测试，确认 PASS**

```bash
.venv/Scripts/python.exe -m pytest tests/test_protocol.py -v
```

Expected: 26 passed。

- [ ] **Step 5: Commit**

```bash
git add tinyframe/protocol.py tests/test_protocol.py
git commit -m "$(cat <<'EOF'
feat(tinyframe): 添加 send() 单向发送和 write_impl 注入点

send() 使用固定 ID=0 表示单向帧。write_impl 由上层注入
（engine 层会把它接到 QSerialPort.write）。

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: 实现 query（请求-响应配对）+ ID 分配器

**Files:**
- Modify: `tinyframe/protocol.py`
- Test: `tests/test_protocol.py`

- [ ] **Step 1: 追加测试**

在 `tests/test_protocol.py` 末尾追加：

```python
def test_query_allocates_even_ids():
    tf = TinyFrame(is_master=True)
    tf.write_impl = lambda b: None
    ids = [tf.query(type_=0x01, data=b"", on_response=lambda f: None,
                    on_timeout=lambda i, t: None, timeout_ms=100)
           for _ in range(5)]
    assert ids == [0, 2, 4, 6, 8]


def test_query_response_triggers_on_response_and_not_on_type():
    tf = TinyFrame(is_master=True)
    tf.write_impl = lambda b: None

    responses = []
    type_any = []
    tf.on_type(0x02, lambda f: type_any.append(f))
    tf.query(type_=0x01, data=b"\x10\x04",
             on_response=lambda f: responses.append(f),
             on_timeout=lambda i, t: None,
             timeout_ms=100)
    # 响应帧：ID=0（上面分配的第一个），TYPE=0x02
    tf.accept(tf._compose(type_=0x02, id_=0, data=b"\xAA\xBB"))
    assert len(responses) == 1
    assert responses[0].data == b"\xAA\xBB"
    # on_type(0x02) 在 ID 命中时仍会触发（规范：ID 监听不屏蔽 type 监听）
    # 如果想改成 ID 命中时跳过 type 分派，这条断言要翻转
    assert len(type_any) == 1


def test_query_response_with_wrong_id_does_not_trigger_on_response():
    tf = TinyFrame(is_master=True)
    tf.write_impl = lambda b: None
    responses = []
    tf.query(type_=0x01, data=b"",
             on_response=lambda f: responses.append(f),
             on_timeout=lambda i, t: None,
             timeout_ms=100)
    tf.accept(tf._compose(type_=0x02, id_=0x99, data=b""))
    assert responses == []


def test_query_id_wraps_around():
    tf = TinyFrame(is_master=True)
    tf.write_impl = lambda b: None
    tf._next_id = 0xFFFC
    ids = [tf.query(type_=0x01, data=b"", on_response=lambda f: None,
                    on_timeout=lambda i, t: None, timeout_ms=100)
           for _ in range(3)]
    assert ids == [0xFFFC, 0xFFFE, 0x0000]
```

- [ ] **Step 2: 运行测试，确认 FAIL**

```bash
.venv/Scripts/python.exe -m pytest tests/test_protocol.py -v
```

Expected: 新 4 个 FAIL。

- [ ] **Step 3: 实现 query + ID 分配**

在 `TinyFrame.__init__` 末尾追加：

```python
        # ID 分配（MASTER 偶数自增）
        self._next_id = 0
        # 挂起的 query：{id: (on_response, on_timeout, remaining_ms, type_)}
        self._pending: dict[int, tuple] = {}
```

在 `TinyFrame` 类中追加：

```python
    def _alloc_id(self) -> int:
        if not self._is_master:
            raise RuntimeError("SLAVE 不应分配 ID")
        allocated = self._next_id
        self._next_id = (self._next_id + 2) & 0xFFFF
        return allocated

    def query(self,
              type_: int,
              data: bytes,
              on_response: Callable[[TFFrame], None],
              on_timeout: Callable[[int, int], None],
              timeout_ms: int = 200) -> int:
        if self.write_impl is None:
            raise RuntimeError("write_impl 未设置，无法发送")
        id_ = self._alloc_id()
        self._pending[id_] = (on_response, on_timeout, timeout_ms, type_ & 0xFF)
        frame = self._compose(type_=type_, id_=id_, data=data)
        self.write_impl(frame)
        return id_
```

修改 `_dispatch` —— ID 监听优先触发（在 type_listeners 之前）：

```python
    def _dispatch(self, frame: TFFrame) -> None:
        pending = self._pending.pop(frame.id, None)
        if pending is not None:
            on_resp, _on_to, _remaining, _type = pending
            on_resp(frame)
        for cb in self._type_listeners.get(frame.type, []):
            cb(frame)
        for cb in self._any_listeners:
            cb(frame)
```

- [ ] **Step 4: 运行测试，确认 PASS**

```bash
.venv/Scripts/python.exe -m pytest tests/test_protocol.py -v
```

Expected: 30 passed。

- [ ] **Step 5: Commit**

```bash
git add tinyframe/protocol.py tests/test_protocol.py
git commit -m "$(cat <<'EOF'
feat(tinyframe): 实现 query() + MASTER 偶数 ID 分配

query 发送后把 (on_response, on_timeout, remaining_ms, type)
记录到 _pending，收到匹配 ID 的帧时 on_response 优先触发。
ID 在 0..0xFFFE 间按 +2 自增、回绕到 0。

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 9: 实现 tick（超时驱动）

**Files:**
- Modify: `tinyframe/protocol.py`
- Test: `tests/test_protocol.py`

- [ ] **Step 1: 追加测试**

在 `tests/test_protocol.py` 末尾追加：

```python
def test_tick_triggers_timeout_when_elapsed():
    tf = TinyFrame(is_master=True)
    tf.write_impl = lambda b: None
    timeouts = []
    id_ = tf.query(type_=0x01, data=b"",
                   on_response=lambda f: None,
                   on_timeout=lambda i, t: timeouts.append((i, t)),
                   timeout_ms=200)
    tf.tick(100)
    assert timeouts == []
    tf.tick(100)
    assert timeouts == [(id_, 0x01)]


def test_tick_late_response_after_timeout_is_ignored():
    tf = TinyFrame(is_master=True)
    tf.write_impl = lambda b: None
    responses = []
    timeouts = []
    id_ = tf.query(type_=0x01, data=b"",
                   on_response=lambda f: responses.append(f),
                   on_timeout=lambda i, t: timeouts.append(i),
                   timeout_ms=50)
    tf.tick(100)
    assert timeouts == [id_]
    # 迟到响应
    tf.accept(tf._compose(type_=0x02, id_=id_, data=b""))
    assert responses == []


def test_tick_does_not_affect_pending_below_timeout():
    tf = TinyFrame(is_master=True)
    tf.write_impl = lambda b: None
    responses = []
    id_ = tf.query(type_=0x01, data=b"",
                   on_response=lambda f: responses.append(f),
                   on_timeout=lambda i, t: None,
                   timeout_ms=500)
    tf.tick(100)
    tf.accept(tf._compose(type_=0x02, id_=id_, data=b"\x01"))
    assert len(responses) == 1
```

- [ ] **Step 2: 运行测试，确认 FAIL**

```bash
.venv/Scripts/python.exe -m pytest tests/test_protocol.py -v
```

Expected: 新 3 个 FAIL（`tick` 不存在）。

- [ ] **Step 3: 实现 tick**

在 `TinyFrame` 类中追加：

```python
    def tick(self, elapsed_ms: int) -> None:
        expired = []
        for id_, (on_resp, on_to, remaining, type_) in list(self._pending.items()):
            new_remaining = remaining - elapsed_ms
            if new_remaining <= 0:
                expired.append((id_, on_to, type_))
            else:
                self._pending[id_] = (on_resp, on_to, new_remaining, type_)
        for id_, on_to, type_ in expired:
            self._pending.pop(id_, None)
            on_to(id_, type_)
```

- [ ] **Step 4: 运行测试，确认 PASS**

```bash
.venv/Scripts/python.exe -m pytest tests/test_protocol.py -v
```

Expected: 33 passed。

- [ ] **Step 5: Commit**

```bash
git add tinyframe/protocol.py tests/test_protocol.py
git commit -m "$(cat <<'EOF'
feat(tinyframe): 实现 tick() 超时驱动

每次 tick 递减 _pending 中所有条目的 remaining_ms，≤0 时
弹出并调用 on_timeout(id, type)。超时后迟到响应被丢弃。

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 10: protocol.py 覆盖率检查 + 导出到 __init__

**Files:**
- Modify: `tinyframe/__init__.py`
- Test: `tests/test_protocol.py`

- [ ] **Step 1: 运行覆盖率，确认 > 90%**

```bash
.venv/Scripts/python.exe -m pip install coverage==7.6.1
.venv/Scripts/python.exe -m coverage run -m pytest tests/test_protocol.py
.venv/Scripts/python.exe -m coverage report -m --include="tinyframe/protocol.py"
```

Expected: 行覆盖 > 90%。若低于 90%，补测试（常见漏掉的分支是 `_alloc_id` 中 `is_master=False` 的异常路径，以及 CRC 覆盖缓冲的 pop 边界）。

- [ ] **Step 2: 如需补 SLAVE 分支测试**

若上一步提示 `_alloc_id` 未覆盖，在 `tests/test_protocol.py` 末尾追加：

```python
def test_slave_cannot_alloc_id():
    tf = TinyFrame(is_master=False)
    tf.write_impl = lambda b: None
    with pytest.raises(RuntimeError, match="SLAVE"):
        tf.query(type_=0x01, data=b"",
                 on_response=lambda f: None,
                 on_timeout=lambda i, t: None,
                 timeout_ms=100)
```

然后重新运行覆盖率。

- [ ] **Step 3: 更新 tinyframe/__init__.py 导出**

重写 `tinyframe/__init__.py`：

```python
"""TinyFrame 协议栈（纯 Python 逻辑 + Qt 引擎包装）。"""
from tinyframe.protocol import TFFrame, TinyFrame, crc16_modbus

__all__ = ["TFFrame", "TinyFrame", "crc16_modbus"]
```

- [ ] **Step 4: 确认包导入成功**

```bash
.venv/Scripts/python.exe -c "from tinyframe import TFFrame, TinyFrame, crc16_modbus; print('ok')"
```

Expected: 输出 `ok`。

- [ ] **Step 5: Commit**

```bash
git add tinyframe/__init__.py tests/test_protocol.py
git commit -m "$(cat <<'EOF'
feat(tinyframe): 导出 TFFrame/TinyFrame/crc16_modbus，补 SLAVE 测试

__init__ 暴露主要 API。pytest-cov 行覆盖 > 90%。

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 11: 实现 TinyFrameEngine 基础框架（open/close/is_open + 信号定义）

**Files:**
- Create: `tinyframe/engine.py`
- Modify: `tinyframe/__init__.py`

- [ ] **Step 1: 创建 engine.py**

创建 `tinyframe/engine.py`：

```python
"""TinyFrame 引擎：包装 QSerialPort 为 Qt 友好的信号/槽接口。"""
from __future__ import annotations

from typing import Callable, Optional

from PyQt5.QtCore import QObject, QTimer, pyqtSignal
from PyQt5.QtSerialPort import QSerialPort, QSerialPortInfo

from tinyframe.protocol import TFFrame, TinyFrame


_PARITY_MAP = {
    "none": QSerialPort.NoParity,
    "even": QSerialPort.EvenParity,
    "odd": QSerialPort.OddParity,
    "mark": QSerialPort.MarkParity,
    "space": QSerialPort.SpaceParity,
}
_STOPBITS_MAP = {
    1: QSerialPort.OneStop,
    2: QSerialPort.TwoStop,
}
_DATABITS_MAP = {
    5: QSerialPort.Data5,
    6: QSerialPort.Data6,
    7: QSerialPort.Data7,
    8: QSerialPort.Data8,
}


class TinyFrameEngine(QObject):
    connected = pyqtSignal(str)            # port_name
    disconnected = pyqtSignal(str)         # reason
    frameReceived = pyqtSignal(object)     # TFFrame
    frameSent = pyqtSignal(object)         # TFFrame
    queryTimeout = pyqtSignal(int, int)    # id, type
    rawBytesIn = pyqtSignal(bytes)
    rawBytesOut = pyqtSignal(bytes)
    crcFailed = pyqtSignal(object)         # TFFrame

    TICK_INTERVAL_MS = 10

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._serial = QSerialPort(self)
        self._serial.readyRead.connect(self._on_ready_read)
        self._serial.errorOccurred.connect(self._on_error)

        self._tf = TinyFrame(is_master=True)
        self._tf.write_impl = self._write_to_serial
        self._tf.on_any_frame(self._on_frame)
        self._tf.on_crc_failed(lambda f: self.crcFailed.emit(f))

        self._tick_timer = QTimer(self)
        self._tick_timer.setInterval(self.TICK_INTERVAL_MS)
        self._tick_timer.timeout.connect(lambda: self._tf.tick(self.TICK_INTERVAL_MS))
        self._tick_timer.start()

    # ---- 串口控制 ----
    def open(self, port_name: str, baud: int = 115200,
             data_bits: int = 8, stop_bits: int = 1,
             parity: str = "none") -> bool:
        if self._serial.isOpen():
            self._serial.close()
        self._serial.setPortName(port_name)
        self._serial.setBaudRate(baud)
        self._serial.setDataBits(_DATABITS_MAP.get(data_bits, QSerialPort.Data8))
        self._serial.setStopBits(_STOPBITS_MAP.get(stop_bits, QSerialPort.OneStop))
        self._serial.setParity(_PARITY_MAP.get(parity.lower(), QSerialPort.NoParity))
        self._serial.setFlowControl(QSerialPort.NoFlowControl)
        ok = self._serial.open(QSerialPort.ReadWrite)
        if ok:
            self.connected.emit(port_name)
        else:
            self.disconnected.emit(self._serial.errorString())
        return ok

    def close(self) -> None:
        if self._serial.isOpen():
            self._serial.close()
            self.disconnected.emit("用户关闭")

    def is_open(self) -> bool:
        return self._serial.isOpen()

    @staticmethod
    def list_ports() -> list[str]:
        return [p.portName() for p in QSerialPortInfo.availablePorts()]

    # ---- 协议转发 ----
    def query(self, type_: int, data: bytes,
              on_response: Callable[[TFFrame], None],
              on_timeout: Callable[[int, int], None],
              timeout_ms: int = 200) -> int:
        if not self.is_open():
            return -1

        def _wrapped_timeout(i: int, t: int) -> None:
            self.queryTimeout.emit(i, t)
            on_timeout(i, t)

        return self._tf.query(type_, data, on_response, _wrapped_timeout, timeout_ms)

    def send(self, type_: int, data: bytes) -> None:
        if not self.is_open():
            return
        self._tf.send(type_, data)

    def send_heartbeat(self, tick_ms: int) -> None:
        payload = (tick_ms & 0xFFFFFFFF).to_bytes(4, "big")
        self.send(0x03, payload)

    # ---- 内部 ----
    def _write_to_serial(self, data: bytes) -> None:
        self._serial.write(data)
        self.rawBytesOut.emit(data)
        # 构造 TFFrame 发 frameSent 信号（发送路径不经过解析器，这里手工解一下头）
        if len(data) >= 8:
            id_ = (data[1] << 8) | data[2]
            length = (data[3] << 8) | data[4]
            type_ = data[5]
            payload = bytes(data[6:6 + length])
            self.frameSent.emit(TFFrame(type=type_, id=id_, data=payload, direction="tx"))

    def _on_frame(self, frame: TFFrame) -> None:
        self.frameReceived.emit(frame)

    def _on_ready_read(self) -> None:
        raw = bytes(self._serial.readAll())
        if raw:
            self.rawBytesIn.emit(raw)
            self._tf.accept(raw)

    def _on_error(self, err) -> None:
        if err == QSerialPort.NoError:
            return
        if self._serial.isOpen():
            self._serial.close()
        self.disconnected.emit(self._serial.errorString())
```

- [ ] **Step 2: 更新 `tinyframe/__init__.py`**

```python
"""TinyFrame 协议栈（纯 Python 逻辑 + Qt 引擎包装）。"""
from tinyframe.protocol import TFFrame, TinyFrame, crc16_modbus
from tinyframe.engine import TinyFrameEngine

__all__ = ["TFFrame", "TinyFrame", "TinyFrameEngine", "crc16_modbus"]
```

- [ ] **Step 3: 验证可导入（不实例化，避免起 QApplication）**

```bash
.venv/Scripts/python.exe -c "from tinyframe import TinyFrameEngine; print('ok')"
```

Expected: 输出 `ok`。

- [ ] **Step 4: 运行现有测试确认无回退**

```bash
.venv/Scripts/python.exe -m pytest tests/ -v
```

Expected: 所有协议层测试仍通过（engine 不在测试覆盖范围内，spec 7.2 已明确不做集成测试）。

- [ ] **Step 5: Commit**

```bash
git add tinyframe/engine.py tinyframe/__init__.py
git commit -m "$(cat <<'EOF'
feat(tinyframe): TinyFrameEngine(QObject) 包装 QSerialPort + QTimer

对外提供 open/close/query/send/send_heartbeat 接口和
connected/disconnected/frameReceived/frameSent/queryTimeout/
rawBytesIn/rawBytesOut/crcFailed 信号。10ms tick 定时器
驱动协议栈超时计数。

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 12: 改造 chart_widget.py 添加 show_power 参数

**Files:**
- Modify: `chart_widget.py`

- [ ] **Step 1: Read 当前 chart_widget.py L266-353 确认结构**

```bash
.venv/Scripts/python.exe -c "print(open('chart_widget.py', encoding='utf-8').read()[7500:])"
```

记录 `RealtimeChart.__init__` 签名、`_build_ui` 中功率图例的位置、`paintEvent` 功率绘图的分支。

- [ ] **Step 2: 修改 `RealtimeChart.__init__` 添加参数**

将 `chart_widget.py` L266-283 的 `__init__`：

```python
    def __init__(self, volt_max=1000.0, curr_max=100.0, pwr_max=30000.0,
                 parent=None):
        super().__init__(parent)
```

改为：

```python
    def __init__(self, volt_max=1000.0, curr_max=100.0, pwr_max=30000.0,
                 show_power: bool = True, parent=None):
        super().__init__(parent)
        self._show_power = show_power
```

同时在 `__init__` 末尾（`self._build_ui()` 调用之前）确保 `self._show_pwr` 在 `show_power=False` 时被强制为 False：

找到原行：
```python
        self._show_pwr   = True
```

改为：
```python
        self._show_pwr   = bool(show_power)
```

- [ ] **Step 3: 修改 `_build_ui` 在 show_power=False 时不添加功率图例**

找到 `_build_ui` 中添加功率图例的段落（约 L319-332）：

```python
        self._pwr_leg  = _LegendItem('功率', '（右轴）', _PWR_HEX,  is_area=True)
        ...
        self._pwr_leg.connect_toggle(
            lambda s: self._toggle('pwr',  s == Qt.Checked))

        legend = QHBoxLayout()
        legend.setSpacing(20)
        legend.addWidget(self._volt_leg)
        legend.addWidget(self._curr_leg)
        legend.addWidget(self._pwr_leg)
        legend.addStretch()
        vbox.addLayout(legend)
```

改为：

```python
        if self._show_power:
            self._pwr_leg  = _LegendItem('功率', '（右轴）', _PWR_HEX,  is_area=True)
            self._pwr_leg.connect_toggle(
                lambda s: self._toggle('pwr',  s == Qt.Checked))
        else:
            self._pwr_leg = None

        legend = QHBoxLayout()
        legend.setSpacing(20)
        legend.addWidget(self._volt_leg)
        legend.addWidget(self._curr_leg)
        if self._pwr_leg is not None:
            legend.addWidget(self._pwr_leg)
        legend.addStretch()
        vbox.addLayout(legend)
```

- [ ] **Step 4: 修改 `push` 跳过没有 pwr_leg 时的 set_value**

找到 `push` 方法（约 L285-294）：

```python
    def push(self, volt: float, curr: float, power: float):
        if self._paused:
            return
        self._volt_data.append(float(volt))
        self._curr_data.append(float(curr))
        self._pwr_data.append(float(power))
        self._canvas.update()
        self._volt_leg.set_value(f'{volt:.1f} V')
        self._curr_leg.set_value(f'{curr:.2f} A')
        self._pwr_leg.set_value(f'{power:.0f} W')
```

改为：

```python
    def push(self, volt: float, curr: float, power: float):
        if self._paused:
            return
        self._volt_data.append(float(volt))
        self._curr_data.append(float(curr))
        self._pwr_data.append(float(power))
        self._canvas.update()
        self._volt_leg.set_value(f'{volt:.1f} V')
        self._curr_leg.set_value(f'{curr:.2f} A')
        if self._pwr_leg is not None:
            self._pwr_leg.set_value(f'{power:.0f} W')
```

- [ ] **Step 5: 修改 `_ChartCanvas.paintEvent` 跳过右轴刻度（show_power=False 时）**

`paintEvent` 中约 L97-100 的右轴标绘制：

```python
            # 右轴标（功率）
            p_lbl = _fmt_y(c._pwr_max * frac, 'W') + ('W' if c._pwr_max < 1000 else '')
            painter.setPen(axis_r_c)
            painter.drawText(W - rm + 4, y - 7, rm - 4, 14,
                             Qt.AlignLeft | Qt.AlignVCenter, p_lbl)
```

在外面包一层判断：

```python
            if c._show_power:
                # 右轴标（功率）
                p_lbl = _fmt_y(c._pwr_max * frac, 'W') + ('W' if c._pwr_max < 1000 else '')
                painter.setPen(axis_r_c)
                painter.drawText(W - rm + 4, y - 7, rm - 4, 14,
                                 Qt.AlignLeft | Qt.AlignVCenter, p_lbl)
```

还有 L115-117 右轴单位标注 `'W'`：

```python
        painter.setPen(axis_r_c)
        painter.drawText(W - rm, tm - 2, rm, 14, Qt.AlignCenter, 'W')
```

改为：

```python
        if c._show_power:
            painter.setPen(axis_r_c)
            painter.drawText(W - rm, tm - 2, rm, 14, Qt.AlignCenter, 'W')
```

还有 L124 的功率绘图分支：

```python
        if c._show_pwr and len(c._pwr_data) >= 2:
```

改为：

```python
        if c._show_power and c._show_pwr and len(c._pwr_data) >= 2:
```

- [ ] **Step 6: 手动冒烟验证**

创建临时验证脚本 `tmp_chart_check.py`：

```python
import sys
from PyQt5.QtWidgets import QApplication
from chart_widget import RealtimeChart

app = QApplication(sys.argv)
# show_power=False 下构造不应抛异常
w = RealtimeChart(volt_max=1000.0, curr_max=200.0, show_power=False)
w.push(10.0, 2.0, 0.0)
w.resize(800, 400)
w.show()
print("show_power=False 构造和 push 正常")
# 不进入事件循环，立即退出
```

运行：

```bash
.venv/Scripts/python.exe tmp_chart_check.py
rm tmp_chart_check.py
```

Expected: 输出 `show_power=False 构造和 push 正常`；无异常。

- [ ] **Step 7: Commit**

```bash
git add chart_widget.py
git commit -m "$(cat <<'EOF'
feat(chart_widget): 添加 show_power 参数，False 时不绘功率轴/图例

默认 show_power=True 保持向后兼容。False 时跳过右轴刻度、
单位标注、功率图例，以及面积图绘制。push 的第三个参数
仍接收但不写图例。

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 13: 改造 config_manager.py + config.json 为 TinyFrame 版

**Files:**
- Modify: `config_manager.py`
- Modify: `config.json`

- [ ] **Step 1: 重写 `config_manager.py`**

用以下内容完全替换 `config_manager.py`：

```python
import json
import os
from dataclasses import dataclass, asdict


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


class ConfigManager:
    def __init__(self, config_path: str = "config.json"):
        self._path = config_path

    def load(self) -> AppConfig:
        if not os.path.exists(self._path):
            default = AppConfig()
            self.save(default)
            return default
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                data = json.load(f)
            d = AppConfig()
            return AppConfig(
                device_name=data.get("device_name", d.device_name),
                default_port=str(data.get("default_port", d.default_port)),
                default_baud=int(data.get("default_baud", d.default_baud)),
                default_timeout_ms=int(data.get("default_timeout_ms", d.default_timeout_ms)),
                default_poll_ms=int(data.get("default_poll_ms", d.default_poll_ms)),
                default_heartbeat_ms=int(data.get("default_heartbeat_ms", d.default_heartbeat_ms)),
                chart_volt_max=float(data.get("chart_volt_max", d.chart_volt_max)),
                chart_curr_max=float(data.get("chart_curr_max", d.chart_curr_max)),
            )
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            return AppConfig()

    def save(self, cfg: AppConfig) -> None:
        try:
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(asdict(cfg), f, ensure_ascii=False, indent=2)
        except OSError:
            pass
```

- [ ] **Step 2: 重写 `config.json`**

```json
{
  "device_name": "TinyFrame 上位机",
  "default_port": "",
  "default_baud": 115200,
  "default_timeout_ms": 200,
  "default_poll_ms": 500,
  "default_heartbeat_ms": 1000,
  "chart_volt_max": 1000.0,
  "chart_curr_max": 200.0
}
```

- [ ] **Step 3: 冒烟验证**

```bash
.venv/Scripts/python.exe -c "from config_manager import ConfigManager; c = ConfigManager().load(); print(c)"
```

Expected: 输出 `AppConfig(device_name='TinyFrame 上位机', default_port='', default_baud=115200, default_timeout_ms=200, default_poll_ms=500, default_heartbeat_ms=1000, chart_volt_max=1000.0, chart_curr_max=200.0)`。

- [ ] **Step 4: Commit**

```bash
git add config_manager.py config.json
git commit -m "$(cat <<'EOF'
feat(config): AppConfig 字段切换为 TinyFrame 上位机语义

字段：device_name / default_port / default_baud /
default_timeout_ms / default_poll_ms / default_heartbeat_ms /
chart_volt_max / chart_curr_max。ConfigManager 新增 save()。

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 14: 创建 SerialPanel（串口连接条）

**Files:**
- Create: `widgets/serial_panel.py`

- [ ] **Step 1: 创建 widgets/serial_panel.py**

```python
"""调试页顶部串口连接条。"""
from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QFrame, QHBoxLayout
from qfluentwidgets import (CaptionLabel, ComboBox, FluentIcon as FIF,
                            IconInfoBadge, InfoBar, InfoBarPosition, InfoLevel,
                            SwitchButton, ToolButton)

from tinyframe import TinyFrameEngine

_BAUDS = [9600, 19200, 38400, 57600, 115200, 230400, 460800]


class SerialPanel(QFrame):
    def __init__(self, engine: TinyFrameEngine, default_baud: int = 115200,
                 parent=None):
        super().__init__(parent)
        self._engine = engine

        self._port_cb = ComboBox(self)
        self._port_cb.setFixedWidth(140)
        self._refresh_btn = ToolButton(FIF.SYNC, self)
        self._refresh_btn.setToolTip("刷新端口列表")
        self._refresh_btn.setFixedSize(28, 28)
        self._refresh_btn.clicked.connect(self._refresh_ports)

        self._baud_cb = ComboBox(self)
        self._baud_cb.setFixedWidth(100)
        for b in _BAUDS:
            self._baud_cb.addItem(str(b))
        self._baud_cb.setCurrentText(str(default_baud if default_baud in _BAUDS else 115200))

        self._toggle = SwitchButton(self)
        self._toggle.setOnText("关闭串口")
        self._toggle.setOffText("打开串口")
        self._toggle.checkedChanged.connect(self._on_toggle)

        self._badge = IconInfoBadge.info(FIF.CONNECT, self)
        self._badge.setLevel(InfoLevel.INFOAMTION)
        self._status_label = CaptionLabel("未连接", self)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(8)
        layout.addWidget(CaptionLabel("端口：", self))
        layout.addWidget(self._port_cb)
        layout.addWidget(self._refresh_btn)
        layout.addSpacing(8)
        layout.addWidget(CaptionLabel("波特率：", self))
        layout.addWidget(self._baud_cb)
        layout.addSpacing(16)
        layout.addWidget(self._toggle)
        layout.addSpacing(8)
        layout.addWidget(self._badge)
        layout.addWidget(self._status_label)
        layout.addStretch()
        self.setFixedHeight(44)

        engine.connected.connect(self._on_connected)
        engine.disconnected.connect(self._on_disconnected)

        self._refresh_ports()

    def _refresh_ports(self) -> None:
        current = self._port_cb.currentText()
        self._port_cb.clear()
        ports = TinyFrameEngine.list_ports()
        for p in ports:
            self._port_cb.addItem(p)
        if current in ports:
            self._port_cb.setCurrentText(current)

    def _on_toggle(self, checked: bool) -> None:
        if checked:
            port = self._port_cb.currentText().strip()
            baud = int(self._baud_cb.currentText())
            if not port:
                InfoBar.error("未选择端口", "请先选择一个可用端口", duration=3000,
                              position=InfoBarPosition.TOP, parent=self)
                self._toggle.setChecked(False)
                return
            ok = self._engine.open(port, baud=baud)
            if not ok:
                self._toggle.setChecked(False)
        else:
            self._engine.close()

    def _on_connected(self, port: str) -> None:
        self._badge.setLevel(InfoLevel.SUCCESS)
        self._status_label.setText(f"{port} @ {self._baud_cb.currentText()}")
        if not self._toggle.isChecked():
            self._toggle.blockSignals(True)
            self._toggle.setChecked(True)
            self._toggle.blockSignals(False)

    def _on_disconnected(self, reason: str) -> None:
        self._badge.setLevel(InfoLevel.ERROR)
        self._status_label.setText(f"未连接：{reason}")
        if self._toggle.isChecked():
            self._toggle.blockSignals(True)
            self._toggle.setChecked(False)
            self._toggle.blockSignals(False)
        InfoBar.error("串口错误", reason, duration=5000,
                      position=InfoBarPosition.TOP, parent=self)
```

- [ ] **Step 2: 导入冒烟验证**

```bash
.venv/Scripts/python.exe -c "from widgets.serial_panel import SerialPanel; print('ok')"
```

Expected: 输出 `ok`。

- [ ] **Step 3: Commit**

```bash
git add widgets/serial_panel.py
git commit -m "$(cat <<'EOF'
feat(widgets): SerialPanel 串口连接条

端口下拉 + 刷新、波特率下拉、打开/关闭开关、状态徽章。
订阅 engine.connected/disconnected 同步 UI，打开失败时
弹回开关并弹 InfoBar.error。

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 15: 创建 FrameSender（手动帧发送器）

**Files:**
- Create: `widgets/frame_sender.py`

- [ ] **Step 1: 创建 widgets/frame_sender.py**

```python
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
```

- [ ] **Step 2: 导入冒烟验证**

```bash
.venv/Scripts/python.exe -c "from widgets.frame_sender import FrameSender; print('ok')"
```

Expected: 输出 `ok`。

- [ ] **Step 3: Commit**

```bash
git add widgets/frame_sender.py
git commit -m "$(cat <<'EOF'
feat(widgets): FrameSender 手动帧发送器

TYPE/payload HEX 输入、Send/Query 单选、超时 SpinBox、
发送按钮。HEX 解析失败弹 InfoBar.error 阻断发送。
Send 路径 engine.send；Query 路径 engine.query（响应和
超时会被全局日志捕获，这里不关心具体回调）。

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 16: 创建 FrameLogView（收发日志 + raw HEX 切换）

**Files:**
- Create: `widgets/frame_log_view.py`

- [ ] **Step 1: 创建 widgets/frame_log_view.py**

```python
"""调试页底部：收发日志（帧视图 + 原始 HEX 视图 + 过滤/暂停）。"""
from __future__ import annotations

import time
from collections import deque

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QBrush, QColor, QFont
from PyQt5.QtWidgets import (QFrame, QHBoxLayout, QHeaderView, QStackedWidget,
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
            while self._buffer:
                kind, payload = self._buffer.popleft()
                self._apply(kind, payload)
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
    def _on_event(self, kind: str, payload) -> None:
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
        if frame.type not in self._known_types:
            self._known_types.add(frame.type)
            self._filter_cb.addItem(f"TYPE=0x{frame.type:02X}", userData=frame.type)

        filter_type = self._filter_cb.currentData()
        if filter_type is not None and filter_type != frame.type:
            return

        row = self._table.rowCount()
        if row >= _MAX_TABLE_ROWS:
            self._table.removeRow(0)
            row -= 1
        self._table.insertRow(row)

        ts = time.strftime("%H:%M:%S") + f".{int((time.time() % 1) * 1000):03d}"
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
        ts = time.strftime("%H:%M:%S") + f".{int((time.time() % 1) * 1000):03d}"
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
```

- [ ] **Step 2: 导入冒烟验证**

```bash
.venv/Scripts/python.exe -c "from widgets.frame_log_view import FrameLogView; print('ok')"
```

Expected: 输出 `ok`。

- [ ] **Step 3: Commit**

```bash
git add widgets/frame_log_view.py
git commit -m "$(cat <<'EOF'
feat(widgets): FrameLogView 收发日志（帧视图 + raw hex + 过滤 + 暂停）

订阅 engine 的 frameReceived/frameSent/queryTimeout/
crcFailed/rawBytesIn/rawBytesOut 信号。表格 5000 行上限，
超限 removeRow(0)。暂停缓冲 10000 条上限。清空需二次确认。

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 17: 创建 DebugPage（调试页容器）

**Files:**
- Create: `widgets/debug_page.py`

- [ ] **Step 1: 创建 widgets/debug_page.py**

```python
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
```

- [ ] **Step 2: 导入冒烟验证**

```bash
.venv/Scripts/python.exe -c "from widgets.debug_page import DebugPage; print('ok')"
```

Expected: 输出 `ok`。

- [ ] **Step 3: Commit**

```bash
git add widgets/debug_page.py
git commit -m "$(cat <<'EOF'
feat(widgets): DebugPage 调试页容器

顶部固定 SerialPanel，下方 QSplitter(Vertical) 装
FrameSender 与 FrameLogView，初始比例 160:480。

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 18: 创建 BusinessPage（业务面板）

**Files:**
- Create: `widgets/business_page.py`

- [ ] **Step 1: 创建 widgets/business_page.py**

```python
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
        self._poll_cb.setCurrentText(f"{config.default_poll_ms} ms")
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
        self._hb_cb.setCurrentText(f"{config.default_heartbeat_ms} ms")
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
```

- [ ] **Step 2: 导入冒烟验证**

```bash
.venv/Scripts/python.exe -c "from widgets.business_page import BusinessPage; print('ok')"
```

Expected: 输出 `ok`。

- [ ] **Step 3: Commit**

```bash
git add widgets/business_page.py
git commit -m "$(cat <<'EOF'
feat(widgets): BusinessPage 业务面板

左侧 RealtimeChart（show_power=False），右侧两张卡片 +
手动读取按钮 + 自动轮询开关 + 心跳开关。响应解析
[addr,count,v_mV(4B BE),i_mA(4B BE)]=10 字节；超时
卡片变灰 + TIMEOUT + 副标题保留上次值，InfoBar 5 秒节流。

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 19: 创建 SettingsPage

**Files:**
- Create: `widgets/settings_page.py`

- [ ] **Step 1: 创建 widgets/settings_page.py**

```python
"""设置页：主题 + 默认超时 + 默认波特率。"""
from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QFrame, QFormLayout, QHBoxLayout, QVBoxLayout
from qfluentwidgets import (BodyLabel, ComboBox, InfoBar, InfoBarPosition,
                            PrimaryPushButton, SpinBox, StrongBodyLabel,
                            SwitchButton, Theme, setTheme, TitleLabel)

from config_manager import AppConfig, ConfigManager

_BAUDS = [9600, 19200, 38400, 57600, 115200, 230400, 460800]


class SettingsPage(QFrame):
    def __init__(self, config: AppConfig, config_manager: ConfigManager, parent=None):
        super().__init__(parent)
        self.setObjectName("settingsPage")
        self._config = config
        self._cm = config_manager

        title = TitleLabel("设置", self)

        self._theme_switch = SwitchButton(self)
        self._theme_switch.setOnText("深色")
        self._theme_switch.setOffText("浅色")
        self._theme_switch.checkedChanged.connect(
            lambda: setTheme(Theme.DARK if self._theme_switch.isChecked() else Theme.LIGHT)
        )

        self._timeout_sb = SpinBox(self)
        self._timeout_sb.setRange(50, 10000)
        self._timeout_sb.setValue(config.default_timeout_ms)
        self._timeout_sb.setSuffix(" ms")

        self._baud_cb = ComboBox(self)
        for b in _BAUDS:
            self._baud_cb.addItem(str(b))
        self._baud_cb.setCurrentText(str(config.default_baud if config.default_baud in _BAUDS else 115200))

        self._save_btn = PrimaryPushButton("保存（下次启动生效）", self)
        self._save_btn.clicked.connect(self._save)

        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(10)
        form.addRow(BodyLabel("主题：", self), self._theme_switch)
        form.addRow(BodyLabel("默认超时：", self), self._timeout_sb)
        form.addRow(BodyLabel("默认波特率：", self), self._baud_cb)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 14, 20, 14)
        outer.addWidget(title)
        outer.addSpacing(8)
        outer.addLayout(form)
        outer.addSpacing(12)
        save_row = QHBoxLayout()
        save_row.addWidget(self._save_btn)
        save_row.addStretch()
        outer.addLayout(save_row)
        outer.addStretch()

    def _save(self) -> None:
        self._config.default_timeout_ms = self._timeout_sb.value()
        self._config.default_baud = int(self._baud_cb.currentText())
        self._cm.save(self._config)
        InfoBar.success("已保存", "下次启动生效",
                        duration=3000, position=InfoBarPosition.TOP, parent=self)
```

- [ ] **Step 2: 导入冒烟验证**

```bash
.venv/Scripts/python.exe -c "from widgets.settings_page import SettingsPage; print('ok')"
```

Expected: 输出 `ok`。

- [ ] **Step 3: Commit**

```bash
git add widgets/settings_page.py
git commit -m "$(cat <<'EOF'
feat(widgets): SettingsPage 主题/默认超时/默认波特率

编辑后点击"保存"写入 config.json，下次启动生效。主题切换
立即生效（保留现有交互）。

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 20: 重写 main.py（新 MainWindow）

**Files:**
- Modify: `main.py`

- [ ] **Step 1: 重写 main.py**

用以下内容完全替换 `main.py`：

```python
import sys

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QAction, QApplication, QMenu, QSystemTrayIcon
from qfluentwidgets import (FluentIcon as FIF, FluentWindow, Action,
                            NavigationItemPosition, setThemeColor)
from qfluentwidgets.components.material import AcrylicMenu

from config_manager import ConfigManager
from tinyframe import TinyFrameEngine
from widgets.business_page import BusinessPage
from widgets.debug_page import DebugPage
from widgets.settings_page import SettingsPage


class MainWindow(FluentWindow):
    def __init__(self):
        super().__init__()
        self._cm = ConfigManager()
        self._config = self._cm.load()

        setThemeColor("#28afe9")

        self._engine = TinyFrameEngine(self)

        self.businessPage = BusinessPage(self._engine, self._config, self)
        self.businessPage.setObjectName("businessPage")
        self.debugPage = DebugPage(self._engine, self._config, self)
        self.debugPage.setObjectName("debugPage")
        self.settingsPage = SettingsPage(self._config, self._cm, self)
        self.settingsPage.setObjectName("settingsPage")

        self._init_navigation()
        self._init_window()
        self._init_tray()

    def _init_navigation(self) -> None:
        self.addSubInterface(self.businessPage, FIF.HOME, "业务面板")
        self.addSubInterface(self.debugPage, FIF.DEVELOPER_TOOLS, "协议调试")
        self.navigationInterface.addSeparator()
        self.addSubInterface(self.settingsPage, FIF.SETTING, "设置",
                             NavigationItemPosition.BOTTOM)
        self.navigationInterface.setAcrylicEnabled(True)

    def _init_window(self) -> None:
        self.setWindowTitle(self._config.device_name)
        self.setWindowIcon(QIcon("./img/star.png"))
        self.resize(1100, 720)
        desktop = QApplication.desktop().availableGeometry()
        self.move(desktop.width() // 2 - self.width() // 2,
                  desktop.height() // 2 - self.height() // 2)
        self.setWindowState(Qt.WindowMaximized)

    def _init_tray(self) -> None:
        exit_action = QAction(QIcon("./img/sp-exit.png"), "Exit", self)
        exit_action.triggered.connect(self.close)
        tray_menu = QMenu(self)
        tray_menu.addAction(exit_action)
        self._tray_icon = QSystemTrayIcon(self)
        self._tray_icon.setIcon(QIcon("./img/star.png"))
        self._tray_icon.setContextMenu(tray_menu)
        self._tray_icon.show()

    def contextMenuEvent(self, e) -> None:
        menu = AcrylicMenu(parent=self)
        menu.addAction(Action(FIF.SETTING, "设置"))
        menu.exec(e.globalPos())

    def closeEvent(self, event) -> None:
        self._engine.close()
        event.accept()


if __name__ == "__main__":
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())
```

- [ ] **Step 2: 导入冒烟验证**

```bash
.venv/Scripts/python.exe -c "import importlib; m = importlib.import_module('main'); print('ok')"
```

Expected: 输出 `ok`（仅导入不启动，`if __name__ == '__main__'` 守卫生效）。

- [ ] **Step 3: 冷启动验证（人工）**

```bash
.venv/Scripts/python.exe main.py
```

观察：
- 窗口正常打开、最大化
- 左侧导航有"业务面板 / 协议调试 / 设置"三项
- 业务面板顶部状态徽章红 + 文字"串口未连接"
- 协议调试页顶部串口连接条可见，端口下拉能列出当前系统端口
- 设置页三项（主题开关 / 默认超时 SpinBox / 默认波特率 ComboBox）与"保存"按钮可见

关闭窗口退出。

- [ ] **Step 4: Commit**

```bash
git add main.py
git commit -m "$(cat <<'EOF'
feat(main): 重写 MainWindow 为 TinyFrame 上位机入口

创建 TinyFrameEngine 实例并注入到 BusinessPage/DebugPage/
SettingsPage。保留窗口图标、托盘、Acrylic 导航、初始最大化
等原有行为。删除所有 CAN/REG/BMS 相关 import 和代码。

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 21: 文档同步 & 收尾

**Files:**
- Modify: `docs/superpowers/specs/2026-04-24-tinyframe-host-design.md`（可选补充）

- [ ] **Step 1: 跑全部 pytest 最后一次确认**

```bash
.venv/Scripts/python.exe -m pytest tests/ -v
```

Expected: 全绿（≥ 34 passed）。

- [ ] **Step 2: 再次冒烟启动 main.py，对照 spec 附录 A 第一组"未连接状态下业务页发送按钮禁用、顶部徽章红"手动验证**

```bash
.venv/Scripts/python.exe main.py
```

观察：
- 业务面板"读取一次"按钮禁用（灰色）
- 顶部状态徽章红 + 文字"串口未连接"
- 协议调试页：打开一个不存在的端口（选端口下拉里空的或不存在的 COMxxx）→ 徽章红，弹 InfoBar.error

关闭窗口。

- [ ] **Step 3: 把手动验证结果贴到 spec 附录 A 的对应 checkbox**

编辑 `docs/superpowers/specs/2026-04-24-tinyframe-host-design.md` 附录 A，把第一个分组 "串口层" 的前两项（不存在端口 + 未连接禁用）的 `[ ]` 改成 `[x]`，表示本地冒烟通过。其他项留给后续真机联调。

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/specs/2026-04-24-tinyframe-host-design.md
git commit -m "$(cat <<'EOF'
docs: 在 spec 附录 A 勾选已本地冒烟通过的验收项

剩余 checkbox 留给下位机真机联调阶段。

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## 附录：常见故障速查

1. **`ImportError: No module named 'qfluentwidgets'`** —— 确认 `.venv` 激活或使用 `.venv/Scripts/python.exe` 前缀。
2. **`QSerialPort: device is not open`** —— 确认先打开串口（SerialPanel 开关 checked）再发送。
3. **全绿测试但 `main.py` 启动时 `AttributeError: module 'qfluentwidgets' has no attribute 'DisplayLabel'`** —— qfluentwidgets 1.8.6 中 `DisplayLabel` 已导出；若运行时报不存在，检查 venv 里实际版本：`.venv/Scripts/python.exe -m pip show PyQt-Fluent-Widgets`。
4. **打包 / 运行时中文显示乱码** —— 源文件和 `config.json` 均为 UTF-8（无 BOM）。`json.dump(..., ensure_ascii=False)` 已保证。
5. **业务页曲线不刷新** —— 确认 `RealtimeChart.push(v, i, 0.0)` 被 `_on_setpoint_response` 调用；确认 `show_power=False` 时 `push` 的第三个参数被 chart_widget 正确忽略。

---

## Self-Review（plan 作者自查结果）

**1. Spec 覆盖**：
- 协议契约（spec 第 2 节）→ Task 3–9 全面覆盖（TFFrame/CRC/compose/accept/send/query/tick）
- 架构（spec 第 3 节）→ Task 11 (Engine) + Task 20 (MainWindow 注入) 对应
- 组件 4.1–4.11 → Task 3–11 / 12 / 13 / 14–19 / 20 一一对应
- 数据流 5.1–5.4 → Task 18（业务页读 + 心跳）、Task 15（帧发送器）、Task 16（日志订阅）
- 错误处理 6.1–6.5 → Task 11 (engine 掉线信号) + Task 14（SerialPanel 错误反馈）+ Task 15 (HEX 校验)+ Task 16 (日志资源上限 + 清空二次确认) + Task 18 (超时节流与卡片变灰)
- 测试 7.1 → Task 3–10（TDD 全程覆盖）
- 文件清理 8.1 → Task 1；改造 8.2 → Task 2/12/13；新增 8.3 → Task 3–11/14–19
- 非目标 9 → plan 中未涉及 CSV 导出、多串口、pyserial 等，符合

**2. Placeholder 扫描**：无 TBD/TODO/待定；每个代码步骤都给了完整代码或完整 diff 位置。

**3. 类型一致性**：`TinyFrameEngine` 的方法签名（`open/close/query/send/send_heartbeat/list_ports/is_open`）在 Task 11 定义，后续 Task 14–18 调用处全一致。信号名 `connected/disconnected/frameReceived/frameSent/queryTimeout/rawBytesIn/rawBytesOut/crcFailed` 在 Task 11 定义，Task 14/16/18 订阅处一致。`TFFrame` 字段 `type/id/data/direction` 在 Task 3 定义，后续解析处一致。`config_manager.ConfigManager.save()` 在 Task 13 新增，Task 19 设置页调用。
