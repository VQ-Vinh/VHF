from __future__ import annotations

from collections.abc import Callable
from typing import Any

from prana_core.common.logger import get_logger

logger = get_logger(__name__)


class GpioPttController:
    """Drive a Raspberry Pi BCM GPIO HIGH only while TX audio is playing."""

    def __init__(
        self,
        pin: int = 17,
        *,
        active_high: bool = True,
        device_factory: Callable[..., Any] | None = None,
    ) -> None:
        if device_factory is None:
            from gpiozero import OutputDevice

            device_factory = OutputDevice
        self._pin = pin
        self._device = device_factory(
            pin,
            active_high=active_high,
            initial_value=False,
        )
        logger.info(
            "PTT GPIO ready",
            extra={"gpio_pin": pin, "active_high": active_high},
        )

    def engage(self) -> None:
        self._device.on()
        logger.info("PTT asserted", extra={"gpio_pin": self._pin})

    def release(self) -> None:
        self._device.off()
        logger.info("PTT released", extra={"gpio_pin": self._pin})

    def close(self) -> None:
        try:
            self.release()
        finally:
            self._device.close()
