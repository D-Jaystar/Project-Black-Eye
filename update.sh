#!/usr/bin/env bash
# update.sh — BlackEye remote update script
# Pulls the latest code from GitHub, updates Python deps, and restarts the service.
# Called by: systemd nightly timer, or the Telegram /update command.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="/tmp/blackeye-update.log"
TELEGRAM_SCRIPT="${SCRIPT_DIR}/scripts/notify_update.py"

## ── Helper: send Telegram message ────────────────────────────────────────────
send_telegram() {
    local message="$1"
    if [ -f "${TELEGRAM_SCRIPT}" ] && [ -f "${SCRIPT_DIR}/.env" ]; then
        source "${SCRIPT_DIR}/.env"
        python3 "${TELEGRAM_SCRIPT}" "${BLACKEYE_TELEGRAM_TOKEN}" "${BLACKEYE_TELEGRAM_CHAT_ID}" "${message}" || true
    fi
}

## ── Main update flow ─────────────────────────────────────────────────────────
{
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting BlackEye update..."

    ## Step 1: Pull latest code
    echo "[1/3] git pull..."
    git -C "${SCRIPT_DIR}" fetch origin main
    LOCAL=$(git -C "${SCRIPT_DIR}" rev-parse HEAD)
    REMOTE=$(git -C "${SCRIPT_DIR}" rev-parse origin/main)

    if [ "${LOCAL}" = "${REMOTE}" ]; then
        echo "  → Already up to date (${LOCAL:0:7}). No restart needed."
        send_telegram "✅ <b>BlackEye Update</b>: Al up-to-date (<code>${LOCAL:0:7}</code>). Geen herstart nodig."
        exit 0
    fi

    git -C "${SCRIPT_DIR}" pull --ff-only origin main
    NEW_HASH=$(git -C "${SCRIPT_DIR}" rev-parse --short HEAD)
    echo "  → Updated to ${NEW_HASH}"

    ## Step 2: Update Python dependencies (only if requirements.txt changed)
    echo "[2/3] Updating Python dependencies..."
    pip3 install -q -r "${SCRIPT_DIR}/requirements.txt"

    ## Step 3: Restart service
    echo "[3/3] Restarting blackeye service..."
    sudo systemctl restart blackeye

    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Update complete → ${NEW_HASH}"
    send_telegram "✅ <b>BlackEye Update</b> voltooid!\n\nNieuwe versie: <code>${NEW_HASH}</code>\nHerstart: succesvol"

} >> "${LOG_FILE}" 2>&1
