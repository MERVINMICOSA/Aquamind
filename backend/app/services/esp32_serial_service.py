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
from datetime import datetime, timedelta, timezone
from time import monotonic
from typing import Callable, Mapping
from uuid import UUID, uuid4

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.esp32_capture import Esp32CaptureState
from app.models.esp32_telemetry import Esp32Telemetry
from app.models.system import AquaponicsSystem
from app.schemas.esp32_telemetry import Esp32SensorPacket
from app.services.esp32_sensor_bridge import build_sensor_readings, discover_sensor_mapping
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


# A disconnected sensor must not be archived as if it were current.
# Continuous firmware reporting is expected to provide a newer packet.
MAX_SAVE_PACKET_AGE_SECONDS = 45


def _aware(value: datetime) -> datetime:
    """SQLite test dates may be naive even for timezone-aware columns."""
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _packet_identity(system_id: UUID, packet: Esp32SensorPacket):
    return (
        Esp32Telemetry.system_id == system_id,
        Esp32Telemetry.device_id == packet.device_id,
        Esp32Telemetry.sequence == packet.sequence,
        Esp32Telemetry.uptime_ms == packet.uptime_ms,
    )


async def _archive_packet(
    session: AsyncSession, *,
    system_id: UUID,
    packet: Esp32SensorPacket,
    received_at: datetime,
    sensor_mapping: Mapping[str, UUID] | None,
    auto_discover_sensors: bool,
) -> str:
    """Archive once and only then derive the optional registered readings."""
    contents = packet.model_dump(mode="json", exclude_unset=True)
    existing = (
        await session.execute(select(Esp32Telemetry).where(*_packet_identity(system_id, packet)))
    ).scalar_one_or_none()
    if existing is not None:
        return "duplicate" if existing.packet == contents else "conflict"

    session.add(Esp32Telemetry(
        system_id=system_id,
        device_id=packet.device_id,
        sequence=packet.sequence,
        uptime_ms=packet.uptime_ms,
        packet=contents,
        received_at=received_at,
    ))
    await session.flush()

    mapping = (
        await discover_sensor_mapping(session, system_id=system_id, packet=packet)
        if auto_discover_sensors else sensor_mapping
    )
    if mapping:
        readings = await build_sensor_readings(
            session, system_id=system_id, packet=packet,
            sensor_mapping=mapping, received_at=received_at,
        )
        session.add_all(readings)
        await session.flush()
        for reading in readings:
            await process_sensor_reading(session, reading, commit=False)
    return "created"


