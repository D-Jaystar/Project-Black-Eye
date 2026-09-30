"""
core/state_machine.py
Defines the core operational states and state machine logic for BlackEye.
"""

from enum import Enum, auto
from typing import final

class SystemState(Enum):
##Represents the operational states of BlackEye
    DISARMED = auto() #Standby: system off
    ARMED = auto()    #Surveillance active
    RECORDING = auto()#Motion detected, video and audio on
    ALERTING = auto() # Capture finished alerting owner

