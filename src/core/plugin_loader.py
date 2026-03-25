"""Dynamic plugin loading for VetFlowConnect."""

from __future__ import annotations

import importlib
import inspect
import logging
import pkgutil
from pathlib import Path

from .keys import VETFLOW_PUBLIC_KEY
from .plugin_manifest import PluginStatus, PluginVerification, is_dev_mode, verify_plugin
from .plugin_base import DevicePlugin

logger = logging.getLogger("vetflow_connect")


def _plugins_package() -> str:
    package = __package__ or ""
    if "." in package:
        root = package.rsplit(".", 1)[0]
        return f"{root}.plugins"
    return "plugins"


class PluginLoader:
    """Find and instantiate DevicePlugin implementations from `plugins/`."""

    def __init__(self, plugins_dir: Path | None = None, *, server_url: str = "", public_key: str = VETFLOW_PUBLIC_KEY) -> None:
        self.plugins_dir = plugins_dir or Path(__file__).resolve().parents[1] / "plugins"
        self.plugins_package = _plugins_package()
        self.server_url = server_url
        self.public_key = public_key
        self.mode = "dev" if is_dev_mode(server_url) else "prod"
        self._verifications: dict[str, PluginVerification] = {}

    def discover(self) -> dict[str, type[DevicePlugin]]:
        """Discover available plugin classes keyed by plugin name."""
        plugin_classes: dict[str, type[DevicePlugin]] = {}
        for module_info in pkgutil.iter_modules([str(self.plugins_dir)]):
            plugin_dir = self.plugins_dir / module_info.name
            verification = verify_plugin(plugin_dir, self.public_key, self.mode)
            self._verifications[module_info.name] = verification
            if not verification.is_load_allowed:
                logger.warning(
                    "Plugin %s blocked by verification: %s",
                    module_info.name,
                    verification.status.value,
                )
                continue

            module_name = f"{self.plugins_package}.{module_info.name}.plugin"
            try:
                module = importlib.import_module(module_name)
            except Exception:
                logger.exception("Failed to import plugin module %s", module_name)
                continue

            for _, obj in inspect.getmembers(module, inspect.isclass):
                if obj is DevicePlugin or not issubclass(obj, DevicePlugin):
                    continue
                if inspect.isabstract(obj):
                    continue
                if not obj.name:
                    logger.warning("Plugin class %s in %s has no name", obj.__name__, module_name)
                    continue
                self._verifications[obj.name] = verification
                plugin_classes[obj.name] = obj
                break
        return plugin_classes

    def instantiate(self, plugin_name: str) -> DevicePlugin:
        """Instantiate a discovered plugin by name."""
        classes = self.discover()
        if plugin_name not in classes:
            available = ", ".join(sorted(classes)) or "none"
            raise KeyError(f"Plugin '{plugin_name}' not found. Available: {available}")
        return classes[plugin_name]()

    def verification_for(self, plugin_name: str) -> PluginVerification:
        return self._verifications.get(plugin_name, PluginVerification(status=PluginStatus.NO_MANIFEST))

    def blocked_plugin_statuses(self) -> list[dict]:
        statuses = []
        for plugin_name, verification in sorted(self._verifications.items()):
            if verification.is_load_allowed:
                continue
            statuses.append(
                {
                    "name": plugin_name,
                    "display_name": _display_name(plugin_name, verification),
                    "healthy": False,
                    "license_status": verification.status.value,
                    "status_text": _status_text(plugin_name, verification),
                }
            )
        return statuses


def _display_name(plugin_name: str, verification: PluginVerification) -> str:
    if verification.manifest is not None and verification.manifest.display_name:
        return verification.manifest.display_name
    return plugin_name.replace("_", " ").title()


def _status_text(plugin_name: str, verification: PluginVerification) -> str:
    display_name = _display_name(plugin_name, verification)
    if verification.status == PluginStatus.INVALID_SIGNATURE:
        return f"Plugin {display_name}: nieprawidlowy podpis"
    if verification.status == PluginStatus.TAMPERED:
        return f"Plugin {display_name}: pliki zostaly zmienione"
    if verification.status == PluginStatus.NO_MANIFEST:
        return f"Plugin {display_name}: brak podpisu"
    return f"Plugin {display_name}: status {verification.status.value}"
