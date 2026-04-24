"""ConfigManager / AppConfig 单元测试（TinyFrame 上位机版）。"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_load_creates_default_file_when_missing(tmp_path):
    from config_manager import AppConfig, ConfigManager

    cfg_path = tmp_path / "config.json"
    mgr = ConfigManager(config_path=str(cfg_path))
    result = mgr.load()

    assert isinstance(result, AppConfig)
    assert result.device_name == "TinyFrame 上位机"
    assert result.default_port == ""
    assert result.default_baud == 115200
    assert result.default_timeout_ms == 200
    assert result.default_poll_ms == 500
    assert result.default_heartbeat_ms == 1000
    assert result.chart_volt_max == 1000.0
    assert result.chart_curr_max == 200.0
    assert cfg_path.exists()


def test_load_reads_existing_file(tmp_path):
    from config_manager import ConfigManager

    cfg_path = tmp_path / "config.json"
    data = {
        "device_name": "测试设备",
        "default_port": "COM3",
        "default_baud": 460800,
        "default_timeout_ms": 150,
        "default_poll_ms": 250,
        "default_heartbeat_ms": 500,
        "chart_volt_max": 48.0,
        "chart_curr_max": 10.0,
    }
    cfg_path.write_text(json.dumps(data), encoding="utf-8")
    mgr = ConfigManager(config_path=str(cfg_path))
    result = mgr.load()

    assert result.device_name == "测试设备"
    assert result.default_port == "COM3"
    assert result.default_baud == 460800
    assert result.default_timeout_ms == 150
    assert result.chart_volt_max == 48.0


def test_load_returns_defaults_on_corrupt_file(tmp_path):
    from config_manager import ConfigManager

    cfg_path = tmp_path / "config.json"
    cfg_path.write_text("not valid json", encoding="utf-8")
    mgr = ConfigManager(config_path=str(cfg_path))
    result = mgr.load()

    assert result.device_name == "TinyFrame 上位机"
    assert result.default_baud == 115200


def test_save_writes_all_fields(tmp_path):
    from config_manager import AppConfig, ConfigManager

    cfg_path = tmp_path / "config.json"
    mgr = ConfigManager(config_path=str(cfg_path))
    cfg = AppConfig(
        device_name="写测试",
        default_port="COM5",
        default_baud=230400,
        default_timeout_ms=300,
    )
    mgr.save(cfg)

    with open(cfg_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["device_name"] == "写测试"
    assert data["default_port"] == "COM5"
    assert data["default_baud"] == 230400
    assert data["default_timeout_ms"] == 300
    # 未设置的字段保留 dataclass 默认
    assert data["default_poll_ms"] == 500
