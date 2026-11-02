from __future__ import annotations

import pytest

from app.hardware.ds18b20_reader import (
    DS18B20Reader,
)
from app.hardware.sensor_registry import (
    HardwareSensorReaderRegistry,
    HardwareSensorReaderRoute,
    HardwareSensorRoutingError,
)


# ============================================================
# READER
# ============================================================


class DummyReader:
    def read(
        self,
        hardware_identifier,
    ):
        raise AssertionError(
            "Registry tests do not perform "
            "physical reads"
        )


# ============================================================
# DS18B20 IDENTIFIER DETECTION
# ============================================================


def test_ds18b20_identifier_is_recognized():
    assert (
        DS18B20Reader
        .supports_identifier(
            "28-00000abcdef0"
        )
        is True
    )


def test_ds18b20_identifier_matching_tolerates_whitespace():
    assert (
        DS18B20Reader
        .supports_identifier(
            "  28-00000abcdef0  "
        )
        is True
    )


def test_non_ds18b20_identifier_is_not_recognized():
    assert (
        DS18B20Reader
        .supports_identifier(
            "ph-sensor-1"
        )
        is False
    )


# ============================================================
# REGISTRY RESOLUTION
# ============================================================


def test_registry_resolves_reader_by_hardware_identifier():
    reader = DummyReader()

    registry = (
        HardwareSensorReaderRegistry(
            [
                HardwareSensorReaderRoute(
                    name="ds18b20",
                    matches=(
                        DS18B20Reader
                        .supports_identifier
                    ),
                    reader=reader,
                ),
            ]
        )
    )

    assert (
        registry.resolve(
            "28-00000abcdef0"
        )
        is reader
    )


def test_registry_returns_none_for_unknown_identifier():
    reader = DummyReader()

    registry = (
        HardwareSensorReaderRegistry(
            [
                HardwareSensorReaderRoute(
                    name="ds18b20",
                    matches=(
                        DS18B20Reader
                        .supports_identifier
                    ),
                    reader=reader,
                ),
            ]
        )
    )

    assert (
        registry.resolve(
            "unknown-hardware"
        )
        is None
    )


def test_registry_returns_none_for_missing_identifier():
    registry = (
        HardwareSensorReaderRegistry(
            []
        )
    )

    assert (
        registry.resolve(
            None
        )
        is None
    )

    assert (
        registry.resolve(
            "   "
        )
        is None
    )


# ============================================================
# CONFIGURATION SAFETY
# ============================================================


def test_duplicate_route_names_are_rejected():
    with pytest.raises(
        HardwareSensorRoutingError,
        match="Duplicate",
    ):
        HardwareSensorReaderRegistry(
            [
                HardwareSensorReaderRoute(
                    name="reader",
                    matches=lambda _: True,
                    reader=DummyReader(),
                ),
                HardwareSensorReaderRoute(
                    name="reader",
                    matches=lambda _: False,
                    reader=DummyReader(),
                ),
            ]
        )


def test_ambiguous_reader_match_is_rejected():
    registry = (
        HardwareSensorReaderRegistry(
            [
                HardwareSensorReaderRoute(
                    name="reader-a",
                    matches=lambda _: True,
                    reader=DummyReader(),
                ),
                HardwareSensorReaderRoute(
                    name="reader-b",
                    matches=lambda _: True,
                    reader=DummyReader(),
                ),
            ]
        )
    )

    with pytest.raises(
        HardwareSensorRoutingError,
        match=(
            "Multiple hardware sensor readers"
        ),
    ):
        registry.resolve(
            "some-device"
        )