async def _flush_timed(
    session: AsyncSession, state: Esp32CaptureState, *,
    now: datetime,
    sensor_mapping: Mapping[str, UUID] | None,
    auto_discover_sensors: bool,
) -> str:
    """Save the final pre-boundary packet; never substitute a post-boundary one.

    Consume all elapsed boundaries without backfilling missing intervals.
    Both serial ingestion and the one-second timer call this with a row lock.
    """
    if state.mode != "timed" or state.next_save_at is None:
        return "not_due"

    due = _aware(state.next_save_at)
    if now < due:
        return "not_due"

    delta = timedelta(minutes=state.interval_minutes)
    start = _aware(state.window_started_at) if state.window_started_at else due - delta
    latest_time = _aware(state.latest_received_at) if state.latest_received_at else None
    result = "skipped"

    if (
        state.latest_packet is not None
        and latest_time is not None
        and start <= latest_time < due
        and 0 <= (due - latest_time).total_seconds() <= MAX_SAVE_PACKET_AGE_SECONDS
    ):
        packet = Esp32SensorPacket.model_validate(state.latest_packet)
        result = await _archive_packet(
            session, system_id=state.system_id, packet=packet,
            received_at=latest_time,
            sensor_mapping=sensor_mapping,
            auto_discover_sensors=auto_discover_sensors,
        )
        if result == "created":
            state.last_saved_at = latest_time
            state.last_saved_scheduled_at = due
        elif result == "conflict":
            logger.warning("ESP32 timed capture found an archive identity conflict")

    # Jump across downtime without repeatedly storing an old live packet.
    steps = int((now - due).total_seconds() // delta.total_seconds()) + 1
    state.window_started_at = due + delta * (steps - 1)
    state.next_save_at = due + delta * steps
    return result


async def flush_esp32_interval(
    session_factory: async_sessionmaker[AsyncSession], *,
    system_id: UUID,
    now: datetime | None = None,
    sensor_mapping: Mapping[str, UUID] | None = None,
    auto_discover_sensors: bool = False,
) -> str:
    """Durable timer tick, including after process restart or USB disconnect."""
    current = _aware(now or datetime.now(timezone.utc))
    async with session_factory() as session:
        state = await session.get(Esp32CaptureState, system_id, with_for_update=True)
        if state is None:
            return "not_due"
        result = await _flush_timed(
            session, state, now=current, sensor_mapping=sensor_mapping,
            auto_discover_sensors=auto_discover_sensors,
        )
        await session.commit()
        return result


async def persist_esp32_packet(
    session_factory: async_sessionmaker[AsyncSession], *,
    system_id: UUID,
    expected_device_id: str,
    packet: Esp32SensorPacket,
    sensor_mapping: Mapping[str, UUID] | None = None,
    auto_discover_sensors: bool = False,
    received_at: datetime | None = None,
) -> str:
    """Accept validated USB telemetry, update live state, and archive by mode.

    A single transaction holds the capture-state lock through due-boundary
    selection, optional archive/registered readings and the latest state.
    The archive's unique constraint still enforces idempotency on retries.
    """
    if packet.device_id != expected_device_id:
        return "conflict"

    current = _aware(received_at or datetime.now(timezone.utc))
    contents = packet.model_dump(mode="json", exclude_unset=True)
    async with session_factory() as session:
        parent = await session.get(AquaponicsSystem, system_id)
        if parent is None or parent.deleted_at is not None:
            return "unavailable"

        try:
            state = await session.get(Esp32CaptureState, system_id, with_for_update=True)
            if state is None:
                # Legacy-safe: the default is Live until an admin chooses Timed.
                state = Esp32CaptureState(
                    system_id=system_id, device_id=packet.device_id,
                    mode="live", interval_minutes=5,
                )
                session.add(state)
                await session.flush()

            if state.device_id not in (None, packet.device_id):
                return "conflict"
            if (
                state.latest_sequence == packet.sequence
                and state.latest_uptime_ms == packet.uptime_ms
            ):
                return "duplicate" if state.latest_packet == contents else "conflict"

            # Reject already-archived replays; they must not replace newer live data.
            existing = (
                await session.execute(
                    select(Esp32Telemetry).where(*_packet_identity(system_id, packet))
                )
            ).scalar_one_or_none()
            if existing is not None:
                return "duplicate" if existing.packet == contents else "conflict"

            # Important: commit the last packet BEFORE the new packet crosses
            # a deadline. A packet after the deadline cannot be recorded as
            # the last packet of the preceding window.
            if state.mode == "timed":
                if state.next_save_at is None:
                    state.window_started_at = current
                    state.next_save_at = current + timedelta(minutes=state.interval_minutes)
                else:
                    await _flush_timed(
                        session, state, now=current,
                        sensor_mapping=sensor_mapping,
                        auto_discover_sensors=auto_discover_sensors,
                    )
            else:
                await _archive_packet(
                    session, system_id=system_id, packet=packet, received_at=current,
                    sensor_mapping=sensor_mapping,
                    auto_discover_sensors=auto_discover_sensors,
                )
                state.last_saved_at = current
                state.last_saved_scheduled_at = None

            state.device_id = packet.device_id
            state.latest_packet_id = uuid4()
            state.latest_sequence = packet.sequence
            state.latest_uptime_ms = packet.uptime_ms
            state.latest_packet = contents
            state.latest_received_at = current
            await session.commit()
            return "created"
        except IntegrityError:
            await session.rollback()
            # Includes races with the unique archive identity and state insert.
            existing = (
                await session.execute(
                    select(Esp32Telemetry).where(*_packet_identity(system_id, packet))
                )
            ).scalar_one_or_none()
            if existing is not None and existing.packet == contents:
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
        auto_discover_sensors: bool = False,
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
        self.auto_discover_sensors = auto_discover_sensors
        self._task: asyncio.Task | None = None
        self._capture_task: asyncio.Task | None = None
        self._stopping = asyncio.Event()

    async def start(self) -> None:
        if self._task is not None:
            return
        self._stopping.clear()
        self._task = asyncio.create_task(self._run(), name="esp32-usb-serial")
        self._capture_task = asyncio.create_task(self._capture_loop(), name="esp32-history-timer")

    async def stop(self) -> None:
        self._stopping.set()
        if self._task is not None:
            await self._task
            self._task = None
        if self._capture_task is not None:
            await self._capture_task
            self._capture_task = None

    async def _capture_loop(self) -> None:
        while not self._stopping.is_set():
            try:
                await flush_esp32_interval(
                    self.session_factory, system_id=self.system_id,
                    sensor_mapping=self.sensor_mapping,
                    auto_discover_sensors=self.auto_discover_sensors,
                )
            except Exception:
                logger.exception("ESP32 timed capture failed; will retry")
            try:
                await asyncio.wait_for(self._stopping.wait(), timeout=1.0)
            except asyncio.TimeoutError:
                pass

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
                                auto_discover_sensors=self.auto_discover_sensors,
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
