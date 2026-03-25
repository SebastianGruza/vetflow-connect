"""Auto-discovery for HL7-capable analyzers on the local network."""

from __future__ import annotations

import asyncio
import logging
import socket

logger = logging.getLogger("vetflow_connect")

DEFAULT_PORTS = [8888, 8889, 12221]
TIMEOUT_SECONDS = 1.0


def _get_local_subnet() -> str | None:
    """Detect local IP and return subnet prefix."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            local_ip = sock.getsockname()[0]
        parts = local_ip.split(".")
        if len(parts) == 4:
            return f"{parts[0]}.{parts[1]}.{parts[2]}."
    except Exception:
        logger.warning("Could not detect local subnet")
    return None


async def _check_port(host: str, port: int) -> tuple[str, int] | None:
    try:
        _, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=TIMEOUT_SECONDS,
        )
        writer.close()
        await writer.wait_closed()
        return (host, port)
    except (asyncio.TimeoutError, OSError):
        return None


async def discover_devices(
    ports: list[int] | None = None,
    subnet: str | None = None,
) -> list[tuple[str, int]]:
    """Scan the local subnet for open device ports."""
    scan_ports = ports or DEFAULT_PORTS
    scan_subnet = subnet or _get_local_subnet()

    if not scan_subnet:
        logger.warning("Cannot determine local subnet, skipping auto-discover")
        return []

    logger.info("Scanning %s0/24 for device ports %s...", scan_subnet, scan_ports)

    semaphore = asyncio.Semaphore(50)

    async def limited_check(host: str, port: int) -> tuple[str, int] | None:
        async with semaphore:
            return await _check_port(host, port)

    tasks = [
        limited_check(f"{scan_subnet}{index}", port)
        for index in range(1, 255)
        for port in scan_ports
    ]
    results = await asyncio.gather(*tasks)
    found = [item for item in results if item is not None]

    for host, port in found:
        logger.info("Found device at %s:%d", host, port)

    if not found:
        logger.info("No devices found on network")

    return found
