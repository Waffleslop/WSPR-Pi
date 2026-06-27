"""Drive `rtlsdr_wsprd` and parse its spots into Decode records.

`rtlsdr_wsprd` (https://github.com/Guenael/rtlsdr-wsprd) does continuous
RTL-SDR capture, 2-minute window alignment, and wsprd decoding for us. We just
consume its stdout.

Spot-line format verified on device (`rtlsdr_wsprd -t` self-test) against the
build from Guenael/rtlsdr-wsprd. It prints a header then one line per spot:

    Spot(0)  22.80   0.01  14.097150  0    K1JT   FN20 20
    Spot(N)  SNR     DT    FreqMHz    Dr   Call   Loc  Pwr

Note SNR is a float here (not the integer HHMM-prefixed wsprd format), and the
line is prefixed with `Spot(N)` rather than a UTC timestamp.
"""
from __future__ import annotations

import re
import subprocess
import time
from typing import Iterator, Optional

from .config import Config
from .models import Decode

_SPOT_RE = re.compile(
    r"^\s*Spot\(\d+\)\s+(?P<snr>-?\d+\.?\d*)\s+(?P<dt>-?\d+\.?\d*)\s+"
    r"(?P<freq>\d+\.\d+)\s+(?P<drift>-?\d+)\s+(?P<msg>.+?)\s*$"
)


def _looks_like_grid(s: str) -> bool:
    return len(s) in (4, 6) and s[:2].isalpha() and s[2:4].isdigit()


def _safe_int(s: str) -> int:
    try:
        return int(s)
    except ValueError:
        return 0


def parse_spot(line: str, band: str) -> Optional[Decode]:
    """Parse a single stdout line into a Decode, or None if it isn't a spot."""
    m = _SPOT_RE.match(line)
    if not m:
        return None
    parts = m.group("msg").split()
    if not parts:
        return None
    callsign = parts[0]
    grid = parts[1] if len(parts) >= 2 and _looks_like_grid(parts[1]) else ""
    power = _safe_int(parts[2]) if len(parts) >= 3 else 0
    return Decode(
        ts=int(time.time()),
        callsign=callsign,
        grid=grid,
        power_dbm=power,
        snr_int=int(round(float(m.group("snr")))),  # SNR is a float in this build
        dt=float(m.group("dt")),
        freq_hz=float(m.group("freq")) * 1_000_000.0,
        drift=int(m.group("drift")),
        band=band,
    )


def build_argv(cfg: Config) -> list[str]:
    argv = [
        cfg.rtlsdr_wsprd_path,
        "-f", str(cfg.dial_freq_hz),
        "-c", cfg.callsign,
        "-l", cfg.home_grid,
        "-p", str(cfg.ppm),
    ]
    # This build uses -a for auto gain and -g <0-49> for a fixed value; emitting
    # neither would silently leave it at the fixed default (29).
    if cfg.gain and cfg.gain.lower() == "auto":
        argv.append("-a")
    elif cfg.gain:
        argv += ["-g", str(cfg.gain)]
    return argv


def run(cfg: Config) -> Iterator[Decode]:
    """Spawn rtlsdr_wsprd and yield decoded spots as they appear."""
    proc = subprocess.Popen(
        build_argv(cfg),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    assert proc.stdout is not None
    try:
        for line in proc.stdout:
            spot = parse_spot(line, cfg.band)
            if spot is not None:
                yield spot
    finally:
        proc.terminate()
