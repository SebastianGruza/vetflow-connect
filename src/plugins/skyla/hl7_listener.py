"""MLLP-framed HL7 TCP listener for Skyla analyzers."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable

from .hl7_parser import build_ack

logger = logging.getLogger("vetflow_connect")

SB = b"\x0b"
EB = b"\x1c"
CR = b"\x0d"

MessageCallback = Callable[[str], Awaitable[None]]


class HL7Listener:
    """TCP server accepting MLLP-framed HL7 messages."""

    def __init__(self, device_name: str = ""):
        self.device_name = device_name
        self._server: asyncio.AbstractServer | None = None

    async def start(self, host: str, port: int, callback: MessageCallback) -> asyncio.AbstractServer:
        self._server = await asyncio.start_server(
            lambda reader, writer: self._handle_connection(reader, writer, callback),
            host,
            port,
        )
        logger.info("[%s] Listening on %s:%d", self.device_name or "HL7", host, port)
        return self._server

    async def _handle_connection(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        callback: MessageCallback,
    ) -> None:
        peer = writer.get_extra_info("peername")
        logger.info("[%s] Connection from %s", self.device_name, peer)

        buffer = b""
        try:
            while True:
                data = await reader.read(65536)
                if not data:
                    break
                buffer += data

                while SB in buffer and EB in buffer:
                    sb_pos = buffer.index(SB)
                    eb_pos = buffer.index(EB)

                    if eb_pos < sb_pos:
                        buffer = buffer[sb_pos:]
                        continue

                    message_bytes = buffer[sb_pos + 1 : eb_pos]
                    remaining_start = eb_pos + 1
                    if remaining_start < len(buffer) and buffer[remaining_start : remaining_start + 1] == CR:
                        remaining_start += 1
                    buffer = buffer[remaining_start:]

                    try:
                        message = message_bytes.decode("utf-8")
                    except UnicodeDecodeError:
                        message = message_bytes.decode("latin-1")

                    ack = build_ack(message)
                    if ack:
                        writer.write(SB + ack.encode("utf-8") + EB + CR)
                        await writer.drain()

                    try:
                        await callback(message)
                    except Exception:
                        logger.exception("[%s] Error processing message", self.device_name)

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
