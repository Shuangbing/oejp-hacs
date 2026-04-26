"""Sensors for Octo Energy JP."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util
from zoneinfo import ZoneInfo

from .const import DOMAIN, JST_TIMEZONE, RECENT_READING_ATTRIBUTES
from .coordinator import OctoEnergyJpCoordinator, OctoEnergyJpRuntimeData


@dataclass(frozen=True, slots=True)
class OctoEnergyJpSensorDescription(SensorEntityDescription):
    """Entity description for Octo Energy JP sensors."""

    value_fn: Any = None
    attrs_fn: Any = None


SENSOR_DESCRIPTIONS: tuple[OctoEnergyJpSensorDescription, ...] = (
    OctoEnergyJpSensorDescription(
        key="latest_half_hour_usage",
        translation_key="latest_half_hour_usage",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda c: float(c.data.latest_reading.value) if c.data and c.data.latest_reading else None,
        attrs_fn=lambda c: _latest_usage_attrs(c),
    ),
    OctoEnergyJpSensorDescription(
        key="today_total_usage",
        translation_key="today_total_usage",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda c: float(c.get_total_for_local_day(dt_util.now().astimezone(ZoneInfo(JST_TIMEZONE)).date())),
        attrs_fn=lambda c: _window_attrs(c),
    ),
    OctoEnergyJpSensorDescription(
        key="latest_data_timestamp",
        translation_key="latest_data_timestamp",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda c: c.data.latest_reading.end_at if c.data and c.data.latest_reading else None,
        attrs_fn=lambda c: _window_attrs(c),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    runtime_data: OctoEnergyJpRuntimeData = hass.data[DOMAIN][entry.entry_id]
    coordinator = runtime_data.coordinator
    async_add_entities(
        OctoEnergyJpSensor(coordinator, entry, description)
        for description in SENSOR_DESCRIPTIONS
    )


class OctoEnergyJpSensor(CoordinatorEntity[OctoEnergyJpCoordinator], SensorEntity):
    """Representation of an Octo Energy JP sensor."""

    entity_description: OctoEnergyJpSensorDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: OctoEnergyJpCoordinator,
        entry: ConfigEntry,
        description: OctoEnergyJpSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"

    @property
    def native_value(self):
        return self.entity_description.value_fn(self.coordinator)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self.entity_description.attrs_fn(self.coordinator)

    @property
    def device_info(self) -> DeviceInfo:
        account_number = self.coordinator.data.account_number if self.coordinator.data else "unknown"
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.config_entry.entry_id)},
            name="Octo Energy JP",
            manufacturer="Octopus Energy Japan",
            model="Cloud API",
            serial_number=account_number,
        )


def _latest_usage_attrs(coordinator: OctoEnergyJpCoordinator) -> dict[str, Any]:
    if coordinator.data is None or coordinator.data.latest_reading is None:
        return {}
    latest = coordinator.data.latest_reading
    attrs = _window_attrs(coordinator)
    attrs.update(
        {
            "reading_start_at": latest.start_at.isoformat(),
            "reading_end_at": latest.end_at.isoformat(),
            "reading_version": latest.version,
            "data_delay_minutes": _delay_minutes(coordinator.data.data_delay),
            "recent_readings": [
                {
                    "start_at": reading.start_at.isoformat(),
                    "end_at": reading.end_at.isoformat(),
                    "value_kwh": float(reading.value),
                    "version": reading.version,
                }
                for reading in coordinator.data.readings[-RECENT_READING_ATTRIBUTES:]
            ],
        }
    )
    return attrs


def _window_attrs(coordinator: OctoEnergyJpCoordinator) -> dict[str, Any]:
    if coordinator.data is None:
        return {}
    return {
        "account_number": coordinator.data.account_number,
        "fetched_range_start": coordinator.data.range_start.isoformat(),
        "fetched_range_end": coordinator.data.range_end.isoformat(),
        "readings_count": len(coordinator.data.readings),
    }


def _delay_minutes(delay: timedelta | None) -> int | None:
    if delay is None:
        return None
    minutes = int(delay.total_seconds() // 60)
    return max(minutes, 0)
