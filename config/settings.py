## config/settings.py
## Central configuration module for BlackEye.
## All tuneable parameters live here — no magic numbers in other modules.

from pathlib import Path

## ── GPIO ────────────────────────────────────────────────────────────────────

## BCM pin number for the AM312 PIR motion sensor
PIR_GPIO_PIN: int = 17

## ── Audio ────────────────────────────────────────────────────────────────────

## Microphone sample rate in Hz (44100 = CD quality, 16000 = speech minimum)
AUDIO_SAMPLE_RATE: int = 44100

## 1 = mono (sufficient for surveillance audio), 2 = stereo
AUDIO_CHANNELS: int = 1

## ── Storage ──────────────────────────────────────────────────────────────────

## Root directory where all capture sessions are saved
RECORDINGS_DIR: Path = Path("recordings")

## File name template for audio captures; {timestamp} is filled in at runtime
AUDIO_FILENAME_TEMPLATE: str = "audio_{timestamp}.wav"

## File name template for video captures
VIDEO_FILENAME_TEMPLATE: str = "video_{timestamp}.h264"

## File name template for the final muxed clip
MUXED_FILENAME_TEMPLATE: str = "capture_{timestamp}.mp4"

## ── Telegram ─────────────────────────────────────────────────────────────────

## Bot token issued by @BotFather — override via environment variable in production
## Example: export BLACKEYE_TELEGRAM_TOKEN="123456:ABC-DEF..."
TELEGRAM_BOT_TOKEN: str = ""

## Numeric chat ID of the owner who receives alerts
## Example: export BLACKEYE_TELEGRAM_CHAT_ID="987654321"
TELEGRAM_CHAT_ID: str = ""

## ── Logging ──────────────────────────────────────────────────────────────────

## Python logging level: "DEBUG" | "INFO" | "WARNING" | "ERROR"
LOG_LEVEL: str = "INFO"

## Log format string used in main.py basicConfig
LOG_FORMAT: str = "%(asctime)s [%(levelname)s] %(name)s — %(message)s"
