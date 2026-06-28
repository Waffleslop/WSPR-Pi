"""Maidenhead locator <-> coordinates, plus great-circle distance and bearing.

This module is pure math with no hardware dependencies, so it is fully
unit-testable off-device (see tests/test_maidenhead.py).
"""
from __future__ import annotations

import math
from typing import Tuple

_A = ord("A")
_a = ord("a")

EARTH_RADIUS_KM = 6371.0088  # mean radius
MILES_PER_KM = 0.621371192

_COMPASS_16 = ("N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
               "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW")


def km_to_miles(km: float) -> float:
    return km * MILES_PER_KM


def bearing_to_cardinal(deg: float) -> str:
    """Map a bearing in degrees to a 16-point compass label (e.g. 'NE')."""
    return _COMPASS_16[int((deg % 360) / 22.5 + 0.5) % 16]


def grid_to_latlon(grid: str) -> Tuple[float, float]:
    """Return (lat, lon) of the *center* of a Maidenhead grid square.

    Accepts 2-, 4-, 6-, or 8-character locators (e.g. "FN", "FN20",
    "FN20xr", "FN20xr12"). Raises ValueError on malformed input.
    """
    g = grid.strip()
    n = len(g)
    if n not in (2, 4, 6, 8):
        raise ValueError(f"invalid grid length: {grid!r}")

    lon, lat = -180.0, -90.0
    lon_size, lat_size = 20.0, 10.0  # resolution of the field pair, in degrees

    c0, c1 = g[0].upper(), g[1].upper()
    if not ("A" <= c0 <= "R" and "A" <= c1 <= "R"):
        raise ValueError(f"invalid field: {grid!r}")
    lon += (ord(c0) - _A) * lon_size
    lat += (ord(c1) - _A) * lat_size

    if n >= 4:
        if not (g[2].isdigit() and g[3].isdigit()):
            raise ValueError(f"invalid square: {grid!r}")
        lon_size /= 10.0
        lat_size /= 10.0
        lon += int(g[2]) * lon_size
        lat += int(g[3]) * lat_size

    if n >= 6:
        s0, s1 = g[4].lower(), g[5].lower()
        if not ("a" <= s0 <= "x" and "a" <= s1 <= "x"):
            raise ValueError(f"invalid subsquare: {grid!r}")
        lon_size /= 24.0
        lat_size /= 24.0
        lon += (ord(s0) - _a) * lon_size
        lat += (ord(s1) - _a) * lat_size

    if n >= 8:
        if not (g[6].isdigit() and g[7].isdigit()):
            raise ValueError(f"invalid extended square: {grid!r}")
        lon_size /= 10.0
        lat_size /= 10.0
        lon += int(g[6]) * lon_size
        lat += int(g[7]) * lat_size

    # shift to the center of the smallest resolved square
    lon += lon_size / 2.0
    lat += lat_size / 2.0
    return lat, lon


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km between two lat/lon points."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(min(1.0, math.sqrt(a)))


def initial_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Initial great-circle bearing in degrees (0=N, 90=E) from point 1 to 2."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    x = math.sin(dl) * math.cos(p2)
    y = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return (math.degrees(math.atan2(x, y)) + 360.0) % 360.0


def grid_distance_km(home: str, other: str) -> float:
    la1, lo1 = grid_to_latlon(home)
    la2, lo2 = grid_to_latlon(other)
    return haversine_km(la1, lo1, la2, lo2)


def grid_bearing_deg(home: str, other: str) -> float:
    la1, lo1 = grid_to_latlon(home)
    la2, lo2 = grid_to_latlon(other)
    return initial_bearing(la1, lo1, la2, lo2)
