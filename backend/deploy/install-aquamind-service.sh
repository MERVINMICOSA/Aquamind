#!/usr/bin/env bash

set -Eeuo pipefail


# ============================================================
# AQUAMIND
# SYSTEMD SERVICE INSTALLER
# ============================================================
#
# Run this later on the Raspberry Pi after software
# provisioning.
#
# This script:
#
# - detects the real AquaMind backend path;
# - detects the real deployment user;
# - creates the systemd service using those actual values;
# - installs the service definition;
# - reloads systemd.
#
# It deliberately DOES NOT:
#
# - start AquaMind;
# - enable automatic startup;
# - enable hardware;
# - assign GPIO pins;
#
# Startup/enabling waits for deployment preflight.
# ============================================================


info() {
    printf '\n[AquaMind] %s\n' "$1"
}


fail() {
    printf '\n[AquaMind] ERROR: %s\n' "$1" >&2
    exit 1
}


# ============================================================
# PLATFORM
# ============================================================


if [[ "$(uname -s)" != "Linux" ]]; then
    fail \
        "This installer must run on Linux."
fi


if ! command -v systemctl >/dev/null 2>&1; then
    fail \
        "systemd/systemctl was not found."
fi


if ! command -v sudo >/dev/null 2>&1; then
    fail \
        "sudo is required to install the AquaMind service."
fi


if [[ "${EUID}" -eq 0 ]]; then
    fail \
        "Run this script as the normal AquaMind user, not directly as root."
fi


# ============================================================
# PATH DISCOVERY
# ============================================================


SCRIPT_DIR="$(
    cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
    pwd
)"

BACKEND_ROOT="$(
    cd -- "${SCRIPT_DIR}/.."
    pwd
)"


RUN_SCRIPT="${SCRIPT_DIR}/run-aquamind.sh"

RUNTIME_ENV="${SCRIPT_DIR}/aquamind-runtime.env"

HARDWARE_ENV="${SCRIPT_DIR}/raspberry-pi5.hardware.env"

VENV_PYTHON="${BACKEND_ROOT}/.venv/bin/python"


# ============================================================
# REAL SERVICE USER
# ============================================================


SERVICE_USER="${AQUAMIND_SERVICE_USER:-${USER}}"


if ! id "${SERVICE_USER}" >/dev/null 2>&1; then
    fail \
        "Service user '${SERVICE_USER}' does not exist."
fi


# ============================================================
# REQUIRED FILES
# ============================================================


if [[ ! -f "${BACKEND_ROOT}/app/main.py" ]]; then
    fail \
        "AquaMind backend was not found at ${BACKEND_ROOT}."
fi


if [[ ! -f "${RUN_SCRIPT}" ]]; then
    fail \
        "Missing launcher: ${RUN_SCRIPT}"
fi


if [[ ! -f "${RUNTIME_ENV}" ]]; then
    fail \
        "Missing runtime environment file: ${RUNTIME_ENV}"
fi


if [[ ! -f "${HARDWARE_ENV}" ]]; then
    fail \
        "Missing hardware environment file: ${HARDWARE_ENV}"
fi


if [[ ! -x "${VENV_PYTHON}" ]]; then
    fail \
        "AquaMind virtual environment is missing. Run provision-raspberry-pi.sh first."
fi


# ============================================================
# LAUNCHER PERMISSIONS
# ============================================================


chmod +x "${RUN_SCRIPT}"


# ============================================================
# SYSTEMD UNIT
# ============================================================


SERVICE_NAME="aquamind.service"

SERVICE_PATH="/etc/systemd/system/${SERVICE_NAME}"

TEMP_SERVICE="$(
    mktemp
)"


cleanup() {
    rm -f "${TEMP_SERVICE}"
}


trap cleanup EXIT


cat > "${TEMP_SERVICE}" <<EOF
[Unit]
Description=AquaMind Aquaponics Control API
After=network-online.target
Wants=network-online.target

[Service]
Type=simple

User=${SERVICE_USER}

WorkingDirectory=${BACKEND_ROOT}

Environment=PYTHONUNBUFFERED=1

EnvironmentFile=${RUNTIME_ENV}
EnvironmentFile=${HARDWARE_ENV}

ExecStart=${RUN_SCRIPT}

Restart=on-failure
RestartSec=5

TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
EOF


# ============================================================
# INSTALL
# ============================================================


info "Installing AquaMind systemd service..."

sudo install \
    -m 0644 \
    "${TEMP_SERVICE}" \
    "${SERVICE_PATH}"


info "Reloading systemd..."

sudo systemctl daemon-reload


# ============================================================
# VALIDATION
# ============================================================


if ! sudo systemctl cat "${SERVICE_NAME}" >/dev/null; then
    fail \
        "systemd could not load the installed AquaMind service."
fi


# ============================================================
# IMPORTANT SAFETY BOUNDARY
# ============================================================
#
# Do not automatically start or enable the service here.
#
# Phase 9F.4D will verify:
#
# - runtime environment
# - database reachability
# - Python environment
# - GPIO environment
# - deployment mode
# - hardware safety state
#
# before AquaMind becomes persistent.
# ============================================================


printf '\n'
printf '%s\n' \
    "============================================================"
printf '%s\n' \
    " AQUAMIND SYSTEMD SERVICE INSTALLED"
printf '%s\n' \
    "============================================================"
printf '\n'

printf 'Service user: %s\n' \
    "${SERVICE_USER}"

printf 'Backend root: %s\n' \
    "${BACKEND_ROOT}"

printf 'Service file: %s\n' \
    "${SERVICE_PATH}"

printf '\n'

printf '%s\n' \
    "The service has NOT been started."
printf '%s\n' \
    "The service has NOT been enabled at boot."
printf '%s\n' \
    "Hardware configuration has NOT been changed."

printf '\n'

printf '%s\n' \
    "Deployment preflight must pass before activation."
printf '\n'