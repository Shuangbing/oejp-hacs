"""Data coordinator for Octo Energy JP."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util
from zoneinfo import ZoneInfo

from .api import OctoEnergyJpApiError, OctoEnergyJpAuthError, OctoEnergyJpClient
from .const import (
    CONF_SCAN_INTERVAL,
    CONF_SYNC_DAYS,
    DEFAULT_SCAN_INTERVAL_MINUTES,
    DEFAULT_SYNC_DAYS,
    DOMAIN,
    JST_TIMEZONE,
    OVERLAP_HOURS,
)
from .models import HHReading

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 1


@dataclass(slots=True)
class OctoEnergyJpRuntimeData:
    """Runtime data stored in hass.data for a config entry."""

    client: OctoEnergyJpClient
    coordinator: "OctoEnergyJpCoordinator"


@dataclass(slots=True)
class OctoEnergyJpData:
    """Resolved data snapshot used by sensor entities."""

    account_number: str
    readings: list[HHReading]
    latest_reading: HHReading | None
    data_delay: timedelta | None
    range_start: datetime
    range_end: datetime


class OctoEnergyJpCoordinator(DataUpdateCoordinator[OctoEnergyJpData]):
    """Coordinator to poll delayed half-hour usage data."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        client: OctoEnergyJpClient,
        config_entry: ConfigEntry,
    ) -> None:
        self.hass = hass
        self.client = client
        self.config_entry = config_entry
        self._account_number: str | None = None
        self._jst = ZoneInfo(JST_TIMEZONE)
        self._store: Store[dict[str, str]] = Store(
            hass,
            STORAGE_VERSION,
            f"{DOMAIN}_{config_entry.entry_id}.json",
        )
        self._last_synced_end_at: datetime | None = None

        scan_interval = config_entry.options.get(
            CONF_SCAN_INTERVAL,
            config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_MINUTES),
        )
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=int(scan_interval)),
        )

    async def async_load(self) -> None:
        """Load state from local storage."""
        stored = await self._store.async_load() or {}
        last_synced = stored.get("last_synced_end_at")
        if last_synced:
            self._last_synced_end_at = datetime.fromisoformat(last_synced)

    async def async_save(self) -> None:
        """Persist state to local storage."""
        payload: dict[str, str] = {}
        if self._last_synced_end_at is not None:
            payload["last_synced_end_at"] = self._last_synced_end_at.isoformat()
        await self._store.async_save(payload)

    async def _async_update_data(self) -> OctoEnergyJpData:
        email = self.config_entry.data[CONF_EMAIL]
        password = self.config_entry.data[CONF_PASSWORD]

        try:
            # JWT expires quickly on OEJP side; fetch a fresh token every poll.
            token = await self.client.get_token(email, password)
            if self._account_number is None:
                self._account_number = await self.client.get_account_number(token)
        except OctoEnergyJpAuthError as err:
            raise ConfigEntryAuthFailed("Authentication with Octo Energy JP failed") from err
        except OctoEnergyJpApiError as err:
            raise UpdateFailed(f"API bootstrap failed: {err}") from err

        now_utc = dt_util.utcnow()
        sync_days = int(
            self.config_entry.options.get(
                CONF_SYNC_DAYS,
                self.config_entry.data.get(CONF_SYNC_DAYS, DEFAULT_SYNC_DAYS),
            )
        )

        default_start = now_utc.astimezone(self._jst) - timedelta(days=sync_days)
        if self._last_synced_end_at is not None:
            range_start = self._last_synced_end_at - timedelta(hours=OVERLAP_HOURS)
            if range_start < default_start:
                range_start = default_start
        else:
            range_start = default_start
        range_end = now_utc.astimezone(self._jst)

        try:
            readings = await self.client.get_hh_readings(
                account_number=self._account_number,
                token=token,
                start_at=range_start,
                end_at=range_end,
            )
        except OctoEnergyJpAuthError:
            raise ConfigEntryAuthFailed("Authentication expired; please reauthenticate")
        except OctoEnergyJpApiError as err:
            raise UpdateFailed(f"Failed to fetch half-hour readings: {err}") from err

        latest = readings[-1] if readings else None
        delay = now_utc - latest.end_at.astimezone(dt_util.UTC) if latest else None

        if latest and (self._last_synced_end_at is None or latest.end_at > self._last_synced_end_at):
            self._last_synced_end_at = latest.end_at
            await self.async_save()

        return OctoEnergyJpData(
            account_number=self._account_number,
            readings=readings,
            latest_reading=latest,
            data_delay=delay,
            range_start=range_start,
            range_end=range_end,
        )

    def get_total_for_local_day(self, target_day: date):
        """Return day total by JST day from the latest coordinator snapshot."""
        if self.data is None:
            return 0.0
        total = 0.0
        for reading in self.data.readings:
            if reading.start_at.astimezone(self._jst).date() == target_day:
                total += float(reading.value)
        return total
