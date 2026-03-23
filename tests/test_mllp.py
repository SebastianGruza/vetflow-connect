"""Tests for MLLP framing and HL7 listener."""

import asyncio

import pytest

from scripts.vetflow_connect.hl7_listener import CR, EB, HL7Listener, SB
from scripts.vetflow_connect.hl7_parser import parse_hl7

from .mock_messages import TUTTI_CHEMISTRY, VM100_CBC


@pytest.fixture
def listener():
    return HL7Listener(device_name="Test")


def _frame_mllp(message: str) -> bytes:
    """Wrap HL7 message in MLLP framing."""
    return SB + message.encode("utf-8") + EB + CR


class TestMLLPFraming:
    """Test MLLP message framing."""

    def test_framing_constants(self):
        assert SB == b"\x0b"
        assert EB == b"\x1c"
        assert CR == b"\x0d"

    def test_frame_vm100(self):
        framed = _frame_mllp(VM100_CBC)
        assert framed.startswith(SB)
        assert framed.endswith(EB + CR)
        # Extract message back
        content = framed[1:-2].decode("utf-8")
        assert content == VM100_CBC

    def test_frame_tutti(self):
        framed = _frame_mllp(TUTTI_CHEMISTRY)
        content = framed[1:-2].decode("utf-8")
        msg = parse_hl7(content)
        assert msg.device == "Tutti"


class TestHL7ListenerIntegration:
    """Integration tests for HL7 TCP listener."""

    @pytest.mark.asyncio
    async def test_receive_vm100_message(self, listener):
        """Test receiving a VM100 CBC message via TCP."""
        received = []

        async def callback(message: str):
            received.append(message)

        server = await listener.start("127.0.0.1", 0, callback)
        port = server.sockets[0].getsockname()[1]

        try:
            reader, writer = await asyncio.open_connection("127.0.0.1", port)
            writer.write(_frame_mllp(VM100_CBC))
            await writer.drain()

            # Read ACK
            ack_data = await asyncio.wait_for(reader.read(4096), timeout=2.0)
            assert SB in ack_data
            assert b"ACK^R01" in ack_data

            writer.close()
            await writer.wait_closed()

            # Wait for callback
            await asyncio.sleep(0.1)
        finally:
            server.close()
            await server.wait_closed()

        assert len(received) == 1
        msg = parse_hl7(received[0])
        assert msg.device == "VM100"
        assert msg.patient.name == "Nelly"

    @pytest.mark.asyncio
    async def test_receive_tutti_message(self, listener):
        """Test receiving a Tutti Chemistry message via TCP."""
        received = []

        async def callback(message: str):
            received.append(message)

        server = await listener.start("127.0.0.1", 0, callback)
        port = server.sockets[0].getsockname()[1]

        try:
            reader, writer = await asyncio.open_connection("127.0.0.1", port)
            writer.write(_frame_mllp(TUTTI_CHEMISTRY))
            await writer.drain()

            # Read ACK
            ack_data = await asyncio.wait_for(reader.read(4096), timeout=2.0)
            assert b"ACK^R01" in ack_data

            writer.close()
            await writer.wait_closed()
            await asyncio.sleep(0.1)
        finally:
            server.close()
            await server.wait_closed()

        assert len(received) == 1
        msg = parse_hl7(received[0])
        assert msg.device == "Tutti"
        assert msg.patient.name == "Mruczka"

    @pytest.mark.asyncio
    async def test_multiple_messages_same_connection(self, listener):
        """Test receiving multiple MLLP messages on one connection."""
        received = []

        async def callback(message: str):
            received.append(message)

        server = await listener.start("127.0.0.1", 0, callback)
        port = server.sockets[0].getsockname()[1]

        try:
            reader, writer = await asyncio.open_connection("127.0.0.1", port)

            # Send two messages
            writer.write(_frame_mllp(VM100_CBC))
            writer.write(_frame_mllp(TUTTI_CHEMISTRY))
            await writer.drain()

            # Read ACKs
            ack_data = b""
            while ack_data.count(b"ACK^R01") < 2:
                chunk = await asyncio.wait_for(reader.read(4096), timeout=2.0)
                if not chunk:
                    break
                ack_data += chunk

            writer.close()
            await writer.wait_closed()
            await asyncio.sleep(0.1)
        finally:
            server.close()
            await server.wait_closed()

        assert len(received) == 2
