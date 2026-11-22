#!/usr/bin/env bash
# install.sh — BlackEye automated setup script for Raspberry Pi
# Run once after cloning the repo: bash install.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo ""
echo "=============================="
echo "  BlackEye — Installation"
echo "=============================="
echo ""

# ── 1. System packages ────────────────────────────────────────────────────────
echo "[1/6] Installing system packages..."
sudo apt-get update -qq
sudo apt-get install -y ffmpeg python3-pip python3-picamera2 git

# ── 2. Python dependencies ────────────────────────────────────────────────────
echo "[2/6] Installing Python dependencies..."
pip3 install --upgrade pip
pip3 install -r "${SCRIPT_DIR}/requirements.txt"

# ── 3. Environment file ───────────────────────────────────────────────────────
echo "[3/6] Setting up environment configuration..."
if [ ! -f "${SCRIPT_DIR}/.env" ]; then
    cp "${SCRIPT_DIR}/.env.example" "${SCRIPT_DIR}/.env"
    echo "  → .env created from template."
    echo "  !! Edit it now to add your Telegram credentials: nano ${SCRIPT_DIR}/.env"
else
    echo "  → .env already exists, skipping."
fi

# ── 4. Recordings directory ───────────────────────────────────────────────────
echo "[4/6] Creating recordings directory..."
mkdir -p "${SCRIPT_DIR}/recordings"

# ── 5. Main systemd service ───────────────────────────────────────────────────
echo "[5/6] Installing blackeye.service..."
sudo cp "${SCRIPT_DIR}/blackeye.service" /etc/systemd/system/blackeye.service
sudo systemctl daemon-reload
sudo systemctl enable blackeye.service
echo "  → Main service installed and enabled on boot."

# ── 6. Auto-update systemd timer ─────────────────────────────────────────────
echo "[6/6] Installing nightly auto-update timer..."
sudo cp "${SCRIPT_DIR}/scripts/blackeye-update.service" /etc/systemd/system/blackeye-update.service
sudo cp "${SCRIPT_DIR}/scripts/blackeye-update.timer"   /etc/systemd/system/blackeye-update.timer

## Allow pi user to restart the service without a sudo password
## (required for update.sh to call: sudo systemctl restart blackeye)
SUDOERS_LINE="pi ALL=(ALL) NOPASSWD: /bin/systemctl restart blackeye, /bin/systemctl stop blackeye, /bin/systemctl start blackeye"
SUDOERS_FILE="/etc/sudoers.d/blackeye"
if [ ! -f "${SUDOERS_FILE}" ]; then
    echo "${SUDOERS_LINE}" | sudo tee "${SUDOERS_FILE}" > /dev/null
    sudo chmod 440 "${SUDOERS_FILE}"
    echo "  → Sudoers rule added (passwordless systemctl restart blackeye)."
fi

sudo systemctl daemon-reload
sudo systemctl enable blackeye-update.timer
sudo systemctl start  blackeye-update.timer
echo "  → Auto-update timer installed: runs every night at 03:00."

echo ""
echo "=============================="
echo "  Installation complete! ✅"
echo "=============================="
echo ""
echo "Next steps:"
echo "  1. Edit .env:              nano ${SCRIPT_DIR}/.env"
echo "  2. Start BlackEye:         sudo systemctl start blackeye"
echo "  3. View logs:              journalctl -u blackeye -f"
echo "  4. Check update timer:     systemctl list-timers | grep blackeye"
echo ""
echo "Remote commands (via Telegram to your bot):"
echo "  /status    — view system state + uptime"
echo "  /update    — pull latest code + restart now"
echo "  /heartbeat — manual ping"
echo ""
