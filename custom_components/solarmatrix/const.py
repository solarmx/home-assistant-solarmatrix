"""Constants for the SolarMatrix integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "solarmatrix"

DEFAULT_BASE_URL = "https://api.solarmatrix.eu"

CONF_API_KEY = "api_key"
CONF_BASE_URL = "base_url"
CONF_SID = "sid"
CONF_HID = "hid"
CONF_SYSTEM_NAME = "system_name"
CONF_HOUSEHOLD_NAME = "household_name"

POLL_INTERVAL = timedelta(seconds=5)
BACKOFF_FLOOR = timedelta(seconds=60)
BACKOFF_CAP = timedelta(minutes=30)
REQUEST_TIMEOUT_SECONDS = 10
JITTER_SECONDS = 0.5  # ±jitter on first tick
