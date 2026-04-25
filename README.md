<div align="center">

# TinyFrame Host

一款基于 **PyQt5 + Fluent Design** 的 **TinyFrame** 串口上位机 · 实时曲线、帧收发调试、CRC16 Modbus · 纯 Python 协议栈

A PyQt5-based **TinyFrame** serial host with real-time charts, interactive frame debugging and a pure-Python protocol stack.

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![PyQt5](https://img.shields.io/badge/PyQt5-5.15-41CD52?logo=qt&logoColor=white)](https://pypi.org/project/PyQt5/)
[![Fluent](https://img.shields.io/badge/UI-Fluent%20Design-0078D4)](https://github.com/zhiyiYo/PyQt-Fluent-Widgets)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows-lightgrey)](#)
[![Tests](https://img.shields.io/badge/tests-39%20passed-brightgreen)](tests/)

</div>

---

## 📖 简介

TinyFrame Host 是一个把 **[TinyFrame](https://github.com/MightyPork/TinyFrame)** 这个轻量级二进制协议 做成 **Fluent 风格 Windows 上位机** 的完整样例工程。适合做：

- **MCU 调试助手**：用来和 STM32 / TI C2000 / ESP32 等下位机跑 TinyFrame 协议时的图形化调试工具
- **PyQt5 + qfluentwidgets 实践参考**：Fluent 2 风格双Y轴曲线、可交互帧表格、串口面板、设置页全部包含
- **纯 Python TinyFrame 协议栈**：0 Qt 依赖，33 个单元测试覆盖，可直接拆出来用在任何项目里

## ✨ 截图

> 🚧 截图待补充 — 可放入 `docs/screenshots/` 后替换下面占位图。

| 业务面板 | 协议调试 | 关于页 |
| :---: | :---: | :---: |
| <sub>*placeholder*</sub> | <sub>*placeholder*</sub> | <sub>*placeholder*</sub> |

## 🔥 功能亮点

- 📈 **双 Y 轴实时曲线** — QPainter 自绘，60 s 滑动窗口，左蓝右橙配色，掉帧控制在 150 ms push
- 🔁 **请求 / 响应配对** — MASTER 偶数 ID 自增，`query()` 回调 + `timeout_ms` 超时自动触发
- 💓 **心跳定时器** — 500 / 1000 / 2000 ms 可切，`0x03` 帧自动带 4 字节 big-endian 毫秒时钟
- 🔌 **串口热插拔** — 200 ms diff 扫描端口列表，掉线后定时器不停，插回即恢复
- 📋 **帧表格 + TSV 复制** — Ctrl+C / 右键菜单直接粘贴到 Excel，带方向 / 类型 / ID / CRC / payload 五列
- 💾 **配置持久化** — 波特率、校验位、停止位、端口名、轮询周期自动存 `config.json`
- 🎨 **Fluent 2 风格** — qfluentwidgets 1.8，深色 / 浅色跟随系统
- 🔐 **CRC16 Modbus** — `crcmod` 预设，覆盖 SOF..DATA 字节区

## 🧩 TinyFrame 帧格式

```text
┌─────┬──────┬──────┬──────┬───────────┬────────┐
│ SOF │  ID  │ LEN  │ TYPE │   DATA    │ CRC16  │
│ 1B  │  2B  │  2B  │  1B  │  N bytes  │   2B   │
│0x1B │  BE  │  BE  │      │  ≤ 64 B   │modbus  │
└─────┴──────┴──────┴──────┴───────────┴────────┘
  ↑___________________________________↑    ↑
         CRC 覆盖区（不含自己）             LE 小端
```

- 固定开销 **8 字节**，payload 上限 **64 字节**
- ID 分配：MASTER 偶数自增（`0, 2, 4, …, 0xFFFE` 回绕）
- 默认帧类型：
  - `0x01` `REG_READ_REQ` — 寄存器读请求
  - `0x02` `REG_READ_RSP` — 寄存器读应答
  - `0x03` `HEARTBEAT`    — 心跳

> 协议源自 [MightyPork/TinyFrame](https://github.com/MightyPork/TinyFrame)（C 版），本项目为纯 Python 重写，协议兼容但 API 按 Pythonic 习惯调整。

## 🚀 快速开始

### 环境要求

- Windows 10 / 11（Linux / macOS 未测试，QSerialPort 本身跨平台，理论可行）
- Python **3.10+**

### 一键启动

```bat
git clone https://github.com/MisakaMikoto128/tinyframe-host.git
cd tinyframe-host
start.bat
```

`start.bat` 会自动创建 `.venv`、安装依赖、并启动主程序。

### 手动安装

```bash
python -m venv .venv
.venv\Scripts\activate           # Windows
# source .venv/bin/activate       # Linux / macOS
pip install -r requirements.txt
python main.py
```

### 运行测试

```bash
pytest tests/ -v
# 39 passed in ~0.2s  (纯 Python，不需要 Qt 环境)
```

### 打包 exe

```bash
python build.py          # 文件夹模式（默认）
python build.py onefile  # 单文件模式
# 产物在 release/v<version>/
```

## 🏗️ 架构总览

```text
┌──────────────────────────────────────────────┐
│                   main.py                    │
│           MainWindow (FluentWindow)          │
├───────────────┬─────────────────┬────────────┤
│  BusinessPage │   DebugPage     │ SettingsPage│
│  读设定点+曲线│   串口+手动+日志 │  参数持久化 │
└───────┬───────┴────────┬────────┴──────┬─────┘
        │                │                │
        └────────┬───────┴────────────────┘
                 ▼
        ┌─────────────────┐      ┌──────────────┐
        │ TinyFrameEngine │─────▶│  QSerialPort │
        │  (Qt 信号/槽)   │      │              │
        └────────┬────────┘      └──────────────┘
                 │ accept / compose
                 ▼
        ┌─────────────────┐
        │   TinyFrame     │  ← 纯 Python 协议栈
        │ (tinyframe/)    │     状态机解析 + CRC
        └─────────────────┘
```

| 模块 | 行数 | 说明 |
| :-- | --: | :-- |
| `tinyframe/protocol.py`   | 215 | 纯 Python 协议栈（状态机 + ID 分配 + query/tick） |
| `tinyframe/engine.py`     | 170 | Qt 信号/槽包装 `QSerialPort` |
| `chart_widget.py`         | 361 | 双 Y 轴实时曲线（QPainter 自绘） |
| `widgets/business_page.py`| 242 | 业务面板：读设定点 + 心跳 + 曲线 |
| `widgets/debug_page.py`   |  40 | 协议调试页容器 |
| `widgets/frame_log_view.py`| 315 | 帧表格 + TSV 复制 |
| `widgets/frame_sender.py` | 116 | 手动发送器 |
| `widgets/serial_panel.py` | 219 | 串口面板（端口扫描 + 连接控制） |
| `widgets/settings_page.py`|  68 | 设置页 |
| `widgets/about_page.py`   | 363 | 关于页（含帧格式可视化） |
| `config_manager.py`       |  59 | JSON 配置加载 / 保存 |

## 🛠️ 技术栈

| 层 | 技术 | 备注 |
| :-- | :-- | :-- |
| 界面 | PyQt5 5.15 + [qfluentwidgets](https://github.com/zhiyiYo/PyQt-Fluent-Widgets) 1.8 | Fluent 2 风格 |
| 串口 | QtSerialPort | `readyRead` 事件驱动，10 ms tick |
| 协议 | 纯 Python | 0 Qt 依赖，39 unit tests |
| 校验 | crcmod | CRC16 Modbus 预设 |
| 打包 | Nuitka | `--follow-imports`，可选代码签名 |

## 🗺️ Roadmap

- [ ] Linux / macOS 验证（QSerialPort 跨平台，但 dpi / 图标细节需测）
- [ ] CLI 子命令：`tinyframe-host send <type> <hex>` 用于脚本化调试
- [ ] 可配置帧类型映射（YAML 注册表）
- [ ] 波形导出（CSV / PNG）
- [ ] 更多示例：F28377D / STM32 / ESP32 配套 demo 固件仓库

欢迎 Issue / PR 讨论。

## 🤝 贡献

1. Fork 本仓库
2. `git checkout -b feat/your-feature`
3. 提交（请保留 `pytest tests/` 全绿）
4. 发 PR 时附上做了什么 / 为什么

代码风格：无硬性要求，但请尽量保持现有文件风格（双 Y 轴曲线里的中文注释 / `from __future__ import annotations` / type hints）。

## 📝 许可证

[MIT](LICENSE) © [MisakaMikoto128](https://github.com/MisakaMikoto128)

## 🙏 鸣谢

- [MightyPork/TinyFrame](https://github.com/MightyPork/TinyFrame) — 原始 C 版 TinyFrame 协议
- [zhiyiYo/PyQt-Fluent-Widgets](https://github.com/zhiyiYo/PyQt-Fluent-Widgets) — 让 PyQt5 也能写出 Fluent 2 风格 UI
- [crcmod](https://crcmod.sourceforge.net/) — 预设 CRC 算法库

---

<div align="center">
<sub>如果这个项目对你有帮助，欢迎 ⭐ Star。</sub>
</div>
