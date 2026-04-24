"""TinyFrame 协议栈（纯 Python 逻辑 + Qt 引擎包装）。"""
from tinyframe.protocol import TFFrame, TinyFrame, crc16_modbus

__all__ = ["TFFrame", "TinyFrame", "crc16_modbus"]
