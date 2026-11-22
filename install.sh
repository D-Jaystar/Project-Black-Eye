#!/usr/bin/env bash
# install.sh — BlackEye automated setup script for Raspberry Pi
# Run once after cloning the repo: bash install.sh

set -euo pipefail

echo ""
echo "=============================="
echo "  BlackEye — Installation"
echo "=============================="
echo ""

# ── 1. System packages ────────────────────────────────────────────────────────
echo "[1/5] Installing system packages..."
sudo apt-get update -qq
sudo apt-get install -y ffmpeg python3-pip python3-picamera2

# ── 2. Python dependencies ────────────────────────────────────────────────────
echo "[2/5] Installing Python dependencies..."
pip3 install --upgrade pip
pip3 install -r requirements.txt

# ── 3. Environment file ───────────────────────────────────────────────────────
echo "[3/5] Setting up environment configuration..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "  → .env created from template. Edit it now to add your Telegram credentials:"
    echo "      nano .env"
else
    echo "  → .env already exists, skipping."
fi

# ── 4. Recordings directory ───────────────────────────────────────────────────
echo "[4/5] Creating recordings directory..."
mkdir -p recordings

# ── 5. Systemd service ────────────────────────────────────────────────────────
echo "[5/5] Installing systemd service..."
sudo cp blackeye.service /etc/systemd/system/blackeye.service
sudo systemctl daemon-reload
sudo systemctl enable blackeye.service
echo "  → Service installed and enabled on boot."
echo "  → Start now with: sudo systemctl start blackeye"
echo "  → View logs with: journalctl -u blackeye -f"

echo ""
echo "=============================="
echo "  Installation complete! ✅"
echo "=============================="
echo ""
echo "Next steps:"
echo "  1. Edit .env and add your Telegram token + chat ID"
echo "  2. sudo systemctl start blackeye"
echo ""
