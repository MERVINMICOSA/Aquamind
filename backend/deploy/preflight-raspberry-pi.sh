#!/usr/bin/env bash

set -Eeuo pipefail


# ============================================================
# AQUAMIND
# RASPBERRY PI 5 DEPLOYMENT PREFLIGHT
# ============================================================
#
# PURPOSE
#
# Verify that the Raspberry Pi is ready to run AquaMind
# BEFORE the systemd service is enabled or physical hardware
# control is commissioned.
#
# THIS SCRIPT DOES NOT:
#
# - enable HARDWARE_ENABLED
# - assign BCM GPIO pins
# - choose HARDWARE_GPIO_CHIP
# - configure relay polarity
# - enable Linux 1-Wire
# - configure a DS18B20 device ID
# - switch relays
# - start pumps/fans
# - start or enable aquamind.service
#
# The expected safe state for this phase is:
#
#     HARDWARE_ENABLED=false
#
# Physical commissioning happens later after the actual
# components and wiring are confirmed.
# ============================================================


# ============================================================
# COUNTERS
# ============================================================


PASS_COUNT=0
WARN_COUNT=0
FAIL_COUNT=0


# ============================================================
# OUTPUT
# ============================================================


pass() {
    PASS_COUNT=$((PASS_COUNT + 1))
    printf '[PASS] %s\n' "$1"
}


warn() {
    WARN_COUNT=$((WARN_COUNT + 1))
    printf '[WARN] %s\n' "$1" >&2
}


fail() {
    FAIL_COUNT=$((FAIL_COUNT + 1))
    printf '[FAIL] %s\n' "$1" >&2
}


section() {
    printf '\n'
    printf '%s\n' \
        "============================================================"
    printf '%s\n' "$1"
    printf '%s\n' \
        "============================================================"
}


# ============================================================
# PROJECT LOCATION
# ============================================================


SCRIPT_DIR="$(
    cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
    pwd
)"

BACKEND_ROOT="$(
    cd -- "${SCRIPT_DIR}/.."
    pwd
)"

PROJECT_ROOT="$(
    cd -- "${BACKEND_ROOT}/.."
    pwd
)"


RUNTIME_ENV="${SCRIPT_DIR}/aquamind-runtime.env"

HARDWARE_ENV="${SCRIPT_DIR}/raspberry-pi5.hardware.env"

REQUIREMENTS_PI="${BACKEND_ROOT}/requirements-pi.txt"

PROVISION_SCRIPT="${SCRIPT_DIR}/provision-raspberry-pi.sh"

RUN_SCRIPT="${SCRIPT_DIR}/run-aquamind.sh"

SERVICE_INSTALLER="${SCRIPT_DIR}/install-aquamind-service.sh"

VENV_DIR="${VENV_DIR:-${BACKEND_ROOT}/.venv}"

VENV_PYTHON="${VENV_DIR}/bin/python"


# ============================================================
# ENV FILE READER
# ============================================================
#
# Read a simple KEY=value entry without sourcing the file.
#
# We do not execute deployment environment files as shell code.
# ============================================================


read_env_value() {
    local file="$1"
    local key="$2"

    local line

    line="$(
        grep -E "^[[:space:]]*${key}=" \
            "${file}" \
            | tail -n 1 \
            || true
    )"

    if [[ -z "${line}" ]]; then
        return 1
    fi

    local value="${line#*=}"

    # Remove Windows carriage return if the file was created
    # or edited from Windows.
    value="${value//$'\r'/}"

    # Trim surrounding whitespace.
    value="$(
        printf '%s' "${value}" \
            | sed \
                -e 's/^[[:space:]]*//' \
                -e 's/[[:space:]]*$//'
    )"

    # Remove one pair of matching surrounding quotes.
    if [[ "${value}" == \"*\" || "${value}" == \'*\' ]]; then
        value="${value:1:${#value}-2}"
    fi

    printf '%s' "${value}"
}


# ============================================================
# PLATFORM
# ============================================================


section "PLATFORM"


if [[ "$(uname -s)" == "Linux" ]]; then
    pass "Linux operating system detected."
else
    fail \
        "AquaMind Raspberry Pi deployment requires Linux."
fi


MACHINE="$(uname -m)"


case "${MACHINE}" in
    aarch64|armv7l)
        pass \
            "Supported ARM architecture detected: ${MACHINE}"
        ;;
    *)
        fail \
            "Unsupported architecture detected: ${MACHINE}"
        ;;
esac


