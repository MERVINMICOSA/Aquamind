#!/usr/bin/env bash

set -Eeuo pipefail


# ============================================================
# AQUAMIND
# SAFE SYSTEMD SERVICE ACTIVATION
# ============================================================
#
# Run this ONLY on the Raspberry Pi after:
#
#   1. provision-raspberry-pi.sh
#   2. preflight-raspberry-pi.sh
#   3. install-aquamind-service.sh
#
# This script enables the AquaMind software service while
# PHYSICAL HARDWARE REMAINS DISABLED.
#
# It deliberately refuses activation when:
#
#     HARDWARE_ENABLED=true
#
# Successful activation means:
#
# - systemd service enabled at boot
# - AquaMind API running
# - database connectivity verified
# - AsyncSession connectivity verified
# - physical GPIO control still disabled
#
# It DOES NOT:
#
# - assign GPIO pins
# - select a gpiochip
# - configure relay polarity
# - configure DS18B20 IDs
# - enable 1-Wire
# - switch relays
# - start pumps or fans
# ============================================================


# ============================================================
# OUTPUT
# ============================================================


info() {
    printf '\n[AquaMind] %s\n' "$1"
}


fail() {
    printf '\n[AquaMind] ERROR: %s\n' "$1" >&2
    exit 1
}


# ============================================================
# LOCATIONS
# ============================================================


SCRIPT_DIR="$(
    cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
    pwd
)"

BACKEND_ROOT="$(
    cd -- "${SCRIPT_DIR}/.."
    pwd
)"


PREFLIGHT_SCRIPT="${SCRIPT_DIR}/preflight-raspberry-pi.sh"

RUNTIME_ENV="${SCRIPT_DIR}/aquamind-runtime.env"

HARDWARE_ENV="${SCRIPT_DIR}/raspberry-pi5.hardware.env"

VENV_DIR="${VENV_DIR:-${BACKEND_ROOT}/.venv}"

VENV_PYTHON="${VENV_DIR}/bin/python"

SERVICE_NAME="aquamind.service"


# ============================================================
# ENV FILE READER
# ============================================================
#
# Read KEY=value without sourcing the file.
#
# Deployment configuration is treated as data, not executable
# shell code.
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

    # Protect against files originally edited on Windows.
    value="${value//$'\r'/}"

    value="$(
        printf '%s' "${value}" \
            | sed \
                -e 's/^[[:space:]]*//' \
                -e 's/[[:space:]]*$//'
    )"

    if (
        [[ "${value}" == \"*\" ]]
        && [[ "${value}" == *\" ]]
    ); then
        value="${value:1:${#value}-2}"

    elif (
        [[ "${value}" == \'*\' ]]
        && [[ "${value}" == *\' ]]
    ); then
        value="${value:1:${#value}-2}"
    fi

    printf '%s' "${value}"
}


# ============================================================
# ROLLBACK
# ============================================================


rollback_service() {
    printf '\n'

    printf '%s\n' \
        "[AquaMind] Rolling back service activation..." >&2

    sudo systemctl disable \
        --now \
        "${SERVICE_NAME}" \
        >/dev/null 2>&1 \
        || true
}


# ============================================================
# PLATFORM SAFETY
# ============================================================


if [[ "$(uname -s)" != "Linux" ]]; then
    fail \
        "This activation script must run on Linux."
fi


MACHINE="$(uname -m)"


case "${MACHINE}" in
    aarch64|armv7l)
        ;;
    *)
        fail \
            "Unsupported architecture '${MACHINE}'."
        ;;
esac


PI_MODEL=""


if [[ -r /proc/device-tree/model ]]; then
    PI_MODEL="$(
        tr -d '\0' \
            < /proc/device-tree/model
    )"
fi


case "${PI_MODEL}" in
    *"Raspberry Pi 5"*)
        ;;
    *)
        fail \
            "This deployment targets Raspberry Pi 5. Detected: ${PI_MODEL:-unknown}"
        ;;
esac


# ============================================================
# PRIVILEGES
# ============================================================


if [[ "${EUID}" -eq 0 ]]; then
    fail \
        "Run this script as the normal AquaMind user, not directly as root."
fi


if ! command -v sudo >/dev/null 2>&1; then
    fail \
        "sudo is required for service activation."
fi


if ! command -v systemctl >/dev/null 2>&1; then
    fail \
        "systemctl is required for service activation."
fi


# ============================================================
# REQUIRED FILES
# ============================================================


required_files=(
    "${PREFLIGHT_SCRIPT}"
    "${RUNTIME_ENV}"
    "${HARDWARE_ENV}"
    "${BACKEND_ROOT}/app/main.py"
)


for file in "${required_files[@]}"; do

    if [[ ! -f "${file}" ]]; then
        fail \
            "Required file is missing: ${file}"
    fi

done


if [[ ! -x "${VENV_PYTHON}" ]]; then
    fail \
        "AquaMind virtual environment is missing at ${VENV_DIR}."
fi


# ============================================================
# HARDWARE SAFETY GATE
# ============================================================


HARDWARE_ENABLED_VALUE="$(
    read_env_value \
        "${HARDWARE_ENV}" \
        "HARDWARE_ENABLED" \
        || true
)"


case "${HARDWARE_ENABLED_VALUE,,}" in
    false|0|no|off)

        info \
            "Physical hardware is disabled. Safe software activation may continue."

        ;;

    true|1|yes|on)

        fail \
            "HARDWARE_ENABLED is true. Refusing software deployment activation before physical commissioning."

        ;;

    *)

        fail \
            "HARDWARE_ENABLED is missing or invalid."

        ;;
