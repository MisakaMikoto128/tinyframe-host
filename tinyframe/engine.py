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

_FATAL_ERRORS = {
    QSerialPort.DeviceNotFoundError,
    QSerialPort.PermissionError,
    QSerialPort.OpenError,
    QSerialPort.NotOpenError,
    QSerialPort.ResourceError,
    QSerialPort.WriteError,
    QSerialPort.ReadError,
}


class TinyFrameEngine(QObject):
    connected = pyqtSignal(str, int)       # port_name, baud_rate
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
            self.connected.emit(port_name, baud)
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
        # 若 write() 失败或被部分写入（串口掉线 / 缓冲区满），不发 rawBytesOut / frameSent，
        # 避免 UI 侧显示"已发送"但实际没上线的假象。真正的 error 会由 errorOccurred 信号送达。
        #
        # 关于同步 readyRead 重入：loopback / 虚拟串口可能在 write() 返回前同步触发 readyRead，
        # 导致 _on_ready_read → _tf.accept → _dispatch 在 write 栈内执行。这是安全的，因为
        # TinyFrame.query 会先把 (id, on_response, ...) 写入 _pending 再调 write_impl —— 响应
        # 匹配仍能找到监听器。此行为已经过 protocol 单元测试间接覆盖。
        n = self._serial.write(data)
        if n != len(data):
            return
        self.rawBytesOut.emit(data)
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

    def _on_error(self, err: "QSerialPort.SerialPortError") -> None:
        if err == QSerialPort.NoError:
            return
        if err not in _FATAL_ERRORS:
            # 非致命 error（比如 TimeoutError, UnsupportedOperationError）—— 不关闭串口
            return
        # M6: 先捕获 errorString 再 close，防止 close() 清空它
        reason = self._serial.errorString()
        if self._serial.isOpen():
            self._serial.close()
        self.disconnected.emit(reason)
