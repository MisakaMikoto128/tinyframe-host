"""TinyFrame 纯 Python 协议栈。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

import crcmod.predefined

_crc16_modbus_fn = crcmod.predefined.mkPredefinedCrcFun("modbus")


def crc16_modbus(data: bytes) -> int:
    """CRC16 Modbus。空输入返回 0xFFFF（Modbus 初值）。"""
    return _crc16_modbus_fn(data)


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
