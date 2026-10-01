"""
core/state_machine.py
Defines the core operational states and state machine logic for BlackEye.
"""

from enum import Enum, auto
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

class SystemState(Enum):
##Represents the operational states of BlackEye
    DISARMED = auto() #Standby: system off
    ARMED = auto()    #Surveillance active
    RECORDING = auto()#Motion detected, video and audio on
    ALERTING = auto() # Capture finished alerting owner

class StateMachine:
    ## State Tracker controlling transitions

    def __init__(self, initial_state=SystemState.DISARMED) -> None:
        ## Guard clause for initial state
        if not isinstance(initial_state, SystemState):
            raise TypeError("initial_state must be an instance of SystemState")

        self._current_state: SystemState = initial_state
        logging.info(f"State machine initialised in state:{self._current_state.name}")


    @property
    def current_state(self) -> SystemState:
        #getter for the current state
        return self._current_state


    def transition_to(self, new_state: SystemState) -> bool:
        #guard clause for valid state
        if not isinstance(new_state, SystemState):
            raise TypeError("new_state must be an instance of SystemState")

        # guard for when already in the state that is requested
        if self.current_state == new_state:
            logging.warning(f"State transition ignored: already in {new_state.name}")
            return False

        ## Permitted transition map
        valid_transitions = {
            SystemState.DISARMED: {SystemState.ARMED},
            SystemState.ARMED: {SystemState.DISARMED, SystemState.RECORDING},
            SystemState.RECORDING: {SystemState.DISARMED, SystemState.ALERTING},
            SystemState.ALERTING: {SystemState.ARMED, SystemState.DISARMED},
        }

        ## gaurd clause to see if its permitted
        allowed = valid_transitions.get(self._current_state, set())
        if new_state not in allowed:
            logging.error(f"Illegal state transition: {self._current_state.name} -> {new_state.name}")
            return False

        ## Update state
        previous_state = self._current_state
        self._current_state = new_state
        logging.info(f"State machine transitioned from {previous_state} to {new_state.name}")
        return True