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
