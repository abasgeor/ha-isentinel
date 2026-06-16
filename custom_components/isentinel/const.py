"""Constants for the iSentinel LP-gas tank integration."""
from __future__ import annotations

from datetime import timedelta

DOMAIN = "isentinel"

API_BASE = "https://api.isentinel.mx"

# Tanks report roughly every 8-15 h (battery deep-sleep); hourly polling is plenty.
SCAN_INTERVAL = timedelta(minutes=30)

CONF_TANKS = "tanks"  # list of isentinel_id to expose on this HA instance
CONF_AREA = "area"  # optional suggested area for the tank devices on this HA

MANUFACTURER = "iSentinel"
