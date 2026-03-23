"""HTTP client for sending lab results to VetFlow API."""

from __future__ import annotations

import io
import logging
from pathlib import Path

import aiohttp

logger = logging.getLogger("vetflow_connect")


class VetFlowClient:
    """Uploads parsed HL7 results as XML to VetFlow's lab-results/import endpoint."""

    def __init__(self, vetflow_url: str, api_key: str):
        self.url = vetflow_url.rstrip("/")
        self.api_key = api_key

    async def check_connection(self) -> bool:
        """Verify API key is valid and VetFlow is reachable.

        Returns:
            True if API key is accepted, False otherwise.
        """
        endpoint = f"{self.url}/api/clinic/lab-results/import-json-external"

        try:
            async with aiohttp.ClientSession() as session:
                # Send empty ping — server will reject with 422 (validation error)
                # but that means auth passed. 401 = bad key, connection error = unreachable.
                async with session.post(
                    endpoint,
                    json={},
                    headers={"X-Clinic-API-Key": self.api_key},
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status == 401:
                        logger.error("❌ API key rejected — check your api_key in config.json")
                        return False
                    elif resp.status in (200, 422):
                        logger.info("✅ API connection OK — VetFlow is reachable, key is valid")
                        return True
                    else:
                        logger.warning("⚠️ Unexpected response %d — VetFlow reachable but check config", resp.status)
                        return True  # reachable at least
        except aiohttp.ClientError as exc:
            logger.error("❌ Cannot reach VetFlow at %s: %s", self.url, exc)
            return False

    async def send_result_json(self, parsed_data: dict) -> int | None:
        """Send parsed HL7 result as JSON to VetFlow API (new endpoint).

        Args:
            parsed_data: Dict with keys matching LabResultJsonImport schema.

        Returns:
            The lab_result_id on success, None on failure.
        """
        endpoint = f"{self.url}/api/clinic/lab-results/import-json-external"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    endpoint,
                    json=parsed_data,
                    headers={"X-Clinic-API-Key": self.api_key},
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as resp:
                    if resp.status in (200, 201):
                        body = await resp.json()
                        logger.info("Imported to VetFlow: %s", body)
                        return body.get("id")
                    else:
                        text = await resp.text()
                        logger.error("VetFlow API error %d: %s", resp.status, text[:500])
                        return None
        except aiohttp.ClientError as exc:
            logger.error("VetFlow connection error: %s", exc)
            return None

    async def send_images(self, lab_result_id: int, image_paths: list[Path]) -> bool:
        """Upload JPEG images to VetFlow for a lab result.

        Args:
            lab_result_id: ID of the lab result to attach images to.
            image_paths: List of paths to JPEG files.

        Returns:
            True if upload succeeded, False otherwise.
        """
        endpoint = f"{self.url}/api/clinic/lab-results/{lab_result_id}/images"

        try:
            data = aiohttp.FormData()
            for path in image_paths:
                data.add_field(
                    "files",
                    open(path, "rb"),
                    filename=path.name,
                    content_type="image/jpeg",
                )

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    endpoint,
                    data=data,
                    headers={"X-Clinic-API-Key": self.api_key},
                    timeout=aiohttp.ClientTimeout(total=60),
                ) as resp:
                    if resp.status == 200:
                        body = await resp.json()
                        logger.info("Uploaded %d images to VetFlow: %s", body.get("uploaded", 0), body.get("paths", []))
                        return True
                    else:
                        text = await resp.text()
                        logger.error("VetFlow image upload error %d: %s", resp.status, text[:500])
                        return False
        except aiohttp.ClientError as exc:
            logger.error("VetFlow image upload connection error: %s", exc)
            return False

    async def send_result(self, xml_content: str, filename: str = "hl7_result.xml") -> bool:
        """Upload XML lab result to VetFlow.

        The existing /api/clinic/lab-results/import endpoint expects
        multipart/form-data with an XML file upload.

        Args:
            xml_content: XML string in VetFlow <wynik> format.
            filename: Name for the uploaded file.

        Returns:
            True if import succeeded (HTTP 200), False otherwise.
        """
        endpoint = f"{self.url}/api/clinic/lab-results/import"

        data = aiohttp.FormData()
        data.add_field(
            "file",
            io.BytesIO(xml_content.encode("utf-8")),
            filename=filename,
            content_type="application/xml",
        )

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    endpoint,
                    data=data,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as resp:
                    if resp.status == 200:
                        body = await resp.json()
                        matched = body.get("matched_animal_id")
                        imported = body.get("imported", {})
                        logger.info(
                            "Imported to VetFlow: id=%s, animal=%s, order=%s",
                            imported.get("id"),
                            matched,
                            imported.get("order_number"),
                        )
                        return True
                    else:
                        text = await resp.text()
                        logger.error(
                            "VetFlow API error %d: %s",
                            resp.status,
                            text[:500],
                        )
                        return False
        except aiohttp.ClientError as exc:
            logger.error("VetFlow connection error: %s", exc)
            return False
