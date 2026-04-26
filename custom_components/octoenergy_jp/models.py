"""Data models for the Octo Energy JP integration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(slots=True, frozen=True)
class HHReading:
    """Half-hourly reading from OEJP API."""

    start_at: datetime
    end_at: datetime
    version: str
    value: Decimal
