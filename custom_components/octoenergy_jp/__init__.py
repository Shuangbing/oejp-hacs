"""Octo Energy JP custom integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import OctoEnergyJpClient
from .const import CONF_API_URL, DEFAULT_API_URL, DOMAIN, PLATFORMS
from .coordinator import OctoEnergyJpCoordinator, OctoEnergyJpRuntimeData


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Octo Energy JP from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    session = async_get_clientsession(hass)
    api_url = entry.options.get(CONF_API_URL, entry.data.get(CONF_API_URL, DEFAULT_API_URL))
    client = OctoEnergyJpClient(session=session, api_url=api_url)
    coordinator = OctoEnergyJpCoordinator(hass=hass, client=client, config_entry=entry)
    await coordinator.async_load()
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = OctoEnergyJpRuntimeData(
        client=client,
        coordinator=coordinator,
    )
    entry.async_on_unload(entry.add_update_listener(async_update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Support future config entry migrations."""
    return True


async def async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry when options are updated."""
    await hass.config_entries.async_reload(entry.entry_id)
