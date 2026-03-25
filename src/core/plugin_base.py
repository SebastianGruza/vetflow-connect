"""Base abstractions for VetFlowConnect device plugins."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Awaitable, Callable

logger = logging.getLogger("vetflow_connect")

VitalsHandler = Callable[["VitalsData"], Awaitable[None]]
LabResultHandler = Callable[["LabResult"], Awaitable[None]]


@dataclass
class VitalsData:
    device_serial: str
    timestamp: str
    measurements: dict


@dataclass
class LabResult:
    device_serial: str
    timestamp: str
    panels: list[dict]
    raw_message: str


class DevicePlugin(ABC):
    """Base class for all device plugins."""

    name: str = ""
    display_name: str = ""
    protocol: str = ""
    device_type: str = ""
    version: str = "1.0.0"

    def __init__(self) -> None:
        self.api_client = None
        self._vitals_handler: VitalsHandler | None = None
        self._lab_result_handler: LabResultHandler | None = None

    def configure(
        self,
        *,
        api_client=None,
        vitals_handler: VitalsHandler | None = None,
        lab_result_handler: LabResultHandler | None = None,
    ) -> None:
        """Attach runtime services to the plugin instance."""
        self.api_client = api_client
        self._vitals_handler = vitals_handler
        self._lab_result_handler = lab_result_handler

    @abstractmethod
    async def start(self, config: dict) -> None:
        """Start listening or connecting to the device."""

    @abstractmethod
    async def stop(self) -> None:
        """Stop the plugin and release resources."""

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the device/plugin is healthy."""

    async def on_vitals(self, data: VitalsData) -> None:
        """Forward vitals to the configured handler if present."""
        if self._vitals_handler is not None:
            await self._vitals_handler(data)

    async def on_lab_result(self, data: LabResult) -> None:
        """Forward lab results to the configured handler if present."""
        if self._lab_result_handler is not None:
            await self._lab_result_handler(data)
