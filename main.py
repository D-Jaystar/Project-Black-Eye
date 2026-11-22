## main.py
## Entry point for BlackEye — wires all modules together and starts the event loop.

import logging
import os
import platform
import signal
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from config import settings
from core.state_machine import StateMachine
from core.controller import Controller
from capture.audio_recorder import AudioRecorder
from capture.video_recorder import VideoRecorder
from capture.media_muxer import MediaMuxer
from notifier.telegram_bot import TelegramNotifier

## Configure logging once, here, for the entire application
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
    format=settings.LOG_FORMAT,
)

## Absolute path to the project root (works regardless of cwd)
PROJECT_ROOT: Path = Path(__file__).resolve().parent


def _make_path(template: str, session_ts: str) -> str:
    ## Resolve filename template by injecting the session timestamp
    return str(settings.RECORDINGS_DIR / template.format(timestamp=session_ts))


# ── Telegram command handlers ──────────────────────────────────────────────────

def _cmd_status(state_machine: StateMachine) -> str:
    ## /status — returns current system state + uptime info
    import time
    uptime_seconds = int(time.monotonic())
    hours, remainder = divmod(uptime_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    state = state_machine.current_state.name
    return (
        f"📡 <b>BlackEye Status</b>\n\n"
        f"State: <code>{state}</code>\n"
        f"Uptime: <code>{hours:02d}:{minutes:02d}:{seconds:02d}</code>\n"
        f"Host: <code>{platform.node()}</code>\n"
        f"Python: <code>{sys.version.split()[0]}</code>"
    )


def _cmd_update() -> str:
    ## /update — pulls latest code from GitHub and restarts the service.
    ## The update script runs detached so the restart survives killing this process.
    update_script = PROJECT_ROOT / "update.sh"

    ## Guard Clause: update script must exist
    if not update_script.is_file():
        return "❌ <code>update.sh</code> not found on device."

    ## Launch update detached — it will restart this service, so we reply first
    subprocess.Popen(
        ["bash", "-c", f"sleep 3 && bash {update_script}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    return (
        "🔄 <b>Update gestart!</b>\n\n"
        "De Pi trekt nu de laatste code van GitHub.\n"
        "BlackEye herstart automatisch na ±30 seconden.\n"
        "Je ontvangt een bevestiging zodra het klaar is."
    )


def _cmd_heartbeat_now(notifier: TelegramNotifier) -> str:
    ## /heartbeat — manual on-demand heartbeat
    return _build_heartbeat_message()


def _build_heartbeat_message() -> str:
    import time
    uptime_seconds = int(time.monotonic())
    hours, remainder = divmod(uptime_seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    return (
        f"💚 <b>BlackEye Heartbeat</b>\n\n"
        f"Systeem is actief en bewaakt.\n"
        f"Tijdstip: <code>{now}</code>\n"
        f"Uptime: <code>{hours}u {minutes}m</code>"
    )


def _start_heartbeat_thread(notifier: TelegramNotifier) -> None:
    ## Sends a daily heartbeat at 08:00 to confirm the device is alive.
    import time

    def _loop() -> None:
        while True:
            now = datetime.now()
            ## Calculate seconds until next 08:00
            next_8am = now.replace(hour=8, minute=0, second=0, microsecond=0)
            if now >= next_8am:
                next_8am = next_8am.replace(day=next_8am.day + 1)
            sleep_seconds = (next_8am - now).total_seconds()
            time.sleep(sleep_seconds)
            notifier.send_alert(_build_heartbeat_message())

    thread = threading.Thread(target=_loop, daemon=True, name="Heartbeat-Thread")
    thread.start()
    logging.info("Heartbeat thread started — daily ping at 08:00.")


# ── Entry point ────────────────────────────────────────────────────────────────

def main() -> None:
    import threading

    ## Ensure the recordings directory exists before any session starts
    settings.RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)

    ## Generate a single shared timestamp so all files for one session share the same stem
    session_ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    ## Wire up the dependency graph
    state_machine = StateMachine()
    audio_recorder = AudioRecorder(
        sample_rate=settings.AUDIO_SAMPLE_RATE,
        channels=settings.AUDIO_CHANNELS,
    )
    video_recorder = VideoRecorder(
        width=settings.VIDEO_WIDTH,
        height=settings.VIDEO_HEIGHT,
        framerate=settings.VIDEO_FRAMERATE,
    )
    media_muxer = MediaMuxer()
    notifier = TelegramNotifier.from_env()

    controller = Controller(
        state_machine=state_machine,
        audio_recorder=audio_recorder,
        video_recorder=video_recorder,
        media_muxer=media_muxer,
        notifier=notifier,
        pir_pin=settings.PIR_GPIO_PIN,
        audio_output_path=_make_path(settings.AUDIO_FILENAME_TEMPLATE, session_ts),
        video_output_path=_make_path(settings.VIDEO_FILENAME_TEMPLATE, session_ts),
        muxed_output_path=_make_path(settings.MUXED_FILENAME_TEMPLATE, session_ts),
    )

    ## Register Telegram commands
    notifier.register_command("/status",    lambda: _cmd_status(state_machine))
    notifier.register_command("/update",    _cmd_update)
    notifier.register_command("/heartbeat", lambda: _build_heartbeat_message())

    ## Start the command listener (long-polling) and heartbeat
    notifier.start_command_listener()
    _start_heartbeat_thread(notifier)

    ## Arm the system on startup
    controller.arm()
    notifier.send_alert(
        f"🟢 <b>BlackEye</b> is opgestart en bewaakt.\n"
        f"<code>{datetime.now().strftime('%Y-%m-%d %H:%M')}</code>\n\n"
        f"Beschikbare commando's:\n"
        f"/status — systeemstatus\n"
        f"/update — update + herstart\n"
        f"/heartbeat — ping"
    )

    ## Graceful shutdown on SIGINT (Ctrl+C) or SIGTERM
    def _handle_shutdown(signum, frame) -> None:
        logging.info(f"Received signal {signum} — shutting down.")
        notifier.stop_command_listener()
        controller.shutdown()

    signal.signal(signal.SIGINT, _handle_shutdown)
    signal.signal(signal.SIGTERM, _handle_shutdown)

    logging.info("BlackEye is running. Waiting for events...")
    signal.pause()


if __name__ == "__main__":
    main()
