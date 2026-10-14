## capture/video_recorder.py
## Background video capture engine for BlackEye using Picamera2 / libcamera.
## Mirrors the AudioRecorder interface: start/stop with non-blocking threading.

import logging
import threading
from pathlib import Path
from typing import Optional

## Picamera2 is only available on Raspberry Pi — import is guarded so the rest
## of the codebase can still be imported and tested on non-Pi hardware.
try:
    from picamera2 import Picamera2
    from picamera2.encoders import H264Encoder
    from picamera2.outputs import FileOutput
    _PICAMERA2_AVAILABLE: bool = True
except ImportError:
    _PICAMERA2_AVAILABLE: bool = False
    logging.warning("picamera2 not available — VideoRecorder will run in stub mode.")


class VideoRecorder:
    ## Captures H.264 video from the Pi camera to a file, asynchronously.

    def __init__(
        self,
        width: int = 1280,
        height: int = 720,
        framerate: int = 30,
    ) -> None:
        ## Guard Clause: width must be a positive integer
        if not isinstance(width, int) or width <= 0:
            raise ValueError(f"[ERROR] Invalid width: {width}. Must be a positive integer.")

        ## Guard Clause: height must be a positive integer
        if not isinstance(height, int) or height <= 0:
            raise ValueError(f"[ERROR] Invalid height: {height}. Must be a positive integer.")

        ## Guard Clause: framerate must be a positive integer
        if not isinstance(framerate, int) or framerate <= 0:
            raise ValueError(f"[ERROR] Invalid framerate: {framerate}. Must be a positive integer.")

        self._width: int = width
        self._height: int = height
        self._framerate: int = framerate
        self._camera: Optional[object] = None
        self._is_recording: bool = False
        self._current_output_path: Optional[Path] = None
        self._lock: threading.Lock = threading.Lock()

        logging.info(
            f"VideoRecorder initialized ({self._width}x{self._height} @ {self._framerate}fps)"
        )

    @property
    def is_recording(self) -> bool:
        ## Thread-safe getter for the active recording state
        with self._lock:
            return self._is_recording

    def start_recording(self, output_path: str) -> bool:
        ## Guard Clause: reject if picamera2 is not available
        if not _PICAMERA2_AVAILABLE:
            logging.error("start_recording rejected: picamera2 is not installed.")
            return False

        ## Guard Clause: reject if already recording
        if self.is_recording:
            logging.warning("start_recording rejected: recording is already in progress.")
            return False

        ## Guard Clause: validate output path and extension
        if not isinstance(output_path, str) or not output_path.strip():
            raise TypeError("[ERROR] output_path must be a non-empty string.")

        target_file = Path(output_path)
        if target_file.suffix.lower() not in (".h264", ".mp4"):
            raise ValueError(
                f"[ERROR] Unsupported video container: '{target_file.suffix}'. Must be .h264 or .mp4"
            )

        ## Ensure parent directory exists
        target_file.parent.mkdir(parents=True, exist_ok=True)

        ## Initialise and configure camera
        self._camera = Picamera2()
        video_config = self._camera.create_video_configuration(
            main={"size": (self._width, self._height)},
        )
        self._camera.configure(video_config)

        encoder = H264Encoder()
        output = FileOutput(str(target_file))

        self._camera.start_recording(encoder, output)

        with self._lock:
            self._is_recording = True
            self._current_output_path = target_file

        logging.info(f"Video recording started: {target_file.name}")
        return True

    def stop_recording(self) -> Optional[str]:
        ## Guard Clause: reject stop if not recording
        if not self.is_recording or self._camera is None:
            logging.warning("stop_recording rejected: no active video recording session found.")
            return None

        ## Stop the encoder and release the camera resource
        self._camera.stop_recording()
        self._camera.close()
        self._camera = None

        with self._lock:
            self._is_recording = False
            recorded_path = str(self._current_output_path) if self._current_output_path else None

        logging.info(f"Video recording stopped and saved to: {recorded_path}")
        return recorded_path
