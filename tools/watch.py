"""Tail new WSPR decodes from the SQLite store as the service writes them.

Run on the Pi (safe to run alongside the live wspr-pi service):
    PYTHONPATH=src python3 tools/watch.py [db_path]

Polls the decodes table and prints each new spot as it lands, like a live feed.
Ctrl+C to stop. Default db is wspr.sqlite in the current directory, so run it
from ~/wspr-pi. Uses a read-only-style poll with a busy timeout, so it won't
disturb the service's writes.
"""
from __future__ import annotations

import sqlite3
import sys
import time

from wspr_pi import maidenhead


def _fmt(r) -> str:
    t = time.strftime("%m-%d %H:%M:%S", time.localtime(r["ts"]))
    if r["distance_km"] is not None:
        mi = round(maidenhead.km_to_miles(r["distance_km"]))
        card = (maidenhead.bearing_to_cardinal(r["bearing_deg"])
                if r["bearing_deg"] is not None else "")
        loc = f"{mi:>5,} mi {card}"
    else:
        loc = "   -- mi"
    return f"{t}  {r['callsign']:<8} {r['grid']:<6} {r['snr_int']:+3d} dB  {loc}"


_COLS = ("SELECT id, ts, callsign, grid, snr_int, distance_km, bearing_deg "
         "FROM decodes")


def main() -> None:
    db_path = sys.argv[1] if len(sys.argv) > 1 else "wspr.sqlite"
    db = sqlite3.connect(db_path, timeout=5)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA busy_timeout=3000")

    # Startup summary: how many decodes exist, and the most recent few.
    last = 0
    try:
        total = db.execute("SELECT COUNT(*) FROM decodes").fetchone()[0]
        recent = db.execute(_COLS + " ORDER BY id DESC LIMIT 5").fetchall()
        print(f"{db_path}: {total} decodes logged so far")
        for r in reversed(recent):
            print("  " + _fmt(r))
        if recent:
            last = recent[0]["id"]
    except sqlite3.OperationalError:
        print(f"{db_path}: no decodes table yet (service hasn't written any)")

    print("\n— watching for new decodes — Ctrl+C to stop\n")
    try:
        while True:
            try:
                rows = db.execute(
                    _COLS + " WHERE id > ? ORDER BY id", (last,)
                ).fetchall()
            except sqlite3.OperationalError:
                time.sleep(2)  # table not created yet, or a momentary write lock
                continue
            for r in rows:
                last = r["id"]
                print(_fmt(r))
            time.sleep(10)
    except KeyboardInterrupt:
        print("\nstopped")


if __name__ == "__main__":
    main()
