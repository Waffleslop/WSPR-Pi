"""Main application: decode -> enrich -> store -> display, with button paging.

A background thread consumes rtlsdr_wsprd spots; the main thread owns the
display and redraws on new decodes or button presses.
"""
from __future__ import annotations

import threading
from pathlib import Path

from . import config as config_mod
from . import decoder, maidenhead
from .buttons import Buttons
from .display import Display
from .models import Decode
from .store import Store


class App:
    def __init__(self, cfg: config_mod.Config):
        self.cfg = cfg
        self.store = Store(cfg.db_path)
        self.display = Display(cfg.page_size)
        self.page = 0
        self.mode = "WSPR"
        self._dirty = threading.Event()
        self.buttons = Buttons(cfg, self._next, self._prev, self._toggle_mode)

    # --- button handlers (run on gpiozero's callback thread) ---
    def _next(self):
        max_page = max(0, (self.store.count() - 1) // self.cfg.page_size)
        self.page = min(self.page + 1, max_page)
        self._dirty.set()

    def _prev(self):
        self.page = max(0, self.page - 1)
        self._dirty.set()

    def _toggle_mode(self):
        # Placeholder: only WSPR exists today. ADS-B would slot in here.
        self._dirty.set()

    # --- decode pipeline ---
    def _enrich(self, d: Decode) -> Decode:
        if d.grid:
            try:
                d.distance_km = maidenhead.grid_distance_km(self.cfg.home_grid, d.grid)
                d.bearing_deg = maidenhead.grid_bearing_deg(self.cfg.home_grid, d.grid)
            except ValueError:
                pass
        return d

    def _decode_loop(self):
        for spot in decoder.run(self.cfg):
            self.store.add(self._enrich(spot))
            self.page = 0  # jump back to the freshest page on a new decode
            self._dirty.set()

    # --- main loop ---
    def run(self):
        threading.Thread(target=self._decode_loop, daemon=True).start()
        self._refresh()
        while True:
            self._dirty.wait(timeout=30)
            self._dirty.clear()
            self._refresh()

    def _refresh(self):
        total = self.store.count()
        pages = max(1, (total + self.cfg.page_size - 1) // self.cfg.page_size)
        rows = self.store.page(self.page, self.cfg.page_size)
        self.display.render(rows, self.page, pages, self.mode, self.cfg.band, total)


def main():
    cfg_path = Path("config/config.toml")
    if not cfg_path.exists():
        cfg_path = Path("config/config.example.toml")
        print(f"[app] config/config.toml not found; using {cfg_path}")
    cfg = config_mod.load(cfg_path)
    App(cfg).run()


if __name__ == "__main__":
    main()