PI_MODEL=""


if [[ -r /proc/device-tree/model ]]; then
    PI_MODEL="$(
        tr -d '\0' \
            < /proc/device-tree/model
    )"
fi


if [[ -z "${PI_MODEL}" ]]; then
    fail \
        "Unable to read Raspberry Pi model information."

elif [[ "${PI_MODEL}" == *"Raspberry Pi 5"* ]]; then
    pass \
        "Raspberry Pi 5 detected: ${PI_MODEL}"

else
    fail \
        "Expected Raspberry Pi 5 but detected: ${PI_MODEL}"
fi


# Report memory without using it as an unsafe exact-model test.
if [[ -r /proc/meminfo ]]; then
    MEM_KB="$(
        awk \
            '/^MemTotal:/ {print $2}' \
            /proc/meminfo
    )"

    if [[ -n "${MEM_KB}" ]]; then
        MEM_MIB=$((MEM_KB / 1024))

        printf \
            '[INFO] Detected memory: approximately %s MiB\n' \
            "${MEM_MIB}"
    fi
fi


# ============================================================
# PROJECT FILES
# ============================================================


section "AQUAMIND FILES"


required_files=(
    "${BACKEND_ROOT}/app/main.py"
    "${BACKEND_ROOT}/requirements.txt"
    "${REQUIREMENTS_PI}"
    "${RUNTIME_ENV}"
    "${HARDWARE_ENV}"
    "${PROVISION_SCRIPT}"
    "${RUN_SCRIPT}"
    "${SERVICE_INSTALLER}"
)


for file in "${required_files[@]}"; do

    if [[ -f "${file}" ]]; then
        pass \
            "Found $(basename "${file}")"

    else
        fail \
            "Required file is missing: ${file}"
    fi

done


# ============================================================
# PYTHON ENVIRONMENT
# ============================================================


section "PYTHON ENVIRONMENT"


if [[ -x "${VENV_PYTHON}" ]]; then
    pass \
        "AquaMind virtual environment found."

else
    fail \
        "Virtual environment missing at ${VENV_DIR}"
fi


if [[ -x "${VENV_PYTHON}" ]]; then

    PYTHON_VERSION="$(
        "${VENV_PYTHON}" \
            -c \
            'import sys; print(".".join(map(str, sys.version_info[:3])))'
    )"

    printf \
        '[INFO] Virtual environment Python: %s\n' \
        "${PYTHON_VERSION}"


    if "${VENV_PYTHON}" - <<'PY'
import sys

raise SystemExit(
    0 if sys.version_info >= (3, 10) else 1
)
PY
    then
        pass \
            "Python version satisfies AquaMind requirements."
    else
        fail \
            "AquaMind requires Python 3.10 or newer."
    fi

fi


# ============================================================
# PYTHON PACKAGE PREFLIGHT
# ============================================================


section "PYTHON DEPENDENCIES"


if [[ -x "${VENV_PYTHON}" ]]; then

    if "${VENV_PYTHON}" - <<'PY'
import asyncpg
import fastapi
import gpiozero
import lgpio
import sqlalchemy
import uvicorn

from gpiozero.pins.lgpio import LGPIOFactory

print(
    "[INFO] FastAPI:",
    getattr(fastapi, "__version__", "installed"),
)

print(
    "[INFO] SQLAlchemy:",
    getattr(sqlalchemy, "__version__", "installed"),
)

print(
    "[INFO] GPIO Zero:",
    getattr(gpiozero, "__version__", "installed"),
)

print(
    "[INFO] asyncpg: installed"
)

print(
    "[INFO] lgpio module: installed"
)

print(
    "[INFO] LGPIOFactory import: OK"
)
PY
    then
        pass \
            "Required AquaMind/Pi Python imports succeeded."

    else
        fail \
            "One or more required Python dependencies could not be imported."
    fi

fi


# ============================================================
# NETWORK RUNTIME CONFIGURATION
# ============================================================


section "API RUNTIME CONFIGURATION"


