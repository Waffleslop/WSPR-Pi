"""Tests for the pure-math locator helpers. Run: pytest -q (from repo root)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from wspr_pi import maidenhead as mh  # noqa: E402


def approx(a, b, tol=0.5):
    return abs(a - b) <= tol


def test_field_square_center():
    lat, lon = mh.grid_to_latlon("FN20")
    assert approx(lat, 40.5)
    assert approx(lon, -75.0)


def test_six_char_within_square():
    lat, lon = mh.grid_to_latlon("FN20xr")
    assert 40.0 < lat < 41.0
    assert -76.0 < lon < -74.0


def test_distance_is_symmetric_and_sane():
    d1 = mh.grid_distance_km("FN20", "IO91")  # ~US east coast -> UK
    d2 = mh.grid_distance_km("IO91", "FN20")
    assert approx(d1, d2, 0.1)
    assert 5000 < d1 < 6500


def test_bearing_range():
    b = mh.grid_bearing_deg("FN20", "IO91")
    assert 0.0 <= b < 360.0


def test_invalid_grid_raises():
    for bad in ("ZZ99", "F", "FN2", "12AB"):
        try:
            mh.grid_to_latlon(bad)
        except ValueError:
            continue
        raise AssertionError(f"expected ValueError for {bad!r}")
