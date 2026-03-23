"""Auto-discover Skyla HL7 devices on the local network."""

from __future__ import annotations

import asyncio
import logging
import socket

logger = logging.getLogger("vetflow_connect")

# Default HL7 ports for Skyla devices
DEFAULT_PORTS = [8888, 8889]

# Connection timeout per host
TIMEOUT_SECONDS = 1.0


def _get_local_subnet() -> str | None:
    """Detect local IP and return subnet prefix (e.g., '192.168.1.')."""
    try:
        # Connect to a public DNS to determine local IP (no data sent)
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
        parts = local_ip.split(".")
        if len(parts) == 4:
            return f"{parts[0]}.{parts[1]}.{parts[2]}."
    except Exception:
        logger.warning("Could not detect local subnet")
    return None


async def _check_port(host: str, port: int) -> tuple[str, int] | None:
    """Try connecting to host:port with timeout."""
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
    """Scan local network for open HL7 ports.

    Args:
        ports: List of ports to scan (default: [8888, 8889]).
        subnet: Subnet prefix to scan (e.g., "192.168.1.").
                Auto-detected if not provided.

    Returns:
        List of (host, port) tuples where connections succeeded.
    """
    scan_ports = ports or DEFAULT_PORTS
    scan_subnet = subnet or _get_local_subnet()

    if not scan_subnet:
        logger.warning("Cannot determine local subnet, skipping auto-discover")
        return []

    logger.info("Scanning %s0/24 for HL7 devices on ports %s...", scan_subnet, scan_ports)

    tasks = []
    for i in range(1, 255):
        host = f"{scan_subnet}{i}"
        for port in scan_ports:
            tasks.append(_check_port(host, port))

    # Run all checks concurrently with a semaphore to avoid overwhelming the network
    semaphore = asyncio.Semaphore(50)

    async def limited_check(coro):
        async with semaphore:
            return await coro

    results = await asyncio.gather(*[limited_check(t) for t in tasks])
    found = [r for r in results if r is not None]

    for host, port in found:
        logger.info("Found HL7 device at %s:%d", host, port)

    if not found:
        logger.info("No HL7 devices found on network")

    return found
