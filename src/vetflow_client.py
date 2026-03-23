"""HTTP client for sending lab results to VetFlow API."""

from __future__ import annotations

import io
import logging

import aiohttp

logger = logging.getLogger("vetflow_connect")


class VetFlowClient:
    """Uploads parsed HL7 results as XML to VetFlow's lab-results/import endpoint."""

    def __init__(self, vetflow_url: str, api_key: str):
        self.url = vetflow_url.rstrip("/")
        self.api_key = api_key

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
