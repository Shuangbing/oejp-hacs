"""Config flow for Octo Energy JP."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import OctoEnergyJpApiError, OctoEnergyJpAuthError, OctoEnergyJpClient
from .const import (
    CONF_API_URL,
    CONF_SCAN_INTERVAL,
    CONF_SYNC_DAYS,
    DEFAULT_API_URL,
    DEFAULT_SCAN_INTERVAL_MINUTES,
    DEFAULT_SYNC_DAYS,
    DOMAIN,
    MAX_SYNC_DAYS,
    MIN_SCAN_INTERVAL_MINUTES,
)


class OctoEnergyJpConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Octo Energy JP."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}

        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_EMAIL].strip().lower())
            self._abort_if_unique_id_configured()

            is_valid = await _validate_input(self.hass, user_input)
            if is_valid:
                return self.async_create_entry(title="Octo Energy JP", data=user_input)
            errors["base"] = "auth"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_EMAIL): str,
                    vol.Required(CONF_PASSWORD): str,
                    vol.Optional(CONF_API_URL, default=DEFAULT_API_URL): str,
                    vol.Optional(
                        CONF_SCAN_INTERVAL,
                        default=DEFAULT_SCAN_INTERVAL_MINUTES,
                    ): vol.All(vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL_MINUTES)),
                    vol.Optional(
                        CONF_SYNC_DAYS,
                        default=DEFAULT_SYNC_DAYS,
                    ): vol.All(vol.Coerce(int), vol.Range(min=1, max=MAX_SYNC_DAYS)),
                }
            ),
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        return OctoEnergyJpOptionsFlow(config_entry)


class OctoEnergyJpOptionsFlow(config_entries.OptionsFlow):
    """Handle options for Octo Energy JP."""

    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_API_URL,
                        default=self.config_entry.options.get(
                            CONF_API_URL,
                            self.config_entry.data.get(CONF_API_URL, DEFAULT_API_URL),
                        ),
                    ): str,
                    vol.Optional(
                        CONF_SCAN_INTERVAL,
                        default=self.config_entry.options.get(
                            CONF_SCAN_INTERVAL,
                            self.config_entry.data.get(
                                CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_MINUTES
                            ),
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL_MINUTES)),
                    vol.Optional(
                        CONF_SYNC_DAYS,
                        default=self.config_entry.options.get(
                            CONF_SYNC_DAYS,
                            self.config_entry.data.get(CONF_SYNC_DAYS, DEFAULT_SYNC_DAYS),
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=1, max=MAX_SYNC_DAYS)),
                }
            ),
        )


async def _validate_input(hass, data: dict[str, Any]) -> bool:
    session = async_get_clientsession(hass)
    client = OctoEnergyJpClient(session=session, api_url=data[CONF_API_URL])
    try:
        token = await client.get_token(data[CONF_EMAIL], data[CONF_PASSWORD])
        await client.get_account_number(token)
    except (OctoEnergyJpAuthError, OctoEnergyJpApiError):
        return False
    return True
