"""Drive the full app with fake spots so the e-paper, buttons, store, and
distance/bearing math can be exercised on hardware *without* the RTL-SDR.

Run on the Pi:
    PYTHONPATH=src python3 tools/demo_no_sdr.py

It loads config (so home grid = yours), inserts a spread of synthetic decodes
into a throwaway in-memory-ish DB, renders them to the real e-paper, and lets
the wired buttons page through history. The SDR decode loop is stubbed out, so
no rtlsdr_wsprd process is spawned. Ctrl+C to exit.
"""
from __future__ import annotations

import time
from pathlib import Path

from wspr_pi import config as config_mod
from wspr_pi.app import App
from wspr_pi.models import Decode

# (callsign, grid, power_dbm, snr, freq_offset_hz, balloon?)
# Grids span near->far from FN20 so distance/bearing values are obviously varied.
SAMPLE = [
    ("K1ABC", "FN42", 37, -8, 1500, None),
    ("W3XYZ", "FM18", 23, -14, -800, None),
    ("VE3AAA", "FN03", 30, -19, 400, None),
    ("G0ABC", "IO91", 27, -23, 1200, None),
    ("DL1XYZ", "JO62", 33, -25, -300, None),
    ("JA1ABC", "PM95", 37, -27, 900, None),
    ("VK2DEF", "QF56", 30, -28, -1100, None),
    ("ZL2GHI", "RE78", 23, -29, 600, None),
    ("N0CALL", "EM29", 20, -11, 200, None),
    ("WB8BAL", "EN90", 10, -17, 1700, (12000, 95)),  # a "balloon" telemetry spot
    ("KD2QWE", "FN30", 37, -6, -500, None),
    ("AC1ZZZ", "FN31", 27, -21, 1000, None),
]


def main() -> None:
    cfg_path = Path("config/config.toml")
    if not cfg_path.exists():
        cfg_path = Path("config/config.example.toml")
        print(f"[demo] config/config.toml not found; using {cfg_path}")
    cfg = config_mod.load(cfg_path)

    # Use a separate DB so we never touch the real wspr.sqlite.
    cfg.db_path = "demo_no_sdr.sqlite"

    app = App(cfg)

    base = int(time.time())
    for i, (call, grid, pwr, snr, foff, balloon) in enumerate(SAMPLE):
        d = Decode(
            ts=base - i * 120,  # 2 minutes apart, newest first
            callsign=call,
            grid=grid,
            power_dbm=pwr,
            snr_int=snr,
            dt=0.3,
            freq_hz=cfg.dial_freq_hz + foff,
            drift=0,
            band=cfg.band,
        )
        if balloon:
            d.is_balloon = True
            d.altitude_m, d.speed_kmh = balloon
        app.store.add(app._enrich(d))  # _enrich fills distance/bearing from home grid

    print(f"[demo] inserted {len(SAMPLE)} fake spots; home grid = {cfg.home_grid}")
    print(f"[demo] page_size = {cfg.page_size} -> "
          f"{-(-len(SAMPLE) // cfg.page_size)} pages")
    print("[demo] rendering to e-paper (or console if the panel is absent).")
    print("[demo] press NEXT/PREV buttons to page; Ctrl+C to quit.")

    # Stub the SDR loop so run() doesn't spawn rtlsdr_wsprd.
    app._decode_loop = lambda: None
    try:
        app.run()
    except KeyboardInterrupt:
        print("\n[demo] bye")
        app.display.sleep()


if __name__ == "__main__":
    main()
