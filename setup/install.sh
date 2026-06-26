#!/usr/bin/env bash
# Provision a Raspberry Pi (Zero W / Zero 2 W, Raspberry Pi OS) for wspr-pi.
# Run on the Pi:  bash setup/install.sh
# Re-run safe. VERIFY each section the first time; SDR/decoder builds evolve.
set -euo pipefail

echo "==> System packages"
sudo apt-get update
sudo apt-get install -y \
    git build-essential clang cmake pkg-config \
    libusb-1.0-0-dev \
    libfftw3-dev libcurl4-openssl-dev \
    python3 python3-pip python3-venv python3-pil \
    chrony i2c-tools

echo "==> RTL-SDR Blog drivers (required for the V4 / R828D tuner)"
# Stock Osmocom librtlsdr mis-detects the V4. Build the rtl-sdr-blog fork.
if [ ! -d "$HOME/rtl-sdr-blog" ]; then
    git clone https://github.com/rtlsdrblog/rtl-sdr-blog "$HOME/rtl-sdr-blog"
fi
cmake -S "$HOME/rtl-sdr-blog" -B "$HOME/rtl-sdr-blog/build" \
    -DINSTALL_UDEV_RULES=ON -DDETACH_KERNEL_DRIVER=ON
make -C "$HOME/rtl-sdr-blog/build" -j"$(nproc)"
sudo make -C "$HOME/rtl-sdr-blog/build" install
sudo cp "$HOME/rtl-sdr-blog/rtl-sdr.rules" /etc/udev/rules.d/ || true
sudo ldconfig
# Blacklist the DVB kernel module so it doesn't grab the dongle.
echo 'blacklist dvb_usb_rtl28xxu' | sudo tee /etc/modprobe.d/blacklist-rtl.conf

echo "==> rtlsdr_wsprd (standalone WSPR capture+decode daemon)"
# Upstream repo was renamed Guenael/rtlsdr_wsprd -> rtlsdr-wsprd (hyphen).
# Binary is still named rtlsdr_wsprd. The Makefile's ARMv6 (Pi Zero/1) profile
# injects clang-only flags (--target=arm-linux-gnueabihf), so build with clang
# (the Makefile's default CC) rather than gcc. Letting it pick CC also keeps its
# own arch detection working for ARMv7/aarch64 (Zero 2 W).
if [ ! -d "$HOME/rtlsdr-wsprd" ]; then
    git clone https://github.com/Guenael/rtlsdr-wsprd "$HOME/rtlsdr-wsprd"
fi
make -C "$HOME/rtlsdr-wsprd" -j"$(nproc)"
sudo make -C "$HOME/rtlsdr-wsprd" install || \
    sudo cp "$HOME/rtlsdr-wsprd/rtlsdr_wsprd" /usr/local/bin/

echo "==> Waveshare e-Paper Python library"
sudo raspi-config nonint do_spi 0   # enable SPI
if [ ! -d "$HOME/e-Paper" ]; then
    git clone https://github.com/waveshare/e-Paper "$HOME/e-Paper"
fi
pip3 install --break-system-packages \
    "$HOME/e-Paper/RaspberryPi_JetsonNano/python" || \
    echo "NOTE: install the waveshare_epd package manually if the above path differs"

echo "==> Python app deps"
pip3 install --break-system-packages -r "$(dirname "$0")/../requirements.txt"

echo "==> Done. Reboot recommended (driver blacklist + SPI)."
echo "    Then: cp config/config.example.toml config/config.toml && edit it."
