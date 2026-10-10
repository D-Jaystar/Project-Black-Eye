## core/controller.py
## Links hardware triggers to state transitions.

import logging
from core.state_machine import StateMachine, SystemState
from detector.pir_sensor import PirMotionDetector




class Controller:
    ## Orchestrates state transitions and manages sensory hardware interfaces.

    def __init__(self, state_machine: StateMachine, pir_pin: int = 17) -> None:
        ## Guard Clause: Validate state machine instance
        if not isinstance(state_machine, StateMachine):
            raise TypeError("state_machine must be an instance of StateMachine")

        self._state_machine: StateMachine = state_machine
        self._detector: PirMotionDetector = PirMotionDetector(
            pin=pir_pin,
            on_motion_callback=self._handle_motion_detected
        )

        logging.info("Controller initialized")

    def _handle_motion_detected(self) -> None:
        ## Guard Clause: Only transition if system is strictly ARMED
        if self._state_machine.current_state != SystemState.ARMED:
            logging.info(f"Motion ignored: system is in {self._state_machine.current_state.name} state.")
            return

        logging.info("Motion Detected while ARMED. Initializing Transition.")
        self._state_machine.transition_to(SystemState.RECORDING)

    def arm(self) -> bool:
        if not self._state_machine.transition_to(SystemState.ARMED):
            logging.warning("Failed to arm system: Transition rejected.")
            return False

        self._detector.start()
        logging.info("System armed. MotionDetection on")
        return True


    def disarm(self) -> bool:
        ## Guard Clause: only stop detector after a successful state transition
        if not self._state_machine.transition_to(SystemState.DISARMED):
            logging.warning("Failed to disarm system: Transition rejected.")
            return False

        self._detector.stop()
        logging.info("System disarmed. MotionDetection off")
        return True

    def shutdown(self) -> bool:
        logging.info("Shutting down system.")
        return self.disarm()