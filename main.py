## main.py
## Entry point for BlackEye — wires all modules together and starts the event loop.

import logging
import signal

from core.state_machine import StateMachine
from core.controller import Controller
from capture.audio_recorder import AudioRecorder

## Configure logging once, here, for the entire application
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)


def main() -> None:
    ## Wire up the dependency graph
    state_machine = StateMachine()
    audio_recorder = AudioRecorder()
    controller = Controller(
        state_machine=state_machine,
        audio_recorder=audio_recorder,
        pir_pin=17,
        recording_output_path="recordings/capture.wav",
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
