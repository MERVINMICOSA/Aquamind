#!/usr/bin/env bash

set -Eeuo pipefail


# ============================================================
# AQUAMIND
# RASPBERRY PI 5 PROVISIONING
# ============================================================
#
# Purpose:
#
# - verify the deployment machine is the intended Pi platform;
# - install required OS-level Python/GPIO utilities;
# - create an isolated Python virtual environment;
# - install AquaMind Raspberry Pi dependencies;
# - verify required Python GPIO imports;
# - report GPIO environment information without assigning pins;
#
# This script deliberately DOES NOT:
#
# - enable AquaMind hardware control;
# - assign BCM GPIO pins;
# - choose a gpiochip;
# - configure relay polarity;
# - configure DS18B20 device IDs;
# - enable the Linux 1-Wire interface;
# - modify physical hardware mappings.
#
# Those actions belong to physical commissioning after the
# final hardware configuration is known.
# ============================================================


# ============================================================
# OUTPUT HELPERS
# ============================================================


info() {
    printf '\n[AquaMind] %s\n' "$1"
}


warn() {
    printf '\n[AquaMind] WARNING: %s\n' "$1" >&2
}


fail() {
    printf '\n[AquaMind] ERROR: %s\n' "$1" >&2
    exit 1
}


# ============================================================
# SCRIPT / PROJECT LOCATION
# ============================================================


SCRIPT_DIR="$(
    cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
    pwd
)"

PROJECT_ROOT="$(
    cd -- "${SCRIPT_DIR}/.."
    pwd
)"


REQUIREMENTS_FILE="${PROJECT_ROOT}/requirements-pi.txt"

VENV_DIR="${VENV_DIR:-${PROJECT_ROOT}/.venv}"

PYTHON_BIN="${PYTHON_BIN:-python3}"


# ============================================================
# PLATFORM VALIDATION
# ============================================================


info "Validating deployment platform..."


if [[ "$(uname -s)" != "Linux" ]]; then
    fail "This provisioning script must run on Linux."
fi


MACHINE="$(uname -m)"


case "${MACHINE}" in
    aarch64|armv7l)
        ;;
    *)
        fail \
            "Unsupported CPU architecture '${MACHINE}'. Expected aarch64 or armv7l."
        ;;
esac


# ============================================================
# RASPBERRY PI MODEL VALIDATION
# ============================================================


PI_MODEL=""


if [[ -r /proc/device-tree/model ]]; then
    PI_MODEL="$(
        tr -d '\0' < /proc/device-tree/model
    )"
fi


if [[ -z "${PI_MODEL}" ]]; then
    fail \
        "Unable to identify the Raspberry Pi model from /proc/device-tree/model."
fi


case "${PI_MODEL}" in
    *"Raspberry Pi 5"*)
        ;;
    *)
        fail \
            "This deployment profile targets Raspberry Pi 5. Detected: ${PI_MODEL}"
        ;;
esac


info "Detected hardware: ${PI_MODEL}"
info "Detected architecture: ${MACHINE}"


# ============================================================
# PROJECT FILE VALIDATION
# ============================================================


if [[ ! -f "${REQUIREMENTS_FILE}" ]]; then
    fail \
        "Missing Raspberry Pi requirements file: ${REQUIREMENTS_FILE}"
fi


if [[ ! -f "${PROJECT_ROOT}/requirements.txt" ]]; then
    fail \
        "Missing base requirements file: ${PROJECT_ROOT}/requirements.txt"
fi


# ============================================================
# PRIVILEGE SAFETY
# ============================================================


if [[ "${EUID}" -eq 0 ]]; then
    fail \
        "Do not run this script directly as root. Run it as the normal AquaMind/Pi user; sudo will be requested only for OS packages."
fi


if ! command -v sudo >/dev/null 2>&1; then
    fail "sudo is required for OS package provisioning."
fi


if ! command -v apt-get >/dev/null 2>&1; then
    fail \
        "apt-get was not found. This provisioning profile expects Raspberry Pi OS/Debian."
fi


# ============================================================
# OS PACKAGES
# ============================================================


info "Refreshing Raspberry Pi OS package metadata..."

sudo apt-get update


info "Installing required OS packages..."

sudo apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    gpiod


# ============================================================
# PYTHON VALIDATION
# ============================================================


if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
    fail \
        "Python executable '${PYTHON_BIN}' was not found after package installation."
fi


PYTHON_VERSION="$(
    "${PYTHON_BIN}" \
        -c 'import sys; print(".".join(map(str, sys.version_info[:3])))'
)"


