## main.py
## Entry point for BlackEye — wires all modules together and starts the event loop.

import logging
import signal
from datetime import datetime

from config import settings
from core.state_machine import StateMachine
from core.controller import Controller
from capture.audio_recorder import AudioRecorder
from capture.video_recorder import VideoRecorder

## Configure logging once, here, for the entire application
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
    format=settings.LOG_FORMAT,
)


def _build_output_path(template: str) -> str:
    ## Resolve filename template by injecting the current timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = template.format(timestamp=timestamp)
    return str(settings.RECORDINGS_DIR / filename)


def main() -> None:
    ## Ensure the recordings directory exists before any session starts
    settings.RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)

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
    controller = Controller(
        state_machine=state_machine,
        audio_recorder=audio_recorder,
        video_recorder=video_recorder,
        pir_pin=settings.PIR_GPIO_PIN,
        audio_output_path=_build_output_path(settings.AUDIO_FILENAME_TEMPLATE),
        video_output_path=_build_output_path(settings.VIDEO_FILENAME_TEMPLATE),
    )

    ## Arm the system on startup
    controller.arm()

    ## Graceful shutdown on SIGINT (Ctrl+C) or SIGTERM
    def _handle_shutdown(signum, frame) -> None:
        logging.info(f"Received signal {signum} — shutting down.")
        controller.shutdown()

    signal.signal(signal.SIGINT, _handle_shutdown)
    signal.signal(signal.SIGTERM, _handle_shutdown)

    logging.info("BlackEye is running. Waiting for events...")

    ## Non-blocking event loop: pause the main thread without busy-waiting
    signal.pause()


if __name__ == "__main__":
    main()
