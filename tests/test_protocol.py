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


def _build_frame(type_: int, id_: int, data: bytes) -> bytes:
    tf = TinyFrame()
    return tf._compose(type_=type_, id_=id_, data=data)


def test_accept_full_frame_triggers_on_any_frame():
    tf = TinyFrame()
    captured = []
    tf.on_any_frame(lambda f: captured.append(f))
    tf.accept(_build_frame(0x02, 0x0000, b"\x10\x04\x00\x00\x00\x01\x00\x00\x00\x02"))
    assert len(captured) == 1
    assert captured[0].type == 0x02
    assert captured[0].id == 0x0000
    assert captured[0].data == b"\x10\x04\x00\x00\x00\x01\x00\x00\x00\x02"
    assert captured[0].direction == "rx"


def test_accept_streamed_byte_by_byte():
    tf = TinyFrame()
    captured = []
    tf.on_any_frame(lambda f: captured.append(f))
    frame = _build_frame(0x03, 0x00AA, b"\x12\x34\x56\x78")
    for b in frame:
        tf.accept(bytes([b]))
    assert len(captured) == 1
    assert captured[0].data == b"\x12\x34\x56\x78"


def test_accept_bad_crc_does_not_trigger():
    tf = TinyFrame()
    captured = []
    tf.on_any_frame(lambda f: captured.append(f))
    frame = _build_frame(0x02, 0, b"\x01")
    # 翻转最后一字节（CRC_HI）
    bad = frame[:-1] + bytes([frame[-1] ^ 0xFF])
    tf.accept(bad)
    assert captured == []


def test_accept_bad_crc_triggers_on_crc_failed():
    tf = TinyFrame()
    failed = []
    tf.on_crc_failed(lambda f: failed.append(f))
    frame = _build_frame(0x02, 0x55, b"\xAA")
    bad = frame[:-1] + bytes([frame[-1] ^ 0x01])
    tf.accept(bad)
    assert len(failed) == 1
    assert failed[0].type == 0x02
    assert failed[0].id == 0x55


def test_accept_len_over_max_resyncs_silently():
    tf = TinyFrame()
    captured = []
    tf.on_any_frame(lambda f: captured.append(f))
    # 构造 LEN=0x00FF（超过 64），随后接正常帧，验证能重同步
    noise = b"\x1B\x00\x00\x00\xFF\x01"  # LEN=255
    tf.accept(noise)
    good = _build_frame(0x02, 0, b"\x42")
    tf.accept(good)
    assert len(captured) == 1
    assert captured[0].data == b"\x42"


def test_accept_leading_garbage_then_frame():
    tf = TinyFrame()
    captured = []
    tf.on_any_frame(lambda f: captured.append(f))
    tf.accept(b"\x00\xFF\x77\x23")  # 垃圾
    tf.accept(_build_frame(0x02, 0, b"\x01"))
    assert len(captured) == 1


def test_accept_payload_containing_sof_byte():
    tf = TinyFrame()
    captured = []
    tf.on_any_frame(lambda f: captured.append(f))
    tf.accept(_build_frame(0x02, 0, b"\x1B\x1B\x1B"))
    assert len(captured) == 1
    assert captured[0].data == b"\x1B\x1B\x1B"


def test_accept_back_to_back_frames():
    tf = TinyFrame()
    captured = []
    tf.on_any_frame(lambda f: captured.append(f))
    buf = _build_frame(0x02, 0, b"\x01") + _build_frame(0x02, 2, b"\x02") + _build_frame(0x02, 4, b"\x03")
    tf.accept(buf)
    assert len(captured) == 3
    assert [f.data for f in captured] == [b"\x01", b"\x02", b"\x03"]


