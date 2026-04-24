import json
import os
from dataclasses import dataclass, asdict


@dataclass
class AppConfig:
    device_name: str = "TinyFrame 上位机"
    default_port: str = ""
    default_baud: int = 115200
    default_timeout_ms: int = 200
    default_poll_ms: int = 500
    default_heartbeat_ms: int = 1000
    chart_volt_max: float = 1000.0
    chart_curr_max: float = 200.0


class ConfigManager:
    def __init__(self, config_path: str = "config.json"):
        self._path = config_path

    def load(self) -> AppConfig:
        if not os.path.exists(self._path):
            default = AppConfig()
            self.save(default)
            return default
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                data = json.load(f)
            d = AppConfig()
            return AppConfig(
                device_name=data.get("device_name", d.device_name),
                default_port=str(data.get("default_port", d.default_port)),
                default_baud=int(data.get("default_baud", d.default_baud)),
                default_timeout_ms=int(data.get("default_timeout_ms", d.default_timeout_ms)),
                default_poll_ms=int(data.get("default_poll_ms", d.default_poll_ms)),
                default_heartbeat_ms=int(data.get("default_heartbeat_ms", d.default_heartbeat_ms)),
                chart_volt_max=float(data.get("chart_volt_max", d.chart_volt_max)),
                chart_curr_max=float(data.get("chart_curr_max", d.chart_curr_max)),
            )
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            return AppConfig()

    def save(self, cfg: AppConfig) -> None:
        try:
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(asdict(cfg), f, ensure_ascii=False, indent=2)
        except OSError:
            pass
