"""Config flow for the iSentinel integration."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .api import IsentinelApi, IsentinelAuthError, IsentinelConnectionError
from .const import CONF_TANKS, DOMAIN


class IsentinelConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the iSentinel config flow."""

    VERSION = 1

    def __init__(self) -> None:
        self._email: str = ""
        self._password: str = ""
        self._tanks: list[dict[str, Any]] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            self._email = user_input[CONF_EMAIL]
            self._password = user_input[CONF_PASSWORD]
            api = IsentinelApi(async_get_clientsession(self.hass), self._email, self._password)
            try:
                await api.login()
                self._tanks = await api.get_devices()
            except IsentinelAuthError:
                errors["base"] = "invalid_auth"
            except IsentinelConnectionError:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(self._email.lower())
                return await self.async_step_tanks()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {vol.Required(CONF_EMAIL): str, vol.Required(CONF_PASSWORD): str}
            ),
            errors=errors,
        )

    async def async_step_tanks(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(
                title=self._email,
                data={
                    CONF_EMAIL: self._email,
                    CONF_PASSWORD: self._password,
                    CONF_TANKS: user_input[CONF_TANKS],
                },
            )

        options = [
            SelectOptionDict(
                value=str(t.get("isentinel_id") or t.get("embedded_id")),
                label=f"{t.get('alias')} ({(t.get('last_event') or {}).get('tank_level')}%)",
            )
            for t in self._tanks
            if t.get("isentinel_id") or t.get("embedded_id")
        ]
        return self.async_show_form(
            step_id="tanks",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_TANKS): SelectSelector(
                        SelectSelectorConfig(
                            options=options, multiple=True, mode=SelectSelectorMode.LIST
                        )
                    )
                }
            ),
        )
