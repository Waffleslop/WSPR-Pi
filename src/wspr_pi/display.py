"""e-paper rendering for the Waveshare 2.13" V4 HAT.

Falls back to a console renderer when not running on the Pi (no waveshare_epd /
PIL), so the whole app can be developed and exercised on a laptop.
"""
from __future__ import annotations

from typing import List, Optional

from .models import Decode


class Display:
    def __init__(self, page_size: int = 5):
        self.page_size = page_size
        self._epd = None
        try:
            from waveshare_epd import epd2in13_V4  # type: ignore

            self._epd = epd2in13_V4.EPD()
            self._epd.init()
            self._epd.Clear(0xFF)
        except Exception as e:  # not on Pi, or lib missing
            print(f"[display] e-paper unavailable ({e}); using console fallback")

    def render(self, decodes: List[Decode], page: int, mode: str = "WSPR",
               status: str = "") -> None:
        if self._epd is None:
            self._render_console(decodes, page, mode, status)
        else:
            self._render_epaper(decodes, page, mode, status)

    @staticmethod
    def _fmt(d: Decode) -> str:
        dist = f"{d.distance_km:.0f}km" if d.distance_km is not None else "--"
        line = f"{d.callsign} {d.grid} {d.snr_int}dB {dist}"
        if d.is_balloon and d.altitude_m is not None:
            line += f" {d.altitude_m}m {d.speed_kmh}km/h"
        return line

    def _render_console(self, decodes, page, mode, status):
        print(f"--- {mode}  page {page}  {status} ---")
        if not decodes:
            print("(no decodes yet)")
        for d in decodes:
            print("  " + self._fmt(d))

    def _render_epaper(self, decodes, page, mode, status):
        from PIL import Image, ImageDraw, ImageFont

        epd = self._epd
        # 2.13" V4 panel is 250 x 122; landscape uses (height, width).
        img = Image.new("1", (epd.height, epd.width), 0xFF)
        draw = ImageDraw.Draw(img)
        font = ImageFont.load_default()
        draw.text((2, 0), f"{mode}  p{page}  {status}", font=font, fill=0)
        draw.line((0, 13, epd.height, 13), fill=0)
        y = 16
        for d in decodes:
            draw.text((2, y), self._fmt(d), font=font, fill=0)
            y += 13
        # Use partial refresh for the live update; full refresh on cold start.
        epd.display(epd.getbuffer(img))

    def sleep(self) -> None:
        if self._epd is not None:
            try:
                self._epd.sleep()
            except Exception:
                pass
