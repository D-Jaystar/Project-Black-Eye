## core/controller.py
## Links hardware triggers to state transitions and manages the capture lifecycle.

import logging
from typing import Optional
from core.state_machine import StateMachine, SystemState
from detector.pir_sensor import PirMotionDetector
from capture.audio_recorder import AudioRecorder


class Controller:
    ## Orchestrates state transitions, sensor input, and audio capture lifecycle.

    def __init__(
        self,
        state_machine: StateMachine,
        audio_recorder: AudioRecorder,
        pir_pin: int = 17,
        recording_output_path: str = "recordings/capture.wav",
    ) -> None:
        ## Guard Clause: Validate state machine instance
        if not isinstance(state_machine, StateMachine):
            raise TypeError("state_machine must be an instance of StateMachine")

        ## Guard Clause: Validate audio recorder instance
        if not isinstance(audio_recorder, AudioRecorder):
            raise TypeError("audio_recorder must be an instance of AudioRecorder")

        self._state_machine: StateMachine = state_machine
        self._audio_recorder: AudioRecorder = audio_recorder
        self._recording_output_path: str = recording_output_path
        self._last_recording_path: Optional[str] = None

        self._detector: PirMotionDetector = PirMotionDetector(
            pin=pir_pin,
            on_motion_callback=self._handle_motion_detected,
            off_motion_callback=self._handle_motion_stopped,
        )

        logging.info("Controller initialized")

    def _handle_motion_detected(self) -> None:
        ## Guard Clause: Only act when strictly ARMED
        if self._state_machine.current_state != SystemState.ARMED:
            logging.info(f"Motion ignored: system is in {self._state_machine.current_state.name} state.")
            return

        logging.info("Motion detected while ARMED — starting capture and transitioning to RECORDING.")
        self._state_machine.transition_to(SystemState.RECORDING)
        self._audio_recorder.start_recording(self._recording_output_path)

    def _handle_motion_stopped(self) -> None:
        ## Guard Clause: Only act when strictly RECORDING
        if self._state_machine.current_state != SystemState.RECORDING:
            logging.info(f"Motion-stop ignored: system is in {self._state_machine.current_state.name} state.")
            return

        logging.info("Motion stopped — finalising capture and transitioning to ALERTING.")
        self._last_recording_path = self._audio_recorder.stop_recording()
        self._state_machine.transition_to(SystemState.ALERTING)

    def acknowledge_alert(self) -> bool:
        ## Guard Clause: Only acknowledge from ALERTING state
        if self._state_machine.current_state != SystemState.ALERTING:
            logging.warning("acknowledge_alert ignored: system is not in ALERTING state.")
            return False

        logging.info(f"Alert acknowledged. Recording was saved to: {self._last_recording_path}")
        self._last_recording_path = None
        return self._state_machine.transition_to(SystemState.ARMED)

    def arm(self) -> bool:
        if not self._state_machine.transition_to(SystemState.ARMED):
            logging.warning("Failed to arm system: Transition rejected.")
            return False

        self._detector.start()
        logging.info("System armed. Motion detection active.")
        return True

    def disarm(self) -> bool:
        ## Guard Clause: only stop detector after a successful state transition
        if not self._state_machine.transition_to(SystemState.DISARMED):
            logging.warning("Failed to disarm system: Transition rejected.")
            return False

        self._detector.stop()

        ## Ensure any active recording is cleanly flushed on disarm
        if self._audio_recorder.is_recording:
            logging.warning("Disarming while recording is active — stopping recorder.")
            self._audio_recorder.stop_recording()

        logging.info("System disarmed. Motion detection off.")
        return True

    def shutdown(self) -> bool:
        logging.info("Shutting down system.")
        return self.disarm()