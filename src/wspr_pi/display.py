"""e-paper rendering for the Waveshare 2.13" V4 HAT.

Two-line-per-spot layout tuned for the 250x122 panel: each decode shows the
callsign + grid + SNR on one line, and distance (miles) + compass bearing +
operator name on the next. Falls back to a console renderer when not running on
the Pi (no waveshare_epd / PIL), so the whole app stays exercisable on a laptop.
"""
from __future__ import annotations

import time
from typing import List, Optional

from . import maidenhead
from .models import Decode

# DejaVu ships via fonts-dejavu-core (installed by setup/install.sh).
_FONT_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
_FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


class Display:
    def __init__(self, page_size: int = 3):
        self.page_size = page_size
        self._epd = None
        self._fonts = None
        try:
            from waveshare_epd import epd2in13_V4  # type: ignore

            self._epd = epd2in13_V4.EPD()
            self._epd.init()
            self._epd.Clear(0xFF)
        except Exception as e:  # not on Pi, or lib missing
            print(f"[display] e-paper unavailable ({e}); using console fallback")

    # --- fonts (loaded lazily; only needed for the e-paper path) ---
    def _ensure_fonts(self):
        if self._fonts is not None:
            return self._fonts
        from PIL import ImageFont

        try:
            self._fonts = {
                "head": ImageFont.truetype(_FONT_BOLD, 12),
                "call": ImageFont.truetype(_FONT_BOLD, 15),
                "detail": ImageFont.truetype(_FONT_REG, 12),
            }
        except Exception:  # TTF missing -> bitmap default, still legible
            d = ImageFont.load_default()
            self._fonts = {"head": d, "call": d, "detail": d}
        return self._fonts

    # --- public API ---
    def render(self, decodes: List[Decode], page: int, pages: int,
               mode: str = "WSPR", band: str = "", total: int = 0) -> None:
        if self._epd is None:
            self._render_console(decodes, page, pages, mode, band, total)
        else:
            self._render_epaper(decodes, page, pages, mode, band, total)

    # --- formatting helpers ---
    @staticmethod
    def _header(mode, band, total, page, pages) -> str:
        clock = time.strftime("%H%Mz", time.gmtime())
        bits = [mode]
        if band:
            bits.append(band)
        bits.append(f"{total} spots")
        bits.append(f"p{page + 1}/{pages}")
        bits.append(clock)
        return "  ·  ".join(bits)

    @staticmethod
    def _line1(d: Decode) -> str:
        grid = d.grid or "----"
        return f"{d.callsign}  {grid}"

    @staticmethod
    def _detail(d: Decode) -> str:
        parts = []
        if d.distance_km is not None:
            miles = round(maidenhead.km_to_miles(d.distance_km))
            card = (maidenhead.bearing_to_cardinal(d.bearing_deg)
                    if d.bearing_deg is not None else "")
            parts.append(f"{miles:,} mi {card}".strip())
        if d.is_balloon and d.altitude_m is not None:
            parts.append(f"{d.altitude_m:,}m {d.speed_kmh}km/h")
        elif d.op_name:
            parts.append(d.op_name)
        return "  ·  ".join(parts) if parts else "—"

    # --- renderers ---
    def _render_console(self, decodes, page, pages, mode, band, total):
        print(f"--- {self._header(mode, band, total, page, pages)} ---")
        if not decodes:
            print("(no decodes yet)")
        for d in decodes:
            print(f"  {self._line1(d):<16} {d.snr_int:+d} dB")
            print(f"      {self._detail(d)}")

    def _render_epaper(self, decodes, page, pages, mode, band, total):
        from PIL import Image, ImageDraw

        epd = self._epd
        f = self._ensure_fonts()
        # 2.13" V4 panel is 250 x 122; landscape uses (height, width).
        w, h = epd.height, epd.width
        img = Image.new("1", (w, h), 0xFF)
        draw = ImageDraw.Draw(img)

        draw.text((2, 1), self._header(mode, band, total, page, pages),
                  font=f["head"], fill=0)
        draw.line((0, 16, w, 16), fill=0)

        y = 19
        row_h = 34  # two text lines per spot
        for d in decodes:
            draw.text((2, y), self._line1(d), font=f["call"], fill=0)
            snr = f"{d.snr_int:+d} dB"
            sw = draw.textlength(snr, font=f["detail"])
            draw.text((w - 2 - sw, y + 2), snr, font=f["detail"], fill=0)
            draw.text((10, y + 16), self._detail(d), font=f["detail"], fill=0)
            y += row_h

        if not decodes:
            draw.text((10, y + 8), "(listening… no decodes yet)",
                      font=f["detail"], fill=0)

        epd.display(epd.getbuffer(img))

    def sleep(self) -> None:
        if self._epd is not None:
            try:
                self._epd.sleep()
            except Exception:
                pass
