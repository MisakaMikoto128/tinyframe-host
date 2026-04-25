# v0.1.0 · First public release 🎉

TinyFrame Host 首个公开版本。把 [MightyPork/TinyFrame](https://github.com/MightyPork/TinyFrame) 协议做成 PyQt5 + Fluent Design 上位机，附带 39 个单元测试、0 Qt 依赖的纯 Python 协议栈、Nuitka 打包脚本。

## ✨ Highlights

- 📈 **双 Y 轴实时曲线** — QPainter 自绘，60 s 滑动窗口，150 ms push 节拍
- 🔁 **请求 / 响应配对** — MASTER 偶数 ID 自增，回调 + 超时一套搞定
- 💓 **心跳定时器** — 500 / 1000 / 2000 ms 可切，`0x03` 帧 BE 时钟
- 🔌 **串口热插拔** — 200 ms diff 扫描，掉线自动恢复
- 📋 **帧表格 + TSV 复制** — Ctrl+C / 右键，直接贴 Excel
- 💾 **配置持久化** — 波特率 / 校验位 / 端口 / 轮询周期 自动存
- 🎨 **Fluent 2 风格** — qfluentwidgets 1.8，跟随系统深色浅色
- 🧪 **39 个单元测试** — 纯 Python 协议栈，不需要 Qt 环境

## 📦 模块组成

| 模块 | 行数 | 说明 |
| :-- | --: | :-- |
| `tinyframe/protocol.py`    | 215 | 状态机 + ID 分配 + query/tick |
| `tinyframe/engine.py`      | 170 | Qt 信号/槽包装 QSerialPort |
| `chart_widget.py`          | 361 | 双 Y 轴实时曲线 |
| `widgets/business_page.py` | 242 | 业务面板：读设定点 + 心跳 + 曲线 |
| `widgets/frame_log_view.py`| 315 | 帧表格 + TSV 复制 |
| `widgets/about_page.py`    | 363 | 关于页（帧格式可视化） |
| 其它 widgets               | ~500 | 协议调试、串口面板、设置、手动发送器 |

## 🚀 快速开始

```bash
git clone https://github.com/MisakaMikoto128/tinyframe-host.git
cd tinyframe-host
start.bat                      # 自动建 venv + 装依赖 + 启动
# 或手动：pip install -r requirements.txt && python main.py
```

运行测试：

```bash
pytest tests/ -v
# 39 passed in ~0.2s
```

打 exe：

```bash
python build.py                # 文件夹模式
python build.py onefile        # 单文件模式
```

## 🧩 TinyFrame 协议回顾

```
SOF(1) · ID(2,BE) · LEN(2,BE) · TYPE(1) · DATA(≤64B) · CRC16(2,LE, Modbus)
```

- 固定开销 **8 字节** · payload 上限 **64 字节**
- 默认 type：`0x01` READ_REQ / `0x02` READ_RSP / `0x03` HEARTBEAT
- 基于原作 [MightyPork/TinyFrame](https://github.com/MightyPork/TinyFrame) 的纯 Python 重写，协议兼容

## 🗺️ 下一步计划

- [ ] Linux / macOS 验证
- [ ] CLI 子命令，脚本化调试
- [ ] 可配置帧类型映射（YAML）
- [ ] 波形导出 CSV / PNG
- [ ] 配套下位机 demo（F28377D / STM32 / ESP32）

---

## 🙏 鸣谢

- [MightyPork/TinyFrame](https://github.com/MightyPork/TinyFrame)
- [zhiyiYo/PyQt-Fluent-Widgets](https://github.com/zhiyiYo/PyQt-Fluent-Widgets)
- [crcmod](https://crcmod.sourceforge.net/)

欢迎 Issue / PR。如果这个项目对你有帮助，star 一下让更多人看到 ⭐️
