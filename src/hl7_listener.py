"""MLLP-framed HL7 TCP listener for Skyla analyzers."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable

try:
    from .hl7_parser import build_ack
except ImportError:
    from hl7_parser import build_ack

logger = logging.getLogger("vetflow_connect")

# MLLP framing bytes
SB = b"\x0b"  # Start Block
EB = b"\x1c"  # End Block
CR = b"\x0d"  # Carriage Return

MessageCallback = Callable[[str], Awaitable[None]]


class HL7Listener:
    """TCP server accepting MLLP-framed HL7 messages from Skyla analyzers."""

    def __init__(self, device_name: str = ""):
        self.device_name = device_name
        self._server: asyncio.AbstractServer | None = None

    async def start(
        self,
        host: str,
        port: int,
        callback: MessageCallback,
    ) -> asyncio.AbstractServer:
        """Start TCP server listening for MLLP messages.

        Args:
            host: Bind address (e.g., "0.0.0.0").
            port: TCP port to listen on.
            callback: Async function called with each parsed HL7 message string.

        Returns:
            The asyncio Server instance.
        """
        self._server = await asyncio.start_server(
            lambda r, w: self._handle_connection(r, w, callback),
            host,
            port,
        )
        logger.info(
            "[%s] Listening on %s:%d",
            self.device_name or "HL7",
            host,
            port,
        )
        return self._server

    async def _handle_connection(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        callback: MessageCallback,
    ) -> None:
        """Handle a single TCP connection, extracting MLLP-framed messages."""
        peer = writer.get_extra_info("peername")
        logger.info("[%s] Connection from %s", self.device_name, peer)

        buffer = b""
        try:
            while True:
                data = await reader.read(65536)
                if not data:
                    break
                buffer += data

                # Extract complete MLLP messages: <SB>message<EB><CR>
                while SB in buffer and EB in buffer:
                    sb_pos = buffer.index(SB)
                    eb_pos = buffer.index(EB)

                    if eb_pos < sb_pos:
                        # Malformed — discard data before SB
                        buffer = buffer[sb_pos:]
                        continue

                    # Extract message between SB and EB
                    message_bytes = buffer[sb_pos + 1 : eb_pos]
                    # Skip EB + optional CR
                    remaining_start = eb_pos + 1
                    if remaining_start < len(buffer) and buffer[remaining_start : remaining_start + 1] == CR:
                        remaining_start += 1
                    buffer = buffer[remaining_start:]

                    try:
                        message = message_bytes.decode("utf-8")
                    except UnicodeDecodeError:
                        message = message_bytes.decode("latin-1")

                    logger.debug(
                        "[%s] Received message (%d bytes)",
                        self.device_name,
                        len(message_bytes),
                    )

                    # Send ACK response
                    ack = build_ack(message)
                    if ack:
                        writer.write(SB + ack.encode("utf-8") + EB + CR)
                        await writer.drain()
                        logger.debug("[%s] Sent ACK", self.device_name)

                    # Process message
                    try:
                        await callback(message)
                    except Exception:
                        logger.exception(
                            "[%s] Error processing message",
                            self.device_name,
                        )

        except asyncio.CancelledError:
            pass
        except ConnectionResetError:
            logger.info("[%s] Connection reset by %s", self.device_name, peer)
        except Exception:
            logger.exception("[%s] Connection error from %s", self.device_name, peer)
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass
            logger.info("[%s] Connection closed from %s", self.device_name, peer)
