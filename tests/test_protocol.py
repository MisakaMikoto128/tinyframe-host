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
