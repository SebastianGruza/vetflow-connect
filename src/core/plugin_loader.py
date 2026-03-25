"""Dynamic plugin loading for VetFlowConnect."""

from __future__ import annotations

import importlib
import inspect
import logging
import pkgutil
from pathlib import Path

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

    def __init__(self, plugins_dir: Path | None = None) -> None:
        self.plugins_dir = plugins_dir or Path(__file__).resolve().parents[1] / "plugins"
        self.plugins_package = _plugins_package()

    def discover(self) -> dict[str, type[DevicePlugin]]:
        """Discover available plugin classes keyed by plugin name."""
        plugin_classes: dict[str, type[DevicePlugin]] = {}
        for module_info in pkgutil.iter_modules([str(self.plugins_dir)]):
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
