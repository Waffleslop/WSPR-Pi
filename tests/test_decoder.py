"""Parser tests pinned to real `rtlsdr_wsprd -t` self-test output.

The reference line was captured on-device from the Guenael/rtlsdr-wsprd build:

    Spot(0)  22.80   0.01  14.097150  0    K1JT   FN20 20
"""
from wspr_pi.config import Config
from wspr_pi.decoder import build_argv, parse_spot

REAL_SPOT = "Spot(0)  22.80   0.01  14.097150  0    K1JT   FN20 20"


def test_parse_real_spot_line():
    d = parse_spot(REAL_SPOT, "20m")
    assert d is not None
    assert d.callsign == "K1JT"
    assert d.grid == "FN20"
    assert d.power_dbm == 20
    assert d.snr_int == 23           # round(22.80)
    assert abs(d.dt - 0.01) < 1e-9
    assert abs(d.freq_hz - 14_097_150.0) < 1e-3
    assert d.drift == 0
    assert d.band == "20m"


def test_negative_snr_and_dt():
    d = parse_spot("Spot(2)  -24.30  -1.20  14.097010  1  DL1XYZ JO62 30", "20m")
    assert d is not None
    assert d.snr_int == -24
    assert abs(d.dt + 1.20) < 1e-9
    assert d.drift == 1
    assert d.grid == "JO62"


def test_header_and_noise_are_not_spots():
    assert parse_spot("        SNR      DT        Freq Dr    Call    Loc Pwr", "20m") is None
    assert parse_spot("Self-test SUCCESS!", "20m") is None
    assert parse_spot("", "20m") is None


def test_build_argv_auto_gain_uses_dash_a():
    cfg = Config(home_grid="FN20", band="20m", dial_freq_hz=14095600, gain="auto")
    argv = build_argv(cfg)
    assert "-a" in argv
    assert "-g" not in argv


def test_build_argv_fixed_gain_uses_dash_g():
    cfg = Config(home_grid="FN20", band="20m", dial_freq_hz=14095600, gain="40")
    argv = build_argv(cfg)
    assert "-g" in argv and "40" in argv
    assert "-a" not in argv