esac


# ============================================================
# API CONFIGURATION
# ============================================================


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
    127.0.0.1|0.0.0.0)
        ;;
    *)
        fail \
            "API_BIND_HOST must be 127.0.0.1 or 0.0.0.0."
        ;;
esac


if ! [[ "${API_BIND_PORT}" =~ ^[0-9]+$ ]]; then
    fail \
        "API_BIND_PORT must be an integer."
fi


if (
    ((
        API_BIND_PORT < 1
        || API_BIND_PORT > 65535
    ))
); then
    fail \
        "API_BIND_PORT must be between 1 and 65535."
fi


# ============================================================
# SERVICE INSTALLATION CHECK
# ============================================================


if ! sudo systemctl cat \
    "${SERVICE_NAME}" \
    >/dev/null 2>&1
then
    fail \
        "AquaMind systemd service is not installed. Run install-aquamind-service.sh first."
fi


# ============================================================
# PREFLIGHT
# ============================================================


info \
    "Running deployment preflight before service activation..."


if ! bash "${PREFLIGHT_SCRIPT}"; then

    fail \
        "Deployment preflight failed. AquaMind service will not be activated."

fi


# ============================================================
# ENABLE AND START
# ============================================================


info \
    "Enabling AquaMind at boot and starting the service..."


if ! sudo systemctl enable \
    --now \
    "${SERVICE_NAME}"
then

    rollback_service

    fail \
        "systemd could not enable/start AquaMind."

fi


# ============================================================
# SYSTEMD STATE
# ============================================================


info \
    "Waiting for AquaMind service startup..."


SERVICE_ACTIVE=false


for _ in $(seq 1 15); do

    if sudo systemctl is-active \
        --quiet \
        "${SERVICE_NAME}"
    then
        SERVICE_ACTIVE=true
        break
    fi

    sleep 1

done


if [[ "${SERVICE_ACTIVE}" != "true" ]]; then

    printf '\n'
    printf '%s\n' \
        "[AquaMind] Recent service log:" >&2

    sudo journalctl \
        -u "${SERVICE_NAME}" \
        -n 50 \
        --no-pager \
        >&2 \
        || true

    rollback_service

    fail \
        "AquaMind did not reach the active systemd state."

fi


info \
    "AquaMind systemd service is active."


