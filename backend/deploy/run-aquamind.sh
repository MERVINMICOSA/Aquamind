#!/usr/bin/env bash

set -Eeuo pipefail


# ============================================================
# AQUAMIND
# PRODUCTION APPLICATION LAUNCHER
# ============================================================
#
# This script is executed by systemd on the Raspberry Pi.
#
# Network and hardware environment variables are supplied by
# the systemd unit before this script runs.
#
# Exactly one Uvicorn process is used.
#
# This is important because AquaMind owns physical GPIO and a
# background sensor worker. Multiple Uvicorn workers would
# create multiple competing hardware runtimes.
# ============================================================


fail() {
    printf '[AquaMind] ERROR: %s\n' "$1" >&2
    exit 1
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


# ============================================================
# RUNTIME SETTINGS
# ============================================================


API_BIND_HOST="${API_BIND_HOST:-127.0.0.1}"
API_BIND_PORT="${API_BIND_PORT:-8000}"

VENV_DIR="${VENV_DIR:-${BACKEND_ROOT}/.venv}"
VENV_PYTHON="${VENV_DIR}/bin/python"


# ============================================================
# BIND HOST VALIDATION
# ============================================================
#
# AquaMind deliberately supports only the two deployment modes
# we have defined:
#
#     127.0.0.1 -> Pi-only
#     0.0.0.0   -> LAN-accessible
#
# This prevents a malformed configuration from silently
# changing the application's network exposure.
# ============================================================


case "${API_BIND_HOST}" in
    127.0.0.1|0.0.0.0)
        ;;
    *)
        fail \
            "API_BIND_HOST must be either 127.0.0.1 or 0.0.0.0."
        ;;
esac


# ============================================================
# PORT VALIDATION
# ============================================================


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
# PYTHON ENVIRONMENT VALIDATION
# ============================================================


if [[ ! -x "${VENV_PYTHON}" ]]; then
    fail \
        "AquaMind virtual environment was not found at ${VENV_DIR}."
fi


if [[ ! -f "${BACKEND_ROOT}/app/main.py" ]]; then
    fail \
        "AquaMind backend could not be found at ${BACKEND_ROOT}."
fi


# ============================================================
# APPLICATION START
# ============================================================


cd "${BACKEND_ROOT}"


printf '[AquaMind] Starting API on %s:%s\n' \
    "${API_BIND_HOST}" \
    "${API_BIND_PORT}"


exec "${VENV_PYTHON}" \
    -m uvicorn \
    app.main:app \
    --host "${API_BIND_HOST}" \
    --port "${API_BIND_PORT}"