def test_accept_half_frame_then_new_frame():
    tf = TinyFrame()
    captured = []
    tf.on_any_frame(lambda f: captured.append(f))
    frame = _build_frame(0x02, 0, b"\x01\x02\x03")
    # 喂前一半（不完整），再喂污染字节，再喂两个完整新帧。
    # 没有中途 SOF 重同步的简单状态机下，第一个完整新帧的前导字节
    # 可能被"吃"进上半段状态机；第二个完整新帧总能在下一次 IDLE 对齐。
    tf.accept(frame[:5])
    tf.accept(b"\xFF\xFF\xFF")
    tf.accept(_build_frame(0x02, 0, b"\xAB"))
    tf.accept(_build_frame(0x02, 2, b"\xCD"))
    # 至少解出 \xCD 帧（或 \xAB 帧也行）
    payloads = [f.data for f in captured]
    assert b"\xCD" in payloads or b"\xAB" in payloads


def test_on_type_listener_triggered_for_matching_type_only():
    tf = TinyFrame()
    type_02_captured = []
    type_03_captured = []
    tf.on_type(0x02, lambda f: type_02_captured.append(f))
    tf.on_type(0x03, lambda f: type_03_captured.append(f))
    tf.accept(_build_frame(0x02, 0, b"\x0A"))
    tf.accept(_build_frame(0x03, 0, b"\x0B"))
    assert len(type_02_captured) == 1 and type_02_captured[0].data == b"\x0A"
    assert len(type_03_captured) == 1 and type_03_captured[0].data == b"\x0B"


def test_send_writes_composed_frame():
    tf = TinyFrame(is_master=True)
    sent = []
    tf.write_impl = lambda b: sent.append(b)
    tf.send(type_=0x03, data=b"\x12\x34\x56\x78")
    assert len(sent) == 1
    # Send 用 id=0（单向帧）
    expected = tf._compose(type_=0x03, id_=0, data=b"\x12\x34\x56\x78")
    assert sent[0] == expected


def test_send_without_write_impl_raises():
    tf = TinyFrame()
    with pytest.raises(RuntimeError, match="write_impl"):
        tf.send(type_=0x03, data=b"")


def test_query_allocates_even_ids():
    tf = TinyFrame(is_master=True)
    tf.write_impl = lambda b: None
    ids = [tf.query(type_=0x01, data=b"", on_response=lambda f: None,
                    on_timeout=lambda i, t: None, timeout_ms=100)
           for _ in range(5)]
    assert ids == [0, 2, 4, 6, 8]


def test_query_response_triggers_on_response_and_not_on_type():
    tf = TinyFrame(is_master=True)
    tf.write_impl = lambda b: None

    responses = []
    type_any = []
    tf.on_type(0x02, lambda f: type_any.append(f))
    tf.query(type_=0x01, data=b"\x10\x04",
             on_response=lambda f: responses.append(f),
             on_timeout=lambda i, t: None,
             timeout_ms=100)
    # 响应帧：ID=0（上面分配的第一个），TYPE=0x02
    tf.accept(tf._compose(type_=0x02, id_=0, data=b"\xAA\xBB"))
    assert len(responses) == 1
    assert responses[0].data == b"\xAA\xBB"
    # on_type(0x02) 在 ID 命中时仍会触发（规范：ID 监听不屏蔽 type 监听）
    # 如果想改成 ID 命中时跳过 type 分派，这条断言要翻转
    assert len(type_any) == 1


def test_query_response_with_wrong_id_does_not_trigger_on_response():
    tf = TinyFrame(is_master=True)
    tf.write_impl = lambda b: None
    responses = []
    tf.query(type_=0x01, data=b"",
             on_response=lambda f: responses.append(f),
             on_timeout=lambda i, t: None,
             timeout_ms=100)
    tf.accept(tf._compose(type_=0x02, id_=0x99, data=b""))
    assert responses == []


def test_query_id_wraps_around():
    tf = TinyFrame(is_master=True)
    tf.write_impl = lambda b: None
    tf._next_id = 0xFFFC
    ids = [tf.query(type_=0x01, data=b"", on_response=lambda f: None,
                    on_timeout=lambda i, t: None, timeout_ms=100)
           for _ in range(3)]
    assert ids == [0xFFFC, 0xFFFE, 0x0000]
