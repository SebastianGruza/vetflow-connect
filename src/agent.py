"""VetFlowConnect Agent — main entry point.

Listens for HL7 messages from Skyla VM100 + Tutti analyzers
and sends parsed results to VetFlow API.

Usage:
    python -m scripts.vetflow_connect.agent
    python -m scripts.vetflow_connect.agent --config /path/to/config.json
    python -m scripts.vetflow_connect.agent --discover
"""

from __future__ import annotations

VERSION = "0.3.0"

import argparse
import asyncio
import logging
import os
import sys
import threading
from pathlib import Path

try:
    from .auto_discover import discover_devices
    from .config import Config, load_config
    from .hl7_listener import HL7Listener
    from .hl7_parser import HL7Message, parse_hl7
    from .tray import TrayApp
    from .vetflow_client import VetFlowClient
    from .xml_builder import hl7_to_vetflow_xml
except ImportError:
    from auto_discover import discover_devices
    from config import Config, load_config
    from hl7_listener import HL7Listener
    from hl7_parser import HL7Message, parse_hl7
    from tray import TrayApp
    from vetflow_client import VetFlowClient
    from xml_builder import hl7_to_vetflow_xml

logger = logging.getLogger("vetflow_connect")

# Background event loop — stopped on tray quit
_loop: asyncio.AbstractEventLoop | None = None


def setup_logging(config: Config) -> None:
    """Configure logging to file and console."""
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    console.setLevel(logging.INFO)

    # File handler
    file_handler = logging.FileHandler(config.log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)

    root_logger = logging.getLogger("vetflow_connect")
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(console)
    root_logger.addHandler(file_handler)


def _make_callback(
    client: VetFlowClient,
    device_name: str,
    tray: TrayApp | None = None,
):
    """Create message handler callback for a specific device."""

    async def on_message(raw_message: str) -> None:
        # Save raw HL7 for debugging/analysis
        try:
            if getattr(sys, "frozen", False):
                base_dir = os.path.dirname(sys.executable)
            else:
                base_dir = os.path.dirname(os.path.abspath(__file__))
            raw_dir = os.path.join(base_dir, "captured_raw")
            os.makedirs(raw_dir, exist_ok=True)
            from datetime import datetime as dt

            fname = f"hl7_{device_name}_{dt.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(os.path.join(raw_dir, fname), "w", encoding="utf-8") as f:
                f.write(raw_message)
            logger.info("Raw HL7 saved to captured_raw/%s (%d bytes)", fname, len(raw_message))
        except Exception:
            pass

        # Parse HL7
        parsed: HL7Message = parse_hl7(raw_message)

        if not parsed.results:
            logger.warning("[%s] No results in message, skipping", device_name)
            return

        # Build JSON payload for VetFlow API
        results_dict = {
            r.name: {
                "value": r.value,
                "unit": r.unit,
                "reference_range": r.reference_range,
                "flag": r.flag,
            }
            for r in parsed.results
        }

        json_payload = {
            "lab_name": parsed.device or device_name,
            "test_date": str(parsed.timestamp) if parsed.timestamp else None,
            "patient_name": parsed.patient.name if parsed.patient else None,
            "sample_type": parsed.panel_name or "CBC",
            "order_number": parsed.message_id,
            "results_json": results_dict,
        }

        # Send to VetFlow
        lab_result_id = await client.send_result_json(json_payload)

        status = "OK" if lab_result_id else "FAIL"
        patient_name = parsed.patient.name if parsed.patient else "?"
        panel = parsed.panel_name or "?"
        param_count = len(parsed.results)

        logger.info(
            "[%s] %s | %s | %s | %d params → VetFlow %s",
            device_name, parsed.device, patient_name, panel, param_count, status,
        )

        # Tray notification on successful upload
        if tray and lab_result_id:
            tray.notify(
                "Odebrano wyniki",
                f"{patient_name}, {panel}, {param_count} parametrów",
            )

        # Upload captured images if import succeeded
        if lab_result_id:
            try:
                img_dir = Path(base_dir) / "captured_images"
                if img_dir.exists():
                    jpg_files = sorted(img_dir.glob("*.jpg"))
                    if jpg_files:
                        logger.info("[%s] Uploading %d images for lab_result_id=%d", device_name, len(jpg_files), lab_result_id)
                        ok = await client.send_images(lab_result_id, jpg_files)
                        logger.info("[%s] Image upload %s", device_name, "OK" if ok else "FAIL")
            except Exception as e:
                logger.warning("[%s] Image upload error: %s", device_name, e)

    return on_message


