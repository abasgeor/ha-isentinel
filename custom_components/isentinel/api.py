"""Async client for the iSentinel cloud API (api.isentinel.mx)."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp

from .const import API_BASE

_LOGGER = logging.getLogger(__name__)


class IsentinelAuthError(Exception):
    """Invalid credentials."""


class IsentinelConnectionError(Exception):
    """Transport or non-auth API error."""


class IsentinelApi:
    """Thin async wrapper over the iSentinel consumer API.

    Auth: ``POST /users/login`` {email, password} -> access_token (+ refresh_token).
    Tanks: ``GET /users/devices`` with ``Authorization: Bearer <token>``.
    The token is refreshed by re-logging in on a 401 (no public refresh endpoint).
    """

    def __init__(self, session: aiohttp.ClientSession, email: str, password: str) -> None:
        self._session = session
        self._email = email
        self._password = password
        self._token: str | None = None

    async def login(self) -> None:
        """Authenticate and store the access token."""
        try:
            async with self._session.post(
                f"{API_BASE}/users/login",
                json={"email": self._email, "password": self._password},
            ) as resp:
                if resp.status in (400, 401):
                    raise IsentinelAuthError("Invalid iSentinel credentials")
                resp.raise_for_status()
                data = await resp.json()
        except aiohttp.ClientError as err:
            raise IsentinelConnectionError(f"connection error: {err}") from err
        token = data.get("access_token")
        if not token:
            raise IsentinelAuthError("iSentinel login returned no token")
        self._token = token

    async def _request(self, method: str, path: str, *, _retry: bool = True) -> Any:
        if self._token is None:
            await self.login()
        try:
            async with self._session.request(
                method, f"{API_BASE}{path}",
                headers={"Authorization": f"Bearer {self._token}"},
            ) as resp:
                if resp.status == 401 and _retry:
                    self._token = None
                    await self.login()
                    return await self._request(method, path, _retry=False)
                if resp.status == 401:
                    raise IsentinelAuthError("iSentinel token rejected after re-login")
                resp.raise_for_status()
                return await resp.json()
        except aiohttp.ClientError as err:
            raise IsentinelConnectionError(f"connection error: {err}") from err

    async def get_devices(self) -> list[dict[str, Any]]:
        """GET /users/devices -> list of tanks with last_event/last_fill_event/level_alert."""
        data = await self._request("GET", "/users/devices")
        return data if isinstance(data, list) else []