if [[ -f "${RUNTIME_ENV}" ]]; then

    API_BIND_HOST="$(
        read_env_value \
            "${RUNTIME_ENV}" \
            "API_BIND_HOST" \
            || true
    )"

    API_BIND_PORT="$(
        read_env_value \
            "${RUNTIME_ENV}" \
            "API_BIND_PORT" \
            || true
    )"


    case "${API_BIND_HOST}" in
        127.0.0.1)
            pass \
                "API mode is Pi-only (127.0.0.1)."
            ;;

        0.0.0.0)
            pass \
                "API mode is LAN-accessible (0.0.0.0)."

            warn \
                "LAN mode exposes AquaMind on available network interfaces; network/firewall access must be reviewed."
            ;;

        *)
            fail \
                "API_BIND_HOST must be 127.0.0.1 or 0.0.0.0."
            ;;
    esac


    if [[ "${API_BIND_PORT}" =~ ^[0-9]+$ ]]; then

        if (
            ((
                API_BIND_PORT >= 1
                && API_BIND_PORT <= 65535
            ))
        ); then
            pass \
                "API port is valid: ${API_BIND_PORT}"

        else
            fail \
                "API_BIND_PORT is outside the valid TCP port range."
        fi

    else
        fail \
            "API_BIND_PORT must be an integer."
    fi

fi


# ============================================================
# HARDWARE SAFETY CONFIGURATION
# ============================================================


section "HARDWARE SAFETY"


if [[ -f "${HARDWARE_ENV}" ]]; then

    HARDWARE_ENABLED_VALUE="$(
        read_env_value \
            "${HARDWARE_ENV}" \
            "HARDWARE_ENABLED" \
            || true
    )"


    case "${HARDWARE_ENABLED_VALUE,,}" in
        false|0|no|off)
            pass \
                "Physical hardware control is safely disabled."
            ;;

        true|1|yes|on)
            fail \
                "HARDWARE_ENABLED is already true. Physical hardware must remain disabled during software deployment preflight."
            ;;

        *)
            fail \
                "HARDWARE_ENABLED is missing or invalid."
            ;;
    esac


    GPIO_CHIP_VALUE="$(
        read_env_value \
            "${HARDWARE_ENV}" \
            "HARDWARE_GPIO_CHIP" \
            || true
    )"

    ALLOWED_PINS_VALUE="$(
        read_env_value \
            "${HARDWARE_ENV}" \
            "HARDWARE_ALLOWED_BCM_PINS" \
            || true
    )"

    RELAY_CHANNELS_VALUE="$(
        read_env_value \
            "${HARDWARE_ENV}" \
            "HARDWARE_RELAY_CHANNELS_JSON" \
            || true
    )"


    if [[ -z "${GPIO_CHIP_VALUE}" ]]; then
        pass \
            "No gpiochip has been prematurely assigned."
    else
        warn \
            "HARDWARE_GPIO_CHIP is already populated: verify it during physical commissioning."
    fi


    if [[ -z "${ALLOWED_PINS_VALUE}" ]]; then
        pass \
            "No BCM GPIO allowlist has been prematurely assigned."
    else
        warn \
            "BCM GPIO allowlist is already populated; verify it against the final wiring plan."
    fi


    if [[ -z "${RELAY_CHANNELS_VALUE}" || "${RELAY_CHANNELS_VALUE}" == "[]" ]]; then
        pass \
            "No relay channel mapping has been prematurely assigned."
    else
        warn \
            "Relay channel mappings already exist; verify every entry during physical commissioning."
    fi

fi


# ============================================================
# DATABASE CONFIGURATION
# ============================================================


section "DATABASE"


if [[ -x "${VENV_PYTHON}" ]]; then

    cd "${BACKEND_ROOT}"


    if "${VENV_PYTHON}" - <<'PY'
from app.core.config import settings
from sqlalchemy.engine import make_url


url = make_url(
    settings.DATABASE_URL
)


print(
    "[INFO] SQLAlchemy database driver:",
    url.drivername,
)

print(
    "[INFO] Database host:",
    url.host,
)

print(
    "[INFO] Database port:",
    url.port,
)

print(
    "[INFO] Database name:",
    url.database,
)

print(
    "[INFO] Database user:",
    url.username,
)


if url.drivername != "postgresql+asyncpg":
    raise SystemExit(
        "AquaMind deployment expects the "
        "postgresql+asyncpg driver."
    )
PY
    then
        pass \
            "Database configuration uses postgresql+asyncpg."
    else
        fail \
            "Database configuration is invalid."
    fi

fi


# ============================================================
# DATABASE CONNECTIVITY
# ============================================================


if [[ -x "${VENV_PYTHON}" ]]; then

    if "${VENV_PYTHON}" - <<'PY'
import asyncio

from sqlalchemy import text

from app.main import engine


