"""Physical button handling via gpiozero.

The Waveshare 2.13" V4 HAT may not have built-in keys, so these are buttons you
wire yourself to spare BCM pins (configured in config.toml). Each button shorts
its pin to GND; gpiozero's internal pull-up handles the rest.

No-ops gracefully when GPIO is unavailable (off-Pi development).
"""
from __future__ import annotations

from typing import Callable, List

from .config import Config


class Buttons:
    def __init__(self, cfg: Config, on_next: Callable, on_prev: Callable,
                 on_mode: Callable):
        self._buttons: List[object] = []
        try:
            from gpiozero import Button  # type: ignore

            specs = [
                (cfg.pin_next, on_next),
                (cfg.pin_prev, on_prev),
                (cfg.pin_mode, on_mode),
            ]
            for pin, handler in specs:
                b = Button(pin, pull_up=True, bounce_time=0.05)
                b.when_pressed = handler
                self._buttons.append(b)
        except Exception as e:
            print(f"[buttons] GPIO unavailable ({e}); buttons disabled")
