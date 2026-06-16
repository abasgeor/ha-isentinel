"""DataUpdateCoordinator for iSentinel tanks."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import IsentinelApi, IsentinelAuthError, IsentinelConnectionError
from .const import DOMAIN, SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)

# coordinator.data: { isentinel_id: <tank dict> }
type IsentinelData = dict[str, dict[str, Any]]


class IsentinelCoordinator(DataUpdateCoordinator[IsentinelData]):
    """Polls all tanks on the account once per cycle."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, api: IsentinelApi) -> None:
        super().__init__(
            hass, _LOGGER, name=DOMAIN, update_interval=SCAN_INTERVAL, config_entry=entry
        )
        self.api = api

    async def _async_update_data(self) -> IsentinelData:
        try:
            devices = await self.api.get_devices()
        except IsentinelAuthError as err:
            raise UpdateFailed(f"authentication failed: {err}") from err
        except IsentinelConnectionError as err:
            raise UpdateFailed(str(err)) from err
        result: IsentinelData = {}
        for dev in devices:
            tid = str(dev.get("isentinel_id") or dev.get("embedded_id") or "")
            if tid:
                result[tid] = dev
        return result
