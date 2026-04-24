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
