"""Vision-RCP Config — TOML configuration loader."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib  # type: ignore[no-redef]


_DEFAULT_CONFIG = {
    "daemon": {
        "port": 0,
        "host": "127.0.0.1",
        "log_level": "info",
        "data_dir": "~/.vision-rcp",
    },
    "relay": {
        "url": "",
        "token": "",
        "reconnect_delay": 1.0,
        "reconnect_max_delay": 30.0,
        "reconnect_backoff": 2.0,
    },
    "auth": {
        "access_token_ttl": 900,
        "refresh_token_ttl": 604800,
        "max_auth_attempts": 5,
    },
    "rate_limit": {
        "commands_per_minute": 60,
        "burst": 10,
    },
    "processes": {
        "auto_restart": False,
        "max_restarts": 5,
        "health_check_interval": 5.0,
        "log_buffer_size": 10000,
        "stream_buffer_max": 1048576,
    },
    "audit": {
        "enabled": True,
        "max_entries": 100000,
        "retention_days": 30,
    },
    "groups": {},
}


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge override into base."""
    merged = base.copy()
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


class Config:
    """Immutable configuration loaded from TOML."""

    def __init__(self, config_path: str | Path | None = None):
        self._data: dict[str, Any] = _DEFAULT_CONFIG.copy()

        if config_path:
            path = Path(config_path).expanduser().resolve()
            if path.exists():
                with open(path, "rb") as f:
                    file_data = tomllib.load(f)
                self._data = _deep_merge(self._data, file_data)

        # Environment Overrides
        if os.environ.get("RELAY_URL"):
            self._data["relay"]["url"] = os.environ.get("RELAY_URL")
        if os.environ.get("RELAY_TOKEN"):
            self._data["relay"]["token"] = os.environ.get("RELAY_TOKEN")
        if os.environ.get("RELAY_PORT"):
            # If a local port is explicitly provided, reconstruct the local URL
            port = os.environ.get("RELAY_PORT")
            self._data["relay"]["url"] = f"ws://127.0.0.1:{port}"

        # Expand data_dir
        data_dir = self._data["daemon"]["data_dir"]
        self._data["daemon"]["data_dir"] = str(Path(data_dir).expanduser().resolve())

        # Ensure data directory exists
        os.makedirs(self._data["daemon"]["data_dir"], exist_ok=True)

    @property
    def daemon(self) -> dict[str, Any]:
        return self._data["daemon"]

    @property
    def relay(self) -> dict[str, Any]:
        return self._data["relay"]

    @property
    def network(self) -> dict[str, Any]:
        return self._data.get("network", {})

    @property
    def auth(self) -> dict[str, Any]:
        return self._data["auth"]

    @property
    def rate_limit(self) -> dict[str, Any]:
        return self._data["rate_limit"]

    @property
    def processes(self) -> dict[str, Any]:
        return self._data["processes"]

    @property
    def audit(self) -> dict[str, Any]:
        return self._data["audit"]

    @property
    def groups(self) -> dict[str, Any]:
        return self._data.get("groups", {})

    @property
    def data_dir(self) -> Path:
        return Path(self._data["daemon"]["data_dir"])

    def get(self, section: str, key: str, default: Any = None) -> Any:
        return self._data.get(section, {}).get(key, default)
