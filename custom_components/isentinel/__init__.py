"""The iSentinel LP-gas tank integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import IsentinelApi, IsentinelAuthError, IsentinelConnectionError
from .coordinator import IsentinelCoordinator

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR]

type IsentinelConfigEntry = ConfigEntry[IsentinelCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: IsentinelConfigEntry) -> bool:
    """Set up iSentinel from a config entry."""
    api = IsentinelApi(
        async_get_clientsession(hass),
        entry.data[CONF_EMAIL],
        entry.data[CONF_PASSWORD],
    )
    try:
        await api.login()
    except IsentinelAuthError as err:
        raise ConfigEntryAuthFailed(str(err)) from err
    except IsentinelConnectionError as err:
        raise ConfigEntryNotReady(str(err)) from err

    coordinator = IsentinelCoordinator(hass, entry, api)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: IsentinelConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
