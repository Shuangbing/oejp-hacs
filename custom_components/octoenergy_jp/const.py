"""Constants for the Octo Energy JP integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "octoenergy_jp"
PLATFORMS = ["sensor"]

CONF_API_URL = "api_url"
CONF_SCAN_INTERVAL = "scan_interval_minutes"
CONF_SYNC_DAYS = "sync_days"

DEFAULT_API_URL = "https://api.oejp-kraken.energy/v1/graphql/"
DEFAULT_SCAN_INTERVAL_MINUTES = 60
DEFAULT_SYNC_DAYS = 7

MIN_SCAN_INTERVAL_MINUTES = 15
MAX_SYNC_DAYS = 30

JST_TIMEZONE = "Asia/Tokyo"
OVERLAP_HOURS = 6
RECENT_READING_ATTRIBUTES = 48

DEFAULT_UPDATE_INTERVAL = timedelta(minutes=DEFAULT_SCAN_INTERVAL_MINUTES)
