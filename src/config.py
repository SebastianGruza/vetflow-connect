"""Configuration loader for VetFlowConnect."""

from __future__ import annotations

import json
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger("vetflow_connect")

def _exe_dir() -> Path:
    """Return directory of the .exe (frozen) or script directory (dev)."""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).parent

DEFAULT_CONFIG_PATH = _exe_dir() / "config.json"


@dataclass
class DeviceConfig:
    name: str
    host: str
    port: int
    type: str  # "cbc" or "chemistry"


@dataclass
class Config:
    vetflow_url: str
    api_key: str
    devices: list[DeviceConfig] = field(default_factory=list)
    auto_discover: bool = True
    log_file: str = "vetflow_connect.log"


def load_config(path: Path | None = None) -> Config:
    """Load config from JSON file."""
    config_path = path or DEFAULT_CONFIG_PATH
    if not config_path.exists():
        print(f"\n❌ Config file not found: {config_path}")
        print("Copy config.json.example to config.json and fill in your API key.")
        print("\nExpected location: same folder as VetFlowConnect.exe")
        input("\nNaciśnij Enter żeby zamknąć...")
        sys.exit(1)

    with open(config_path) as f:
        raw = json.load(f)

    devices = [
        DeviceConfig(
            name=d["name"],
            host=d.get("host", "auto"),
            port=d["port"],
            type=d["type"],
        )
        for d in raw.get("devices", [])
    ]

    return Config(
        vetflow_url=raw["vetflow_url"].rstrip("/"),
        api_key=raw["api_key"],
        devices=devices,
        auto_discover=raw.get("auto_discover", True),
        log_file=raw.get("log_file", "vetflow_connect.log"),
    )
