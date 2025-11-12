# config_manager.py
# created by Haddon Baker 10/7/25 with assistance from ChatGPT. Refactored from original simulator_gui.py for modularity
"""
ConfigManager: loads config.json and provides runtime settings with defaults.
"""
from pathlib import Path
import json
from typing import Any, Dict

DEFAULTS = {
    "error_stack_max_len": 20,
    "enable_verbose_logging": True,
    "ai_LPF_boxcar_length": 5,
    "poll_buffer_period_ms": 200,
    "socket_timeout_s": 3,
}


class ConfigManager:
    def __init__(self, config_path: str | Path):
        self.config_path = Path(config_path)
        self._raw = {}
        self.runtime_settings = {}
        self.load()

    def load(self) -> None:
        if not self.config_path.exists():
            # create a minimal config if missing (safer than crash)
            self._raw = {"runtime_settings": DEFAULTS}
            return

        with self.config_path.open("r", encoding="utf-8") as f:
            self._raw = json.load(f)
        self._parse_runtime_settings()

    def _parse_runtime_settings(self) -> None:
        r = self._raw.get("runtime_settings", {})
        self.runtime_settings = {
            "error_stack_max_len": max(int(r.get("error_stack_max_len", DEFAULTS["error_stack_max_len"])), 1),
            "enable_verbose_logging": bool(r.get("enable_verbose_logging", DEFAULTS["enable_verbose_logging"])),
            "ai_LPF_boxcar_length": max(int(r.get("ai_LPF_boxcar_length", DEFAULTS["ai_LPF_boxcar_length"])), 1),
            "poll_buffer_period_ms": max(int(r.get("poll_buffer_period_ms", DEFAULTS["poll_buffer_period_ms"])), 1),
            "socket_timeout_s": max(int(r.get("socket_timeout_s", DEFAULTS["socket_timeout_s"])), 0),
        }

    def get(self, key: str, default: Any = None) -> Any:
        return self.runtime_settings.get(key, default)

    @property
    def raw(self) -> Dict:
        return self._raw
