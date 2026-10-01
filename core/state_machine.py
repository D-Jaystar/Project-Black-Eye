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

        self._currrent_state: SystemState = initial_state
        logging.info(f"State machine initialised in state:{self._currrent_state.name}")


    @property
    def current_state(self) -> SystemState:
        #getter for the current state
        return self._currrent_state
