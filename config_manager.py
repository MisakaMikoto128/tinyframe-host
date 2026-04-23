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
            return AppConfig(
                device_name=data.get("device_name", "REG1K0100A2 充电模块"),
                voltage_max=float(data.get("voltage_max", 1000.0)),
                voltage_min=float(data.get("voltage_min", 150.0)),
                current_max=float(data.get("current_max", 100.0)),
                current_min=float(data.get("current_min", 0.0)),
            )
        except Exception:
            return AppConfig()