info "Detected Python: ${PYTHON_VERSION}"


# AquaMind uses Python language features requiring Python 3.10+
# such as PEP 604 union syntax.


if ! "${PYTHON_BIN}" - <<'PY'
import sys

if sys.version_info < (3, 10):
    raise SystemExit(1)
PY
then
    fail \
        "AquaMind requires Python 3.10 or newer. Detected ${PYTHON_VERSION}."
fi


# ============================================================
# VIRTUAL ENVIRONMENT
# ============================================================


info "Preparing Python virtual environment: ${VENV_DIR}"


if [[ ! -d "${VENV_DIR}" ]]; then
    "${PYTHON_BIN}" -m venv "${VENV_DIR}"
fi


VENV_PYTHON="${VENV_DIR}/bin/python"


if [[ ! -x "${VENV_PYTHON}" ]]; then
    fail \
        "Virtual environment Python executable was not created correctly."
fi


# ============================================================
# PYTHON PACKAGING TOOLS
# ============================================================


info "Updating virtual-environment packaging tools..."

"${VENV_PYTHON}" -m pip install \
    --upgrade \
    pip \
    setuptools \
    wheel


# ============================================================
# AQUAMIND DEPENDENCIES
# ============================================================


info "Installing AquaMind Raspberry Pi dependencies..."

"${VENV_PYTHON}" -m pip install \
    -r "${REQUIREMENTS_FILE}"


# ============================================================
# PYTHON IMPORT PREFLIGHT
# ============================================================
#
# Import only.
#
# Do NOT instantiate LGPIOFactory here because constructing the
# real GPIO backend belongs to runtime/commissioning and could
# touch the GPIO controller.
# ============================================================


info "Verifying Raspberry Pi GPIO Python dependencies..."

"${VENV_PYTHON}" - <<'PY'
import sys

import gpiozero
import lgpio

from gpiozero.pins.lgpio import LGPIOFactory


print(
    "[AquaMind] Python GPIO imports OK"
)

print(
    f"[AquaMind] Python runtime: "
    f"{sys.version.split()[0]}"
)

print(
    f"[AquaMind] GPIO Zero: "
    f"{getattr(gpiozero, '__version__', 'installed')}"
)

print(
    "[AquaMind] lgpio module: installed"
)

print(
    "[AquaMind] LGPIOFactory import: OK"
)
PY


# ============================================================
# GPIO GROUP CHECK
# ============================================================
#
# We report permissions but do not mutate user/group membership
# automatically.
# ============================================================


if getent group gpio >/dev/null 2>&1; then

    if id -nG "${USER}" \
        | tr ' ' '\n' \
        | grep -qx "gpio"
    then
        info \
            "User '${USER}' is a member of the gpio group."
    else
        warn \
            "User '${USER}' is not currently a member of the gpio group. This must be resolved before hardware commissioning."
    fi

else
    warn \
        "No gpio group was detected. Hardware permissions must be verified during commissioning."
fi


# ============================================================
# GPIO CHIP DISCOVERY
# ============================================================
#
# This is informational only.
#
# Raspberry Pi 5 gpiochip numbering must be verified on the
# actual deployment system. We deliberately do not write the
# detected value into AquaMind configuration here.
# ============================================================


info "Detected Linux GPIO chips:"


if command -v gpiodetect >/dev/null 2>&1; then

    if ! gpiodetect; then
        warn \
            "gpiodetect could not enumerate GPIO controllers. Recheck permissions and OS GPIO support before commissioning."
    fi

else
    warn \
        "gpiodetect is unavailable even though the gpiod package was requested."
fi


# ============================================================
# SAFETY REMINDER
# ============================================================


printf '\n'
printf '%s\n' \
    "============================================================"
printf '%s\n' \
    " AQUAMIND RASPBERRY PI SOFTWARE PROVISIONING COMPLETE"
printf '%s\n' \
    "============================================================"
printf '\n'

printf '%s\n' \
    "Hardware control has NOT been enabled."
printf '%s\n' \
    "No GPIO pins have been assigned."
printf '%s\n' \
    "No relay polarity has been assumed."
printf '%s\n' \
    "No DS18B20 device ID has been configured."
printf '%s\n' \
    "No physical sensor interface has been guessed."
printf '\n'

printf '%s\n' \
    "Virtual environment:"
printf '  %s\n' \
    "${VENV_DIR}"

printf '\n'

printf '%s\n' \
    "Keep HARDWARE_ENABLED=false until physical commissioning."
printf '\n'