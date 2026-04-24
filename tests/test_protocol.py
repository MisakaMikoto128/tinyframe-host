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
