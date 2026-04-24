"""TinyFrame 纯 Python 协议栈。"""
from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Callable, Optional

import crcmod.predefined

_crc16_modbus_fn = crcmod.predefined.mkPredefinedCrcFun("modbus")


def crc16_modbus(data: bytes) -> int:
    """CRC16 Modbus。空输入返回 0xFFFF（Modbus 初值）。"""
    return _crc16_modbus_fn(data)


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

        # 写出回调（engine 侧注入）
        self.write_impl: Optional[Callable[[bytes], None]] = None

        # ID 分配（MASTER 偶数自增）
        self._next_id = 0
        # 挂起的 query：{id: (on_response, on_timeout, remaining_ms, type_)}
        self._pending: dict[int, tuple] = {}

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
        pending = self._pending.pop(frame.id, None)
        if pending is not None:
            on_resp, _on_to, _remaining, _type = pending
            on_resp(frame)
        for cb in self._type_listeners.get(frame.type, []):
            cb(frame)
        for cb in self._any_listeners:
            cb(frame)

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

    def send(self, type_: int, data: bytes) -> None:
        if self.write_impl is None:
            raise RuntimeError("write_impl 未设置，无法发送")
        frame = self._compose(type_=type_, id_=0, data=data)
        self.write_impl(frame)

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
