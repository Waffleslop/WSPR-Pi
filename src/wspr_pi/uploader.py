"""Opportunistic WSPRnet uploader (stub).

Two viable strategies:
  1. Let rtlsdr_wsprd upload directly (its -u flag) whenever WiFi is up.
  2. Keep decodes offline in SQLite and batch-POST them here when a network
     appears. This module is the skeleton for strategy 2.

Implement flush() against the wsprnet.org spot-upload endpoint when you wire
this in. Until then the app runs fully offline and never calls it.
"""
from __future__ import annotations

import socket
from typing import List

from .models import Decode


def wifi_available(host: str = "wsprnet.org", port: int = 80, timeout: float = 3.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def flush(decodes: List[Decode]) -> int:
    """POST queued decodes to WSPRnet; return number uploaded."""
    raise NotImplementedError("WSPRnet upload not implemented yet")
