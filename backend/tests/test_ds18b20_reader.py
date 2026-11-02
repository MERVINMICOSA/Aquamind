from __future__ import annotations

from datetime import (
    datetime,
    timezone,
)

import pytest

from app.hardware.ds18b20_reader import (
    DS18B20Reader,
)
from app.hardware.sensor_reader import (
    HardwareSensorReadError,
)


# ============================================================
# FIXED VALUES
# ============================================================


DEVICE_ID = "28-00000abcdef0"

RECORDED_AT = datetime(
    2026,
    9,
    3,
    12,
    0,
    0,
    tzinfo=timezone.utc,
)


# ============================================================
# HELPERS
# ============================================================


def create_device(
    tmp_path,
    *,
    payload: str,
):
    device_directory = (
        tmp_path
        / DEVICE_ID
    )

    device_directory.mkdir()

    (
        device_directory
        / "w1_slave"
    ).write_text(
        payload,
        encoding="utf-8",
    )


def create_reader(
    tmp_path,
):
    return DS18B20Reader(
        devices_root=tmp_path,
        clock=lambda: RECORDED_AT,
    )


# ============================================================
# SUCCESS
# ============================================================


def test_reads_valid_positive_temperature(
    tmp_path,
):
    create_device(
        tmp_path,
        payload=(
            "73 01 4b 46 7f ff 0d 10 41 "
            ": crc=41 YES\n"
            "73 01 4b 46 7f ff 0d 10 41 "
            "t=23187\n"
        ),
    )

    reader = create_reader(
        tmp_path
    )

    result = reader.read(
        DEVICE_ID
    )

    assert (
        result.hardware_identifier
        == DEVICE_ID
    )

    assert (
        result.value_numeric
        == pytest.approx(
            23.187
        )
    )

    assert (
        result.recorded_at
        == RECORDED_AT
    )


def test_reads_valid_negative_temperature(
    tmp_path,
):
    create_device(
        tmp_path,
        payload=(
            "00 00 00 00 00 00 00 00 00 "
            ": crc=00 YES\n"
            "00 00 00 00 00 00 00 00 00 "
            "t=-5250\n"
        ),
    )

    result = (
        create_reader(
            tmp_path
        )
        .read(
            DEVICE_ID
        )
    )

    assert (
        result.value_numeric
        == pytest.approx(
            -5.25
        )
    )


# ============================================================
# IDENTIFIER SAFETY
# ============================================================


def test_invalid_identifier_is_rejected(
    tmp_path,
):
    reader = create_reader(
        tmp_path
    )

    with pytest.raises(
        HardwareSensorReadError,
        match=(
            "Invalid DS18B20 "
            "hardware identifier"
        ),
    ) as exc_info:
        reader.read(
            "../../etc/passwd"
        )

    assert (
        exc_info.value.fault_code
        == "invalid_hardware_identifier"
    )


# ============================================================
# DEVICE PRESENCE
# ============================================================


def test_missing_sensor_is_reported(
    tmp_path,
):
    reader = create_reader(
        tmp_path
    )

    with pytest.raises(
        HardwareSensorReadError,
        match=(
            "DS18B20 sensor was not found"
        ),
    ) as exc_info:
        reader.read(
            DEVICE_ID
        )

    assert (
        exc_info.value.fault_code
        == "sensor_not_found"
    )


# ============================================================
# CRC VALIDATION
# ============================================================


def test_invalid_crc_is_rejected(
    tmp_path,
):
    create_device(
        tmp_path,
        payload=(
            "73 01 4b 46 7f ff 0d 10 41 "
            ": crc=41 NO\n"
            "73 01 4b 46 7f ff 0d 10 41 "
            "t=23187\n"
        ),
    )

    reader = create_reader(
        tmp_path
    )

    with pytest.raises(
        HardwareSensorReadError,
        match=(
            "CRC validation failed"
        ),
    ) as exc_info:
        reader.read(
            DEVICE_ID
        )

    assert (
        exc_info.value.fault_code
        == "sensor_crc_invalid"
    )


# ============================================================
# MALFORMED PAYLOAD
# ============================================================


def test_missing_temperature_value_is_rejected(
    tmp_path,
):
    create_device(
        tmp_path,
        payload=(
            "73 01 4b 46 7f ff 0d 10 41 "
            ": crc=41 YES\n"
            "73 01 4b 46 7f ff 0d 10 41\n"
        ),
    )

    reader = create_reader(
        tmp_path
    )

    with pytest.raises(
        HardwareSensorReadError,
        match=(
            "temperature value is missing"
        ),
    ) as exc_info:
        reader.read(
            DEVICE_ID
        )

    assert (
        exc_info.value.fault_code
        == "sensor_payload_invalid"
    )


# ============================================================
# PHYSICAL RANGE
# ============================================================


def test_out_of_range_temperature_is_rejected(
    tmp_path,
):
    create_device(
        tmp_path,
        payload=(
            "00 00 00 00 00 00 00 00 00 "
            ": crc=00 YES\n"
            "00 00 00 00 00 00 00 00 00 "
            "t=130000\n"
        ),
    )

    reader = create_reader(
        tmp_path
    )

    with pytest.raises(
        HardwareSensorReadError,
        match=(
            "outside the supported "
            "measurement range"
        ),
    ) as exc_info:
        reader.read(
            DEVICE_ID
        )

    assert (
        exc_info.value.fault_code
        == "sensor_value_out_of_range"
    )


# ============================================================
# TIMESTAMP CONTRACT
# ============================================================


def test_reader_requires_timezone_aware_timestamp(
    tmp_path,
):
    create_device(
        tmp_path,
        payload=(
            "73 01 4b 46 7f ff 0d 10 41 "
            ": crc=41 YES\n"
            "73 01 4b 46 7f ff 0d 10 41 "
            "t=25000\n"
        ),
    )

    reader = DS18B20Reader(
        devices_root=tmp_path,
        clock=lambda: datetime(
            2026,
            9,
            3,
            12,
            0,
            0,
        ),
    )

    with pytest.raises(
        HardwareSensorReadError,
        match=(
            "timezone-aware datetime"
        ),
    ) as exc_info:
        reader.read(
            DEVICE_ID
        )

    assert (
        exc_info.value.fault_code
        == "invalid_sensor_timestamp"
    )