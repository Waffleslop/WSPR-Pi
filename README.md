# wspr-pi

A stand-alone, **offline-first WSPR decoder appliance**. An RTL-SDR V4 + antenna
feeds a Raspberry Pi Zero W that decodes WSPR, computes distance/bearing to each
station from your fixed grid square, and shows the most recent decodes on a
Waveshare 2.13" e-paper display. Wired buttons paginate through history. WiFi is
optional and only used to (a) sync the clock and (b) later upload to WSPRnet.

## Hardware

| Part | Role | Notes |
|------|------|-------|
| Raspberry Pi Zero W | brains | original (ARMv6) is fine for WSPR-only |
| RTL-SDR V4 | receiver | needs the **rtl-sdr-blog** driver fork (R828D tuner) |
| Waveshare 2.13" e-Paper HAT V4 | display | 250×122, SPI; great for slow WSPR cadence |
| PiSugar 3 (1200 mAh) | power + RTC | RTC holds time offline; ~1.5–2 h runtime |
| 1–3 push buttons | paging | wired to spare GPIO → GND (HAT V4 has no keys) |
| HF antenna | signal | choose for your target band |

### Design decisions (locked)
- **No GPS.** Fixed station → set your grid in `config.toml`. Clock is synced by
  NTP whenever WiFi is present and held by the PiSugar 3 RTC while offline. WSPR
  needs ~1 s accuracy; RTC drift over a battery session is sub-second.
- **WSPR only for now.** ADS-B (1090 MHz) cannot share the RTL-SDR with HF WSPR
  simultaneously, so it's deferred as a future toggled mode (see `_toggle_mode`).
- **One band at a time.** WSPR bands are too far apart to capture together.

### Power reality
The RTL-SDR (~1.4 W) dominates the budget; expect **~1.5–2 hours** on the
4.44 Wh PiSugar. The e-paper costs nothing when static. For longer sessions, a
larger cell is the only real fix.

## Software layout
```
src/wspr_pi/
  maidenhead.py  grid <-> lat/lon, great-circle distance & bearing  (pure, tested)
  models.py      Decode dataclass (ground station + balloon telemetry fields)
  config.py      TOML config loader
  store.py       SQLite ring buffer of decodes
  decoder.py     spawn/parse rtlsdr_wsprd  (VERIFY flags & line format on device)
  display.py     e-paper renderer + console fallback for off-Pi dev
  buttons.py     gpiozero button handlers (no-op off-Pi)
  uploader.py    opportunistic WSPRnet upload (stub)
  app.py         main loop wiring it all together
setup/           install.sh (drivers + deps) and the systemd unit
tests/           pytest unit tests (run off-Pi)
```

## Develop off-Pi
The display and buttons degrade to console/no-op when the Pi libraries are
absent, so you can run and test on a laptop:
```
pip install -r requirements.txt
pytest -q
PYTHONPATH=src python -m wspr_pi.app   # console-renders decodes (needs the SDR for real spots)
```

## Bring-up on the Pi
```
git clone <this repo> ~/wspr-pi && cd ~/wspr-pi
bash setup/install.sh
sudo reboot
cp config/config.example.toml config/config.toml   # then edit grid/band over SSH
# sanity-check the SDR + decoder directly first:
rtlsdr_wsprd -f 14095600 -c N0CALL -l FN20
# then run the app, or install the service:
PYTHONPATH=src python3 -m wspr_pi.app
```

## Roadmap
1. ✅ Project skeleton + tested locator math
2. Bench bring-up: drivers, `rtlsdr_wsprd` decoding to console
3. Verify `decoder.py` against real stdout (flags + line format)
4. e-paper rendering + button paging on hardware
5. PiSugar battery % + RTC time-sync + low-battery shutdown
6. Opportunistic WSPRnet upload
7. WSPR balloon (U4B/traquito) telemetry → altitude/speed
8. (later) ADS-B as a toggled second mode

## Things to verify on hardware (marked in code)
- `rtlsdr_wsprd` exact CLI flags and stdout spot-line format → `decoder.py`
- Button GPIO pins and whether your HAT has any keys → `config.toml` / `buttons.py`
- e-paper `epd.height/width` orientation and partial-refresh API → `display.py`
