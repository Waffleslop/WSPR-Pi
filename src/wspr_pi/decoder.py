"""Drive `rtlsdr_wsprd` and parse its spots into Decode records.

`rtlsdr_wsprd` (https://github.com/Guenael/rtlsdr_wsprd) does continuous
RTL-SDR capture, 2-minute window alignment, and wsprd decoding for us. We just
consume its stdout.

VERIFY ON DEVICE: the exact CLI flags and the stdout spot-line format vary by
version. Run `rtlsdr_wsprd -h` and capture a few real decode lines, then adjust
`_SPOT_RE` and the argv in `run()` to match. The parser below targets the common
wsprd-style line:  HHMM  SNR  DT  FreqMHz  Drift  MESSAGE
"""
from __future__ import annotations

import re
import subprocess
import time
from typing import Iterator, Optional

from .config import Config
from .models import Decode

_SPOT_RE = re.compile(
    r"^\s*(?P<utc>\d{4})\s+(?P<snr>-?\d+)\s+(?P<dt>-?\d+\.?\d*)\s+"
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
        snr_int=int(m.group("snr")),
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
    if cfg.gain and cfg.gain.lower() != "auto":
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
