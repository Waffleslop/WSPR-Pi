"""SQLite-backed ring buffer of decodes."""
from __future__ import annotations

import sqlite3
from typing import List

from .models import Decode

_SCHEMA = """
CREATE TABLE IF NOT EXISTS decodes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts          INTEGER NOT NULL,
    callsign    TEXT NOT NULL,
    grid        TEXT NOT NULL,
    power_dbm   INTEGER,
    snr_int     INTEGER,
    dt          REAL,
    freq_hz     REAL,
    drift       INTEGER,
    band        TEXT,
    distance_km REAL,
    bearing_deg REAL,
    altitude_m  INTEGER,
    speed_kmh   INTEGER,
    is_balloon  INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_decodes_ts ON decodes(ts DESC, id DESC);

CREATE TABLE IF NOT EXISTS operators (
    callsign TEXT PRIMARY KEY,
    name     TEXT,
    ts       INTEGER
);
"""


class Store:
    def __init__(self, path: str, max_rows: int = 2000):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.max_rows = max_rows
        self.conn.executescript(_SCHEMA)
        self.conn.commit()

    def add(self, d: Decode) -> None:
        self.conn.execute(
            """INSERT INTO decodes
               (ts, callsign, grid, power_dbm, snr_int, dt, freq_hz, drift,
                band, distance_km, bearing_deg, altitude_m, speed_kmh, is_balloon)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (d.ts, d.callsign, d.grid, d.power_dbm, d.snr_int, d.dt, d.freq_hz,
             d.drift, d.band, d.distance_km, d.bearing_deg, d.altitude_m,
             d.speed_kmh, int(d.is_balloon)),
        )
        self._prune()
        self.conn.commit()

    def latest(self, limit: int = 5) -> List[Decode]:
        return self.page(0, limit)

    def page(self, page: int, size: int) -> List[Decode]:
        rows = self.conn.execute(
            "SELECT * FROM decodes ORDER BY ts DESC, id DESC LIMIT ? OFFSET ?",
            (size, page * size),
        ).fetchall()
        decodes = [self._row(r) for r in rows]
        for d in decodes:  # attach cached operator names (None if unknown)
            d.op_name = self.get_name(d.callsign)
        return decodes

    def count(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM decodes").fetchone()[0]

    # --- operator-name cache (populated opportunistically by a lookup) ---
    def get_name(self, callsign: str):
        row = self.conn.execute(
            "SELECT name FROM operators WHERE callsign = ?", (callsign,)
        ).fetchone()
        return row["name"] if row else None

    def has_name(self, callsign: str) -> bool:
        """True if we've already resolved (or tried and stored) this callsign."""
        return self.conn.execute(
            "SELECT 1 FROM operators WHERE callsign = ?", (callsign,)
        ).fetchone() is not None

    def set_name(self, callsign: str, name, ts: int) -> None:
        self.conn.execute(
            """INSERT INTO operators (callsign, name, ts) VALUES (?,?,?)
               ON CONFLICT(callsign) DO UPDATE SET name=excluded.name, ts=excluded.ts""",
            (callsign, name, ts),
        )
        self.conn.commit()

    def _prune(self) -> None:
        self.conn.execute(
            """DELETE FROM decodes WHERE id NOT IN
               (SELECT id FROM decodes ORDER BY ts DESC, id DESC LIMIT ?)""",
            (self.max_rows,),
        )

    @staticmethod
    def _row(r: sqlite3.Row) -> Decode:
        return Decode(
            ts=r["ts"], callsign=r["callsign"], grid=r["grid"],
            power_dbm=r["power_dbm"], snr_int=r["snr_int"], dt=r["dt"],
            freq_hz=r["freq_hz"], drift=r["drift"], band=r["band"],
            distance_km=r["distance_km"], bearing_deg=r["bearing_deg"],
            altitude_m=r["altitude_m"], speed_kmh=r["speed_kmh"],
            is_balloon=bool(r["is_balloon"]),
        )
