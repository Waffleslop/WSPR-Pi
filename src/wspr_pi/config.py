"""Load configuration from a TOML file."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Union

try:  # Python 3.11+
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Pi OS Bullseye ships 3.9
    import tomli as tomllib  # type: ignore


@dataclass
class Config:
    home_grid: str
    band: str
    dial_freq_hz: int
    callsign: str = "N0CALL"
    db_path: str = "wspr.sqlite"
    page_size: int = 5
    ppm: int = 0
    gain: str = "auto"
    rtlsdr_wsprd_path: str = "rtlsdr_wsprd"
    # button BCM pins (you wire these yourself; verify on the bench)
    pin_next: int = 5
    pin_prev: int = 6
    pin_mode: int = 13
    upload_enabled: bool = False
    wsprnet_call: str = ""


def load(path: Union[str, Path]) -> Config:
    data = tomllib.loads(Path(path).read_text(encoding="utf-8"))
    station = data.get("station", {})
    radio = data.get("radio", {})
    display = data.get("display", {})
    buttons = data.get("buttons", {})
    upload = data.get("upload", {})
    return Config(
        home_grid=station["grid"],
        callsign=station.get("callsign", "N0CALL"),
        band=radio.get("band", "20m"),
        dial_freq_hz=int(radio.get("dial_freq_hz", 14095600)),
        ppm=int(radio.get("ppm", 0)),
        gain=str(radio.get("gain", "auto")),
        rtlsdr_wsprd_path=radio.get("rtlsdr_wsprd_path", "rtlsdr_wsprd"),
        db_path=data.get("db_path", "wspr.sqlite"),
        page_size=int(display.get("page_size", 5)),
        pin_next=int(buttons.get("pin_next", 5)),
        pin_prev=int(buttons.get("pin_prev", 6)),
        pin_mode=int(buttons.get("pin_mode", 13)),
        upload_enabled=bool(upload.get("enabled", False)),
        wsprnet_call=upload.get("call", station.get("callsign", "")),
    )
