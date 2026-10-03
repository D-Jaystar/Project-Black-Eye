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


    def start(self) -> None:
    ## handler
        if self._is_running:
            logging.info(f"[info] PirMotionDetector already running")
            return

        self._sensor = DigitalInputDevice(pin=self._pin)
        self._sensor.when_activated = self._on_motion_callback

        if self._off_motion_callback is not None:
            self._sensor.when_deactivated =  self._off_motion_callback()

        self._is_running = True
        logging.info(f"[info] PirMotionDetector started on gpio pin {self._pin}")

    def stop(self) -> None:

        if not self._is_running or self._sensor is None:
            logging.warning("PirMotionDetector is not running")
            return

        self._sensor.close()
        self._is_running = False
        self._sensor = None
        logging.info(f"PirMotionDetector stopped on gpio pin {self._pin}")

    @property
    def is_active(self) -> bool:
        return self._is_running

    @property
    def motion_detected(self) -> bool:
        if self._sensor is None:
            return False
        return self._sensor.is_active

