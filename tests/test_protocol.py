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
