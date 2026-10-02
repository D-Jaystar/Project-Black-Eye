## detector/pir_sensor.py
## Hardware layer for the AM312 Mini-PIR motion sensor.

import logging
from typing import Callable, Optional
from gpiozero import DigitalInputDevice

## Valid GPIO pin range
MIN_GPIO_PIN: int = 0
MAX_GPIO_PIN: int = 27


class PirMotionDetector:
    ## Interrupt-driven motion detector using GPIO pins.

    def __init__(
            self,
            pin: int,
            on_motion_callback: Callable[[], None],
            off_motion_callback: Optional[Callable[[], None]] = None,
    ) -> None:
        ## Guard Clause for pins
        if not isinstance(pin, int) or not (MIN_GPIO_PIN <= pin <= MAX_GPIO_PIN):
            raise ValueError(f"[error] Pin {pin} is not valid, must be between {MIN_GPIO_PIN} and {MAX_GPIO_PIN}")

        ## Guard Clause for mandatory motion callback
        if not callable(on_motion_callback):
            raise TypeError("[error] on_motion_callback must be a callable")

        ## Guard Clause for optional motion stop callback
        if off_motion_callback is not None and not callable(off_motion_callback):
            raise TypeError("[error] off_motion_callback must be a callable")

        self._pin: int = pin
        self._on_motion_callback: Callable[[], None] = on_motion_callback
        self._off_motion_callback: Optional[Callable[[], None]] = off_motion_callback
        self._sensor: Optional[DigitalInputDevice] = None
        self._is_running: bool = False

        logging.info(f"[info] PirMotionDetector initialized for gpio pin {self._pin}")