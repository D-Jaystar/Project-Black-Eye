## capture/audio_recorder.py
## Background audio recording engine for BlackEye using non-blocking threads.

import logging
import threading
from pathlib import Path
from typing import Optional
import sounddevice as sd
import soundfile as sf




class AudioRecorder:
    ## Captures raw microphone audio and writes to WAV format asynchronously.

    def __init__(self, sample_rate: int = 44100, channels: int = 1) -> None:
        ## Guard Clause 1: Validate sample rate
        if not isinstance(sample_rate, int) or sample_rate <= 0:
            raise ValueError(f"[ERROR] Invalid sample rate: {sample_rate}. Must be a positive integer.")

        ## Guard Clause 2: Validate channels
        if not isinstance(channels, int) or channels not in (1, 2):
            raise ValueError(f"[ERROR] Invalid channels: {channels}. Must be 1 (mono) or 2 (stereo).")

        self._sample_rate: int = sample_rate
        self._channels: int = channels
        self._thread: Optional[threading.Thread] = None
        self._stop_event: threading.Event = threading.Event()
        self._is_recording: bool = False
        self._current_output_path: Optional[Path] = None

        logging.info(f"AudioRecorder initialized (Sample Rate: {self._sample_rate}Hz, Channels: {self._channels})")

    @property
    def is_recording(self) -> bool:
        ## Getter for active recording state
        return self._is_recording

    def start_recording(self, output_path: str) -> bool:
        ## Guard Clause 1: Reject if already recording
        if self._is_recording:
            logging.warning("start_recording rejected: recording is already in progress.")
            return False

        ## Guard Clause 2: Validate output path type and extension
        if not isinstance(output_path, str) or not output_path.strip():
            raise TypeError("[ERROR] output_path must be a non-empty string.")

        target_file = Path(output_path)
        if target_file.suffix.lower() != ".wav":
            raise ValueError(f"[ERROR] Unsupported audio container: '{target_file.suffix}'. Must be .wav")

        ## Ensure parent directory exists
        target_file.parent.mkdir(parents=True, exist_ok=True)
        self._current_output_path = target_file

        ## Reset stop flag and dispatch recording thread
        self._stop_event.clear()
        self._is_recording = True
        self._thread = threading.Thread(target=self._record_worker, args=(target_file,), daemon=True)
        self._thread.start()

        logging.info(f"Audio recording started: {target_file.name}")
        return True

    def _record_worker(self, output_file: Path) -> None:
        ## Worker thread streaming input buffer directly into a WAV file
        try:
            with sf.SoundFile(
                    str(output_file),
                    mode="w",
                    samplerate=self._sample_rate,
                    channels=self._channels,
                    subtype="PCM_16"
            ) as audio_file:
                with sd.InputStream(
                        samplerate=self._sample_rate,
                        channels=self._channels,
                        dtype="int16",
                        ## Always write incoming chunks; _stop_event.wait() below controls stream lifetime
                        callback=lambda indata, frames, time, status: audio_file.write(indata)
                ):
                    self._stop_event.wait()
        except Exception as exc:
            logging.error(f"Error during audio recording stream: {exc}")
        finally:
            self._is_recording = False

    def stop_recording(self) -> Optional[str]:
        ## Guard Clause: Reject stop if inactive
        if not self._is_recording or self._thread is None:
            logging.warning("stop_recording rejected: no active recording session found.")
            return None

        ## Signal thread to exit stream and wait for file flush
        self._stop_event.set()
        self._thread.join(timeout=3.0)

        ## Warn if thread did not terminate within the timeout window
        if self._thread.is_alive():
            logging.error("Audio recording thread did not terminate within timeout. Possible resource leak.")

        self._thread = None
        self._is_recording = False

        recorded_path = str(self._current_output_path) if self._current_output_path else None
        logging.info(f"Audio recording stopped and saved to: {recorded_path}")
        return recorded_path