"""Simplified config management for VetFlowConnect."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

DEFAULT_LOG_FILE = "vetflow_connect.log"
DEFAULT_SERVER_URL = "https://vet-flow.pl"
SERVER_CHOICES = [
    ("vet-flow.pl", "https://vet-flow.pl"),
    ("test.vet-flow.pl", "https://test.vet-flow.pl"),
    ("vetflow.gruzalab.pl", "https://vetflow.gruzalab.pl"),
    ("custom", ""),
]


class ConfigNotFoundError(FileNotFoundError):
    """Raised when the local config file is missing."""


def app_dir() -> Path:
    """Return the runtime directory for config/log files."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


DEFAULT_CONFIG_PATH = app_dir() / "config.json"


@dataclass
class Config:
    api_key: str
    url: str
    log_file: str = DEFAULT_LOG_FILE

    @property
    def vetflow_url(self) -> str:
        """Backward-compatible alias for legacy code."""
        return self.url

    def to_dict(self) -> dict:
        return {
            "api_key": self.api_key,
            "url": self.url.rstrip("/"),
            "log_file": self.log_file,
        }


def normalize_url(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("VetFlow URL is required.")
    if "://" not in value:
        value = f"https://{value}"
    return value.rstrip("/")


def load_config(path: Path | None = None) -> Config:
    """Load the local config file."""
    config_path = path or DEFAULT_CONFIG_PATH
    if not config_path.exists():
        raise ConfigNotFoundError(str(config_path))

    raw = json.loads(config_path.read_text(encoding="utf-8"))
    url = raw.get("url") or raw.get("vetflow_url") or DEFAULT_SERVER_URL
    return Config(
        api_key=raw["api_key"].strip(),
        url=normalize_url(url),
        log_file=raw.get("log_file", DEFAULT_LOG_FILE),
    )


def save_config(config: Config, path: Path | None = None) -> Path:
    """Persist config to disk."""
    config_path = path or DEFAULT_CONFIG_PATH
    config_path.write_text(
        json.dumps(config.to_dict(), indent=2) + "\n",
        encoding="utf-8",
    )
    return config_path


def clear_config(path: Path | None = None) -> None:
    """Delete the local config file if present."""
    config_path = path or DEFAULT_CONFIG_PATH
    if config_path.exists():
        config_path.unlink()


def has_config(path: Path | None = None) -> bool:
    return (path or DEFAULT_CONFIG_PATH).exists()
