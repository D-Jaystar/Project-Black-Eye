## capture/media_muxer.py
## Combines a raw H.264 video stream and a WAV audio file into a single .mp4
## container using FFmpeg as a subprocess — no heavyweight Python AV library needed.
## The mux runs in a background daemon thread so it never blocks the main event loop.

import logging
import shutil
import subprocess
import threading
from pathlib import Path
from typing import Callable, Optional


## Callback type: invoked when muxing completes, receives the final mp4 path or None on failure
MuxDoneCallback = Callable[[Optional[str]], None]


class MediaMuxer:
    ## Merges an H.264 video file and a WAV audio file into an MP4 container via FFmpeg.

    def __init__(self) -> None:
        ## Guard Clause: ffmpeg must be present on PATH
        if shutil.which("ffmpeg") is None:
            raise EnvironmentError(
                "[ERROR] ffmpeg is not installed or not on PATH. "
                "Install it with: sudo apt install ffmpeg"
            )

        self._active_thread: Optional[threading.Thread] = None
        logging.info("MediaMuxer initialized (ffmpeg found on PATH)")

    @property
    def is_busy(self) -> bool:
        ## True while a mux operation is running in the background thread
        return self._active_thread is not None and self._active_thread.is_alive()

    def mux(
        self,
        audio_path: str,
        video_path: str,
        output_path: str,
        on_done: Optional[MuxDoneCallback] = None,
    ) -> bool:
        ## Guard Clause: reject if already muxing
        if self.is_busy:
            logging.warning("mux() rejected: a mux operation is already in progress.")
            return False

        ## Guard Clause: audio file must exist
        if not Path(audio_path).is_file():
            logging.error(f"mux() rejected: audio file not found: {audio_path}")
            return False

        ## Guard Clause: video file must exist
        if not Path(video_path).is_file():
            logging.error(f"mux() rejected: video file not found: {video_path}")
            return False

        ## Guard Clause: output must be a non-empty string
        if not isinstance(output_path, str) or not output_path.strip():
            raise TypeError("[ERROR] output_path must be a non-empty string.")

        ## Guard Clause: output must end in .mp4
        if Path(output_path).suffix.lower() != ".mp4":
            raise ValueError(
                f"[ERROR] output_path must end in .mp4, got: '{Path(output_path).suffix}'"
            )

        ## Ensure the output directory exists
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        ## Dispatch the blocking ffmpeg call onto a daemon thread
        self._active_thread = threading.Thread(
            target=self._mux_worker,
            args=(audio_path, video_path, output_path, on_done),
            daemon=True,
            name="MediaMuxer-Thread",
        )
        self._active_thread.start()
        logging.info(
            f"Mux started: {Path(video_path).name} + {Path(audio_path).name} → {Path(output_path).name}"
        )
        return True

    def _mux_worker(
        self,
        audio_path: str,
        video_path: str,
        output_path: str,
        on_done: Optional[MuxDoneCallback],
    ) -> None:
        ## Build the FFmpeg command:
        ##   -i <video>          raw H.264 input
        ##   -i <audio>          WAV audio input
        ##   -c:v copy           re-wrap video without re-encoding (fast, lossless)
        ##   -c:a aac            transcode WAV → AAC (MP4-compatible audio codec)
        ##   -movflags +faststart place MP4 index at front (better for streaming)
        ##   -y                  overwrite output without prompting
        command = [
            "ffmpeg",
            "-i", video_path,
            "-i", audio_path,
            "-c:v", "copy",
            "-c:a", "aac",
            "-movflags", "+faststart",
            "-y",
            output_path,
        ]

        try:
            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=120,  ## Safety timeout: abort if ffmpeg hangs for >2 minutes
            )

            if result.returncode != 0:
                ## Decode ffmpeg's stderr for a readable error message
                error_msg = result.stderr.decode(errors="replace").strip()
                logging.error(f"FFmpeg mux failed (exit {result.returncode}): {error_msg}")
                _invoke_callback(on_done, None)
                return

            logging.info(f"Mux complete → {Path(output_path).name}")
            _invoke_callback(on_done, output_path)

        except subprocess.TimeoutExpired:
            logging.error("FFmpeg mux timed out after 120 seconds — process may have hung.")
            _invoke_callback(on_done, None)

        except Exception as exc:
            logging.error(f"Unexpected error during mux: {exc}")
            _invoke_callback(on_done, None)


def _invoke_callback(callback: Optional[MuxDoneCallback], result: Optional[str]) -> None:
    ## Helper: safely call the on_done callback if one was provided
    if callback is None:
        return
    try:
        callback(result)
    except Exception as exc:
        logging.error(f"Error in mux on_done callback: {exc}")
