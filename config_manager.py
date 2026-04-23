import json
import os
from dataclasses import dataclass, asdict


@dataclass
class AppConfig:
    device_name: str = "REG1K0100A2 充电模块"
    voltage_max: float = 1000.0
    voltage_min: float = 150.0
    current_max: float = 100.0
    current_min: float = 0.0


class ConfigManager:
    def __init__(self, config_path: str = "config.json"):
        self._path = config_path

    def load(self) -> AppConfig:
        if not os.path.exists(self._path):
            default = AppConfig()
            try:
                with open(self._path, 'w', encoding='utf-8') as f:
                    json.dump(asdict(default), f, ensure_ascii=False, indent=2)
            except OSError:
                pass
            return default
        try:
            with open(self._path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            _default = AppConfig()
            return AppConfig(
                device_name=data.get("device_name", _default.device_name),
                voltage_max=float(data.get("voltage_max", _default.voltage_max)),
                voltage_min=float(data.get("voltage_min", _default.voltage_min)),
                current_max=float(data.get("current_max", _default.current_max)),
                current_min=float(data.get("current_min", _default.current_min)),
            )
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            return AppConfig()
