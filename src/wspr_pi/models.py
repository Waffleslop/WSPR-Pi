"""Normalized data model for decodes."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class Decode:
    """One WSPR spot, normalized into a single record.

    Ground-station spots leave the balloon-telemetry fields as None. Balloon
    (U4B/traquito) telemetry decodes set is_balloon=True and fill altitude/speed
    (handled later by a telemetry module).
    """

    ts: int            # unix epoch seconds (decode time)
    callsign: str
    grid: str          # may be "" for type-2/3 messages without a grid
    power_dbm: int
    snr_int: int
    dt: float          # time offset of the decode, seconds
    freq_hz: float
    drift: int
    band: str          # e.g. "20m"

    # derived once the home grid is known
    distance_km: Optional[float] = None
    bearing_deg: Optional[float] = None

    # balloon telemetry (None for ordinary ground stations)
    altitude_m: Optional[int] = None
    speed_kmh: Optional[int] = None
    is_balloon: bool = False
