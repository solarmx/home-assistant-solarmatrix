"""SolarMatrix HTTP API client.

A single instance owns a single aiohttp.ClientSession so that all polls reuse
one TCP/TLS keep-alive connection. The class is intentionally minimal: the
only state outside the session is the base URL and the API key.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import aiohttp

from .const import REQUEST_TIMEOUT_SECONDS


class APIError(Exception):
    """Base class for SolarMatrix API errors."""


class AuthError(APIError):
    """401 — invalid, expired, or revoked API key."""


class AccessError(APIError):
    """403 — caller is authenticated but cannot reach the requested resource."""


class NotFoundError(APIError):
    """404 — resource missing."""


class RateLimitError(APIError):
    """429 — caller throttled. retry_after seconds is from the response."""

    def __init__(self, retry_after: int) -> None:
        super().__init__(f"rate limited; retry_after={retry_after}")
        self.retry_after = retry_after


class UnavailableError(APIError):
    """503 — system not currently producing data (offline or non-operational mode)."""


class UpstreamError(APIError):
    """5xx other than 503 — controller relay or backend internal error."""


@dataclass(frozen=True)
class EnergyTotals:
    """Lifetime cumulative energy per channel, in milliwatt-seconds.

    Always non-negative and monotonically non-decreasing across calls.
    Convert to kWh: ``mws / 3_600_000_000``.
    """

    solar_generation_mws: int
    microinverter_output_mws: int
    grid_import_mws: int
    grid_export_mws: int
    battery_charge_mws: int
    battery_discharge_mws: int

    @classmethod
    def from_json(cls, body: dict[str, Any]) -> "EnergyTotals":
        return cls(
            solar_generation_mws=int(body["solar_generation_mws"]),
            microinverter_output_mws=int(body["microinverter_output_mws"]),
            grid_import_mws=int(body["grid_import_mws"]),
            grid_export_mws=int(body["grid_export_mws"]),
            battery_charge_mws=int(body["battery_charge_mws"]),
            battery_discharge_mws=int(body["battery_discharge_mws"]),
        )


@dataclass(frozen=True)
class Snapshot:
    """One sample of live power, SoC, and lifetime energy for a household."""

    household_id: int
    ts_ms: int
    grid_w: int
    mi_out_w: int
    solar_w: int
    battery_w: int
    battery_soc_pct: int
    energy: EnergyTotals

    @classmethod
    def from_json(cls, body: dict[str, Any]) -> "Snapshot":
        return cls(
            household_id=int(body["household_id"]),
            ts_ms=int(body["ts_ms"]),
            grid_w=int(body["grid_w"]),
            mi_out_w=int(body["mi_out_w"]),
            solar_w=int(body["solar_w"]),
            battery_w=int(body["battery_w"]),
            battery_soc_pct=int(body["battery_soc_pct"]),
            energy=EnergyTotals.from_json(body["energy"]),
        )


class SolarMatrixAPI:
    """Thin async wrapper around the SolarMatrix HTTP API."""

    def __init__(self, session: aiohttp.ClientSession, base_url: str, api_key: str) -> None:
        self._session = session
        self._base = base_url.rstrip("/")
        self._headers = {"X-API-Key": api_key}

    async def list_systems(self) -> list[dict[str, Any]]:
        url = f"{self._base}/api/v1/user/systems"
        return await self._get_json(url)

    async def list_households(self, sid: str) -> list[dict[str, Any]]:
        url = f"{self._base}/api/v1/systems/{sid}/households"
        return await self._get_json(url)

    async def get_household(self, sid: str, hid: int) -> dict[str, Any]:
        url = f"{self._base}/api/v1/systems/{sid}/households/{hid}"
        return await self._get_json(url)

    async def get_snapshot(self, sid: str, hid: int) -> Snapshot:
        url = f"{self._base}/api/v1/systems/{sid}/households/{hid}/snapshot"
        body = await self._get_json(url)
        return Snapshot.from_json(body)

    async def _get_json(self, url: str) -> Any:
        async with self._session.get(
            url,
            headers=self._headers,
            timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT_SECONDS),
        ) as resp:
            if resp.status == 200:
                return await resp.json()
            if resp.status == 401:
                raise AuthError("invalid API key")
            if resp.status == 403:
                raise AccessError("forbidden")
            if resp.status == 404:
                raise NotFoundError("not found")
            if resp.status == 429:
                ra = int(resp.headers.get("Retry-After", "4") or "4")
                raise RateLimitError(retry_after=ra)
            if resp.status == 503:
                raise UnavailableError("service unavailable")
            raise UpstreamError(f"unexpected status {resp.status}")