# ============================================================
# HTTP HEALTH VERIFICATION
# ============================================================
#
# Always verify using 127.0.0.1.
#
# When API_BIND_HOST is:
#
#   127.0.0.1
#       -> local Pi access works.
#
#   0.0.0.0
#       -> local Pi access through 127.0.0.1 also works.
#
# Therefore this test is valid for both deployment modes.
# ============================================================


info \
    "Verifying AquaMind application health..."


if ! "${VENV_PYTHON}" \
    - "${API_BIND_PORT}" <<'PY'
import json
import sys
import time
import urllib.error
import urllib.request


port = int(
    sys.argv[1]
)

base_url = (
    f"http://127.0.0.1:{port}"
)


checks = (
    "/health",
    "/db-health",
    "/db-session-health",
)


deadline = (
    time.monotonic()
    + 30.0
)


last_errors = {}


while (
    time.monotonic()
    < deadline
):
    all_ok = True

    for path in checks:
        url = (
            base_url
            + path
        )

        try:
            with urllib.request.urlopen(
                url,
                timeout=3,
            ) as response:
                payload = json.load(
                    response
                )

            if (
                payload.get("status")
                != "ok"
            ):
                raise RuntimeError(
                    f"unexpected payload: {payload}"
                )

            last_errors.pop(
                path,
                None,
            )

        except Exception as exc:
            all_ok = False

            last_errors[
                path
            ] = str(exc)

    if all_ok:
        print(
            "[AquaMind] /health: OK"
        )

        print(
            "[AquaMind] /db-health: OK"
        )

        print(
            "[AquaMind] /db-session-health: OK"
        )

        raise SystemExit(0)

    time.sleep(1)


print(
    "[AquaMind] Health verification timed out.",
    file=sys.stderr,
)


for path, error in (
    last_errors.items()
):
    print(
        f"[AquaMind] {path}: {error}",
        file=sys.stderr,
    )


raise SystemExit(1)
PY
then

    printf '\n'
    printf '%s\n' \
        "[AquaMind] Recent service log:" >&2

    sudo journalctl \
        -u "${SERVICE_NAME}" \
        -n 50 \
        --no-pager \
        >&2 \
        || true

    rollback_service

    fail \
        "AquaMind application health verification failed."

fi


# ============================================================
# BOOT ENABLEMENT VERIFICATION
# ============================================================


if sudo systemctl is-enabled \
    --quiet \
    "${SERVICE_NAME}"
then

    info \
        "AquaMind automatic startup is enabled."

else

    rollback_service

    fail \
        "AquaMind service is running but was not enabled at boot."

fi


# ============================================================
# FINAL HARDWARE SAFETY RECHECK
# ============================================================


HARDWARE_ENABLED_VALUE="$(
    read_env_value \
        "${HARDWARE_ENV}" \
        "HARDWARE_ENABLED" \
        || true
)"


case "${HARDWARE_ENABLED_VALUE,,}" in
    false|0|no|off)
        ;;
    *)
        rollback_service

        fail \
            "Hardware safety state changed during activation."
        ;;
esac


# ============================================================
# COMPLETE
# ============================================================


printf '\n'
printf '%s\n' \
    "============================================================"

printf '%s\n' \
    " AQUAMIND SAFE SERVICE ACTIVATION COMPLETE"

printf '%s\n' \
    "============================================================"

printf '\n'

printf '%s\n' \
    "AquaMind service: ACTIVE"

printf '%s\n' \
    "Automatic startup: ENABLED"

printf 'API bind host: %s\n' \
    "${API_BIND_HOST}"

printf 'API bind port: %s\n' \
    "${API_BIND_PORT}"

printf '%s\n' \
    "Application health: OK"

printf '%s\n' \
    "Database health: OK"

printf '%s\n' \
    "Physical hardware control: DISABLED"

printf '\n'

printf '%s\n' \
    "The AquaMind software deployment is active."

printf '%s\n' \
    "Physical hardware commissioning is still required before HARDWARE_ENABLED may be changed to true."

printf '\n'