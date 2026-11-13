"""USB serial telemetry receiver for a physically connected ESP32.

The ESP32 sends JSON through USB CDC/UART; no HTTP POST, API token, GPIO
access or actuator executor is involved. Packets are stored as a separate
telemetry archive and cannot trigger calibration-dependent automations.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import datetime, timezone
from time import monotonic
from typing import Callable, Mapping
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.esp32_telemetry import Esp32Telemetry
from app.models.system import AquaponicsSystem
from app.schemas.esp32_telemetry import Esp32SensorPacket
from app.services.esp32_sensor_bridge import build_sensor_readings
from app.services.alert_service import process_sensor_reading

logger = logging.getLogger(__name__)

# Only explicit Linux serial devices, not arbitrary files or network sockets.
SERIAL_PORT_PATTERN = re.compile(
    r"^/dev/(?:tty(?:USB|ACM)[0-9]+|serial/by-(?:id|path)/[A-Za-z0-9_.:-]+)$"
)
MAX_PACKET_BYTES = 8192


class SerialJsonFramer:
    """Find complete JSON objects in a byte stream (compact OR pretty JSON).

    Ignores unrelated ESP32 boot/debug text. Handles USB read fragmentation and
    multiple packets in one chunk. Bounded buffer prevents untrusted serial data
    from exhausting memory.
    """

    def __init__(self, max_bytes: int = MAX_PACKET_BYTES) -> None:
        self.max_bytes = max_bytes
        self._reset()

    def _reset(self) -> None:
        self._buffer = bytearray()
        self._depth = 0
        self._quoted = False
        self._escaped = False

    def feed(self, chunk: bytes) -> list[dict]:
        documents: list[dict] = []
        for byte in chunk:
            if not self._buffer:
                if byte == ord("{"):
                    self._buffer.append(byte)
                    self._depth = 1
                continue

            self._buffer.append(byte)
            if len(self._buffer) > self.max_bytes:
                self._reset()
                continue

            if self._quoted:
                if self._escaped:
                    self._escaped = False
                elif byte == ord("\\"):
                    self._escaped = True
                elif byte == ord('"'):
                    self._quoted = False
                continue

            if byte == ord('"'):
                self._quoted = True
            elif byte == ord("{"):
                self._depth += 1
            elif byte == ord("}"):
                self._depth -= 1
                if self._depth == 0:
                    raw = bytes(self._buffer)
                    self._reset()
                    try:
                        data = json.loads(raw.decode("utf-8"))
                    except (UnicodeDecodeError, json.JSONDecodeError):
                        continue
                    if isinstance(data, dict):
                        documents.append(data)
        return documents


async def persist_esp32_packet(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    system_id: UUID,
    expected_device_id: str,
    packet: Esp32SensorPacket,
    sensor_mapping: Mapping[str, UUID] | None = None,
) -> str:
    """Atomically store packet, opt-in mapped readings, and threshold alerts.

    Retries cannot create additional readings for an archived packet identity.
    No sensor-triggered actuator automation runs from ESP32 ingestion.
    Returns 'created', 'duplicate', 'conflict', or 'unavailable'.
    """
    if packet.device_id != expected_device_id:
        return "conflict"

    # Preserve the wire format as sent. New optional diagnostic fields should
    # not be fabricated as null in legacy packets (or break retry deduplication).
    contents = packet.model_dump(mode="json", exclude_unset=True)
    identity = (
        Esp32Telemetry.system_id == system_id,
        Esp32Telemetry.device_id == packet.device_id,
        Esp32Telemetry.sequence == packet.sequence,
        Esp32Telemetry.uptime_ms == packet.uptime_ms,
    )

    async with session_factory() as session:
        parent = await session.get(AquaponicsSystem, system_id)
        if parent is None or parent.deleted_at is not None:
            return "unavailable"

        row = (
            await session.execute(select(Esp32Telemetry).where(*identity))
        ).scalar_one_or_none()
        if row is not None:
            return "duplicate" if row.packet == contents else "conflict"

        received_at = datetime.now(timezone.utc)
        session.add(Esp32Telemetry(
            system_id=system_id,
            device_id=packet.device_id,
            sequence=packet.sequence,
            uptime_ms=packet.uptime_ms,
            packet=contents,
            received_at=received_at,
        ))

        try:
            # Uniqueness is checked before deriving any readings. The
            # packet/reading/alert changes are committed together.
            await session.flush()

            if sensor_mapping:
                readings = await build_sensor_readings(
                    session,
                    system_id=system_id,
                    packet=packet,
                    sensor_mapping=sensor_mapping,
                    received_at=received_at,
                )
                session.add_all(readings)
                await session.flush()

                for reading in readings:
                    await process_sensor_reading(
                        session,
                        reading,
                        commit=False,
                    )

            await session.commit()
            return "created"
        except IntegrityError:
            await session.rollback()
            row = (
                await session.execute(select(Esp32Telemetry).where(*identity))
            ).scalar_one_or_none()
            if row is not None and row.packet == contents:
                return "duplicate"
            return "conflict"


class Esp32SerialWorker:
    """Optional serial receiver. Reconnects after disconnect; bounded I/O."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        system_id: UUID,
        device_id: str,
        port: str,
        baudrate: int = 115200,
        serial_factory: Callable | None = None,
        reconnect_seconds: float = 2.0,
        sensor_mapping: Mapping[str, UUID] | None = None,
    ) -> None:
        if not SERIAL_PORT_PATTERN.fullmatch(port):
            raise ValueError("ESP32_SERIAL_PORT must be a /dev/ttyUSB*, /dev/ttyACM*, or /dev/serial/by-id|by-path/ device")
        if not 300 <= baudrate <= 2_000_000:
            raise ValueError("ESP32_SERIAL_BAUDRATE out of supported range")
        if not device_id:
            raise ValueError("ESP32_DEVICE_ID is required")
        self.session_factory = session_factory
        self.system_id = system_id
        self.device_id = device_id
        self.port = port
        self.baudrate = baudrate
        self.reconnect_seconds = reconnect_seconds
        self.serial_factory = serial_factory
        self.sensor_mapping = dict(sensor_mapping or {})
        self._task: asyncio.Task | None = None
        self._stopping = asyncio.Event()

    async def start(self) -> None:
        if self._task is not None:
            return
        self._stopping.clear()
        self._task = asyncio.create_task(self._run(), name="esp32-usb-serial")

    async def stop(self) -> None:
        self._stopping.set()
        if self._task is not None:
            await self._task
            self._task = None

    async def _sleep_or_stop(self) -> None:
        try:
            await asyncio.wait_for(
                self._stopping.wait(), timeout=self.reconnect_seconds,
            )
        except asyncio.TimeoutError:
            pass

    async def _run(self) -> None:
        # Import in the worker; development installs without USB never open ports.
        import serial

        open_serial = self.serial_factory or serial.Serial
        while not self._stopping.is_set():
            connection = None
            try:
                # Some ESP32 USB/UART boards reset when a serial monitor opens.
                connection = await asyncio.to_thread(
                    open_serial, self.port, self.baudrate, timeout=0.5,
                )
                logger.info("ESP32 USB serial receiver connected")
                framer = SerialJsonFramer()
                last_valid_packet_at = monotonic()

                while not self._stopping.is_set():
                    if monotonic() - last_valid_packet_at >= 30:
                        logger.warning(
                            "ESP32 telemetry silent for 30 seconds; reopening USB serial port"
                        )
                        break

                    chunk = await asyncio.to_thread(connection.read, 256)
                    if not chunk:
                        # Avoid a busy loop with fake/nonblocking serial drivers.
                        await asyncio.sleep(0.02)
                        continue
                    for data in framer.feed(chunk):
                        try:
                            packet = Esp32SensorPacket.model_validate(data)
                        except (ValidationError, ValueError):
                            logger.warning("ESP32 serial packet rejected: schema validation failed")
                            continue
                        if packet.device_id != self.device_id:
                            logger.warning("ESP32 serial packet rejected: unexpected device_id")
                            continue

                        last_valid_packet_at = monotonic()
                        try:
                            outcome = await persist_esp32_packet(
                                self.session_factory,
                                system_id=self.system_id,
                                expected_device_id=self.device_id,
                                packet=packet,
                                sensor_mapping=self.sensor_mapping,
                            )
                        except Exception:
                            logger.exception("ESP32 serial packet could not be persisted")
                            continue
                        if outcome == "conflict":
                            logger.warning("ESP32 serial packet identity conflicts with saved history")
                        elif outcome == "unavailable":
                            logger.warning("ESP32 serial system is not available")
            except (serial.SerialException, OSError):
                if not self._stopping.is_set():
                    logger.warning("ESP32 USB serial port unavailable; reconnecting")
            except Exception:
                if not self._stopping.is_set():
                    logger.exception("ESP32 serial receiver error; reconnecting")
            finally:
                if connection is not None:
                    try:
                        await asyncio.to_thread(connection.close)
                    except Exception:
                        logger.warning("ESP32 serial port close failed")

            if not self._stopping.is_set():
                await self._sleep_or_stop()