async def probe():
    async with engine.connect() as connection:
        result = await connection.execute(
            text(
                "SELECT "
                "current_database(), "
                "current_user"
            )
        )

        database, user = result.one()

        print(
            "[INFO] Connected database:",
            database,
        )

        print(
            "[INFO] Connected database user:",
            user,
        )


async def main():
    try:
        await asyncio.wait_for(
            probe(),
            timeout=10,
        )

    finally:
        await engine.dispose()


asyncio.run(
    main()
)
PY
    then
        pass \
            "AquaMind database connection succeeded."

    else
        fail \
            "AquaMind could not connect to the configured database."
    fi

fi


# ============================================================
# GPIO ENVIRONMENT
# ============================================================


section "GPIO ENVIRONMENT"


if command -v gpiodetect >/dev/null 2>&1; then

    pass \
        "gpiodetect is installed."

    printf '\n'
    printf '%s\n' \
        "[INFO] GPIO controllers reported by this Raspberry Pi:"

    if ! gpiodetect; then
        warn \
            "gpiodetect could not enumerate GPIO controllers."
    fi

else
    fail \
        "gpiodetect is unavailable. Run Raspberry Pi provisioning first."
fi


GPIO_DEVICE_COUNT=0


if compgen -G "/dev/gpiochip*" >/dev/null; then

    GPIO_DEVICE_COUNT="$(
        find /dev \
            -maxdepth 1 \
            -name 'gpiochip*' \
            -type c \
            2>/dev/null \
            | wc -l
    )"

    pass \
        "Linux GPIO character devices detected: ${GPIO_DEVICE_COUNT}"

else
    warn \
        "No /dev/gpiochip* character devices were detected."
fi


# ============================================================
# GPIO PERMISSIONS
# ============================================================


section "GPIO PERMISSIONS"


if getent group gpio >/dev/null 2>&1; then

    pass \
        "gpio group exists."

    CURRENT_USER="$(
        id -un
    )"

    if id -nG "${CURRENT_USER}" \
        | tr ' ' '\n' \
        | grep -qx "gpio"
    then
        pass \
            "User '${CURRENT_USER}' belongs to the gpio group."

    else
        warn \
            "User '${CURRENT_USER}' is not in the gpio group. This must be resolved before physical GPIO commissioning."
    fi

else
    warn \
        "No gpio group exists on this system."
fi


# ============================================================
# DS18B20 / 1-WIRE STATUS
# ============================================================


section "1-WIRE STATUS"


W1_ROOT="/sys/bus/w1/devices"


if [[ -d "${W1_ROOT}" ]]; then
    pass \
        "Linux 1-Wire device directory exists."

    DS18B20_COUNT="$(
        find "${W1_ROOT}" \
            -mindepth 1 \
            -maxdepth 1 \
            -type d \
            -name '28-*' \
            2>/dev/null \
            | wc -l
    )"

    printf \
        '[INFO] Currently detected DS18B20 devices: %s\n' \
        "${DS18B20_COUNT}"

else
    warn \
        "Linux 1-Wire is not currently exposing ${W1_ROOT}. This is acceptable before DS18B20 commissioning."
fi


# ============================================================
# SYSTEMD
# ============================================================


section "SYSTEMD"


if command -v systemctl >/dev/null 2>&1; then
    pass \
        "systemd/systemctl is available."
else
    fail \
        "systemctl is unavailable."
fi


# ============================================================
# RESULT
# ============================================================


section "PREFLIGHT RESULT"


printf 'Passed checks : %s\n' \
    "${PASS_COUNT}"

printf 'Warnings      : %s\n' \
    "${WARN_COUNT}"

printf 'Failed checks : %s\n' \
    "${FAIL_COUNT}"

printf '\n'


if (( FAIL_COUNT > 0 )); then

    printf '%s\n' \
        "AQUAMIND DEPLOYMENT PREFLIGHT: FAILED"

    printf '\n'

    printf '%s\n' \
        "Do not enable or start the AquaMind systemd service yet."

    printf '%s\n' \
        "Do not enable physical hardware."

    exit 1

fi


printf '%s\n' \
    "AQUAMIND DEPLOYMENT PREFLIGHT: PASSED"

printf '\n'

printf '%s\n' \
    "Software deployment prerequisites are ready."

printf '%s\n' \
    "Warnings should still be reviewed."

printf '\n'

printf '%s\n' \
    "IMPORTANT:"

printf '%s\n' \
    "Passing this preflight does NOT authorize physical hardware."

printf '%s\n' \
    "Keep HARDWARE_ENABLED=false until final component and wiring commissioning."

printf '\n'

exit 0