async def run_discover() -> None:
    """Run network discovery and print results."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    found = await discover_devices()
    if found:
        print(f"\nFound {len(found)} HL7 device(s):")
        for host, port in found:
            print(f"  {host}:{port}")
    else:
        print("\nNo HL7 devices found on local network.")
        print("Make sure Skyla analyzers are powered on and connected to the network.")


async def run_agent(config: Config, tray: TrayApp | None = None) -> None:
    """Start the VetFlowConnect agent."""
    setup_logging(config)

    logger.info("=" * 60)
    logger.info("VetFlowConnect Agent v%s", VERSION)
    logger.info("VetFlow URL: %s", config.vetflow_url)
    logger.info("Devices: %s", ", ".join(d.name for d in config.devices))
    logger.info("=" * 60)

    client = VetFlowClient(config.vetflow_url, config.api_key)

    # Check API connection
    api_ok = await client.check_connection()
    if not api_ok:
        logger.warning("⚠️ VetFlow API check failed — results will be parsed but NOT uploaded")
        logger.warning("⚠️ Check vetflow_url and api_key in config.json")
        if tray:
            tray.set_status(False, "API niedostępne")
    else:
        if tray:
            tray.set_status(True, "Połączono z API")

    # Auto-discover devices if configured
    device_hosts: dict[int, str] = {}
    if config.auto_discover:
        found = await discover_devices()
        for host, port in found:
            device_hosts[port] = host

    # Start listeners
    servers: list[asyncio.AbstractServer] = []
    for device in config.devices:
        host = device.host
        if host == "auto":
            host = device_hosts.get(device.port, "0.0.0.0")

        listener = HL7Listener(device_name=device.name)
        callback = _make_callback(client, device.name, tray)
        server = await listener.start(host="0.0.0.0", port=device.port, callback=callback)
        servers.append(server)

        if host != "0.0.0.0":
            logger.info("[%s] Device found at %s:%d", device.name, host, device.port)
        else:
            logger.info("[%s] Waiting for connection on port %d", device.name, device.port)

    logger.info("Agent ready. Waiting for HL7 messages...")
    if tray and api_ok:
        tray.set_status(True, "Nasłuchuje")

    # Keep running
    try:
        await asyncio.gather(*[s.serve_forever() for s in servers])
    except asyncio.CancelledError:
        logger.info("Agent shutting down...")
    finally:
        for s in servers:
            s.close()
        logger.info("Agent stopped")


def _stop_loop() -> None:
    """Stop the background asyncio event loop (called from tray quit)."""
    global _loop
    if _loop and _loop.is_running():
        _loop.call_soon_threadsafe(_loop.stop)


def _run_agent_thread(config: Config, tray: TrayApp) -> None:
    """Run the asyncio event loop in a background thread."""
    global _loop
    _loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_loop)
    _loop.create_task(run_agent(config, tray))
    _loop.run_forever()
    _loop.close()


def main() -> None:
    """CLI entry point."""
    try:
        # Windowed app (console=False) has None stdout/stderr on Windows
        if sys.stdout is None:
            sys.stdout = open(os.devnull, "w")  # noqa: SIM115
        if sys.stderr is None:
            sys.stderr = open(os.devnull, "w")  # noqa: SIM115

        parser = argparse.ArgumentParser(
            prog="vetflow-connect",
            description="VetFlowConnect — HL7 agent for Skyla analyzers",
        )
        parser.add_argument("--config", type=Path, default=None)
        parser.add_argument("--discover", action="store_true")
        args = parser.parse_args()

        if args.discover:
            asyncio.run(run_discover())
            return

        config = load_config(args.config)

        # System tray on main thread, asyncio loop in background thread
        tray = TrayApp(on_quit=_stop_loop, log_file=str(config.log_file))

        def on_tray_ready(_icon):
            thread = threading.Thread(
                target=_run_agent_thread,
                args=(config, tray),
                daemon=True,
            )
            thread.start()

        tray.run(setup=on_tray_ready)

    except Exception as e:
        # Show error as message box on Windows (no console available)
        if sys.platform == "win32":
            import ctypes

            ctypes.windll.user32.MessageBoxW(
                0, f"Błąd: {e}", "VetFlowConnect", 0x10,
            )
        else:
            print(f"\n❌ Błąd: {e}")
            import traceback

            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
