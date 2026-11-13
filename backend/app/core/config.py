from __future__ import annotations

import os

from dotenv import load_dotenv


load_dotenv()


# ============================================================
# ENVIRONMENT HELPERS
# ============================================================


def _env_bool(
    name: str,
    *,
    default: bool,
) -> bool:
    """
    Read a strict boolean environment variable.

    Accepted true values:
        true, 1, yes, on

    Accepted false values:
        false, 0, no, off

    Invalid values fail configuration immediately instead of
    silently enabling or disabling a safety-critical feature.
    """

    default_value = (
        "true"
        if default
        else "false"
    )

    raw = os.getenv(
        name,
        default_value,
    )

    normalized = (
        raw.strip().lower()
    )

    if normalized in {
        "true",
        "1",
        "yes",
        "on",
    }:
        return True

    if normalized in {
        "false",
        "0",
        "no",
        "off",
    }:
        return False

    raise ValueError(
        f"{name} must be a boolean value"
    )


# ============================================================
# SETTINGS
# ============================================================


class Settings:
    # Optional local USB serial telemetry reader. No network token required.
    ESP32_SERIAL_ENABLED: bool = _env_bool("ESP32_SERIAL_ENABLED", default=False)
    ESP32_SERIAL_PORT: str = os.getenv("ESP32_SERIAL_PORT", "")
    ESP32_SERIAL_BAUDRATE: int = int(os.getenv("ESP32_SERIAL_BAUDRATE", "115200"))
    ESP32_DEVICE_ID: str = os.getenv("ESP32_DEVICE_ID", "")
    ESP32_SYSTEM_ID: str = os.getenv("ESP32_SYSTEM_ID", "")

    # Opt-in sensor history bridge. Sensor rows are discovered automatically
    # from fresh ESP32 fields; no per-sensor UUID / identifier mapping required.
    ESP32_SENSOR_BRIDGE_ENABLED: bool = _env_bool(
        "ESP32_SENSOR_BRIDGE_ENABLED", default=False
    )

    # ========================================================
    # DATABASE
    # ========================================================

    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        (
            "postgresql+psycopg://"
            "aquamind:your-password@localhost:5432/aquamind"
        ),
    )

    DATABASE_POOL_SIZE: int = int(
        os.getenv(
            "DATABASE_POOL_SIZE",
            "10",
        )
    )

    DATABASE_MAX_OVERFLOW: int = int(
        os.getenv(
            "DATABASE_MAX_OVERFLOW",
            "20",
        )
    )

    DATABASE_POOL_TIMEOUT: int = int(
        os.getenv(
            "DATABASE_POOL_TIMEOUT",
            "30",
        )
    )

    # ========================================================
    # AUTHENTICATION / JWT
    # ========================================================

    JWT_SECRET_KEY: str = os.getenv(
        "JWT_SECRET_KEY",
        "",
    )

    JWT_ALGORITHM: str = os.getenv(
        "JWT_ALGORITHM",
        "HS256",
    )

    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv(
            "ACCESS_TOKEN_EXPIRE_MINUTES",
            "30",
        )
    )

    REFRESH_TOKEN_EXPIRE_DAYS: int = int(
        os.getenv(
            "REFRESH_TOKEN_EXPIRE_DAYS",
            "7",
        )
    )

    JWT_ISSUER: str = os.getenv(
        "JWT_ISSUER",
        "aquamind",
    )

    JWT_AUDIENCE: str = os.getenv(
        "JWT_AUDIENCE",
        "aquamind-api",
    )

    # ========================================================
    # CORS / FRONTEND
    # ========================================================

    FRONTEND_ORIGIN: str = os.getenv(
        "FRONTEND_ORIGIN",
        "http://127.0.0.1:3000",
    )

    # ========================================================
    # HARDWARE
    # ========================================================
    #
    # Hardware is disabled by default.
    #
    # This keeps normal development/test environments from
    # attempting to initialize Raspberry Pi GPIO.
    #
    # HARDWARE_ALLOWED_BCM_PINS:
    #
    #     Comma-separated BCM GPIO allowlist.
    #
    # Example format only:
    #
    #     17,18,22
    #
    # HARDWARE_RELAY_CHANNELS_JSON:
    #
    #     JSON array defining logical actuator identifiers,
    #     actuator types, BCM pins, and relay polarity.
    #
    # Actual production values will be chosen after the real
    # Raspberry Pi / relay wiring is known.
    # ========================================================

    HARDWARE_ENABLED: bool = _env_bool(
        "HARDWARE_ENABLED",
        default=False,
    )

    HARDWARE_GPIO_CHIP: str = os.getenv(
        "HARDWARE_GPIO_CHIP",
        "",
    )

    HARDWARE_ALLOWED_BCM_PINS: str = os.getenv(
        "HARDWARE_ALLOWED_BCM_PINS",
        "",
    )

    HARDWARE_RELAY_CHANNELS_JSON: str = os.getenv(
        "HARDWARE_RELAY_CHANNELS_JSON",
        "[]",
    )

    # ========================================================
    # COMPATIBILITY PROPERTIES
    # ========================================================

    @property
    def database_url(self) -> str:
        return self.DATABASE_URL


settings = Settings()