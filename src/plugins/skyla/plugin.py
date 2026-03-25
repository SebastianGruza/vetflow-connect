"""Skyla plugin implementation."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

try:
    from ...core.config import app_dir
    from ...core.plugin_base import DevicePlugin, LabResult
except ImportError:
    from core.config import app_dir
    from core.plugin_base import DevicePlugin, LabResult
from .hl7_listener import HL7Listener
from .hl7_parser import HL7Message, parse_hl7

logger = logging.getLogger("vetflow_connect")


class SkylaPlugin(DevicePlugin):
    """Plugin for Skyla HL7 analyzers."""

    name = "skyla"
    display_name = "Skyla Analyzer"
    protocol = "hl7"
    device_type = "lab_analyzer"
    version = "1.0.0"

    def __init__(self) -> None:
        super().__init__()
        self._server = None
        self._listener: HL7Listener | None = None
        self._device_config: dict = {}

    async def start(self, config: dict) -> None:
        self._device_config = config
        device_name = config.get("name", self.display_name)
        port = int(config.get("port", 12221))

        self._listener = HL7Listener(device_name=device_name)
        self._server = await self._listener.start(
            host="0.0.0.0",
            port=port,
            callback=self._handle_message,
        )
        logger.info("[%s] Skyla plugin listening on port %d", device_name, port)

    async def stop(self) -> None:
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
        logger.info("[%s] Skyla plugin stopped", self._device_config.get("name", self.display_name))

    async def health_check(self) -> bool:
        return self._server is not None and self._server.sockets is not None

    async def _handle_message(self, raw_message: str) -> None:
        self._capture_raw(raw_message)
        parsed = parse_hl7(raw_message)
        if not parsed.results:
            logger.warning("[%s] No results in message, skipping", self._device_config.get("name", self.display_name))
            return

        panels = [self._build_panel_payload(parsed)]
        data = LabResult(
            device_serial=self._device_config.get("serial", parsed.device or self.name),
            timestamp=str(parsed.timestamp or ""),
            panels=panels,
            raw_message=raw_message,
        )
        await self.on_lab_result(data)

    async def on_lab_result(self, data: LabResult) -> None:
        if self.api_client is None:
            logger.warning("[%s] No API client configured, dropping result", self._device_config.get("name", self.display_name))
            await super().on_lab_result(data)
            return

        panel = data.panels[0] if data.panels else {}
        lab_result_id = await self.api_client.send_lab_result(panel)
        if lab_result_id is None:
            lab_result_id = await self.api_client.send_result_json(panel)

        status = "OK" if lab_result_id else "FAIL"
        logger.info(
            "[%s] %s | %s | %s | %d params -> VetFlow %s",
            self._device_config.get("name", self.display_name),
            panel.get("lab_name", self.display_name),
            panel.get("patient_name") or "?",
            panel.get("sample_type") or "?",
            len(panel.get("results_json", {})),
            status,
        )

        if lab_result_id:
            await self._upload_images(lab_result_id)

        await super().on_lab_result(data)

    def _build_panel_payload(self, parsed: HL7Message) -> dict:
        results_dict = {
            result.name: {
                "value": result.value,
                "unit": result.unit,
                "reference_range": result.reference_range,
                "flag": result.flag,
            }
            for result in parsed.results
        }
        return {
            "device_plugin": self.name,
            "device_name": self._device_config.get("name", self.display_name),
            "device_type": self.device_type,
            "lab_name": parsed.device or self._device_config.get("name", self.display_name),
            "test_date": str(parsed.timestamp) if parsed.timestamp else None,
            "patient_name": parsed.patient.name if parsed.patient else None,
            "patient_id": parsed.patient.patient_id if parsed.patient else None,
            "sample_type": parsed.panel_name or "CBC",
            "order_number": parsed.message_id,
            "results_json": results_dict,
        }

    def _capture_raw(self, raw_message: str) -> None:
        try:
            raw_dir = app_dir() / "captured_raw"
            raw_dir.mkdir(exist_ok=True)
            filename = f"hl7_{self._device_config.get('name', self.name)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            (raw_dir / filename).write_text(raw_message, encoding="utf-8")
        except Exception:
            logger.debug("Failed to persist raw HL7 payload", exc_info=True)

    async def _upload_images(self, lab_result_id: int) -> None:
        image_dir = Path(app_dir()) / "captured_images"
        if not image_dir.exists():
            return

        jpg_files = sorted(image_dir.glob("*.jpg"))
        if not jpg_files:
            return

        logger.info(
            "[%s] Uploading %d images for lab_result_id=%d",
            self._device_config.get("name", self.display_name),
            len(jpg_files),
            lab_result_id,
        )
        ok = await self.api_client.send_images(lab_result_id, jpg_files)
        logger.info("[%s] Image upload %s", self._device_config.get("name", self.display_name), "OK" if ok else "FAIL")
