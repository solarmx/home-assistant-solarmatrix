"""Tests for SolarMatrixCoordinator."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryError
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.solarmatrix.api import (
    AccessError,
    AuthError,
    NotFoundError,
    RateLimitError,
    Snapshot,
    UnavailableError,
)
from custom_components.solarmatrix.const import (
    BACKOFF_CAP,
    BACKOFF_FLOOR,
    POLL_INTERVAL,
)
from custom_components.solarmatrix.coordinator import SolarMatrixCoordinator


def _snap() -> Snapshot:
    return Snapshot(0, 1, 1, 1, 1, 1, 50)


async def test_success_resets_interval(hass: HomeAssistant) -> None:
    api = AsyncMock()
    api.get_snapshot.return_value = _snap()
    coord = SolarMatrixCoordinator(hass, api, "sid", 0)
    coord.update_interval = timedelta(seconds=120)  # pretend we were in backoff
    coord._consec_fails = 3
    out = await coord._async_update_data()
    assert out.battery_soc_pct == 50
    assert coord.update_interval == POLL_INTERVAL
    assert coord._consec_fails == 0


@pytest.mark.parametrize(
    "n,expected_seconds",
    [(1, 60), (2, 120), (3, 240), (4, 480), (5, 960), (6, 1800), (10, 1800)],
)
async def test_failure_backoff_schedule(hass: HomeAssistant, n: int, expected_seconds: int) -> None:
    api = AsyncMock()
    api.get_snapshot.side_effect = UnavailableError("offline")
    coord = SolarMatrixCoordinator(hass, api, "sid", 0)
    for _ in range(n):
        with pytest.raises(UpdateFailed):
            await coord._async_update_data()
    assert coord.update_interval.total_seconds() == expected_seconds


async def test_rate_limit_defers(hass: HomeAssistant) -> None:
    api = AsyncMock()
    api.get_snapshot.side_effect = RateLimitError(retry_after=4)
    coord = SolarMatrixCoordinator(hass, api, "sid", 0)
    with pytest.raises(UpdateFailed):
        await coord._async_update_data()
    assert coord.update_interval == timedelta(seconds=4)


async def test_auth_error_raises_reauth(hass: HomeAssistant) -> None:
    api = AsyncMock()
    api.get_snapshot.side_effect = AuthError("revoked")
    coord = SolarMatrixCoordinator(hass, api, "sid", 0)
    with pytest.raises(ConfigEntryAuthFailed):
        await coord._async_update_data()


@pytest.mark.parametrize("exc", [AccessError("nope"), NotFoundError("gone")])
async def test_access_or_not_found_aborts_entry(hass: HomeAssistant, exc: Exception) -> None:
    api = AsyncMock()
    api.get_snapshot.side_effect = exc
    coord = SolarMatrixCoordinator(hass, api, "sid", 0)
    with pytest.raises(ConfigEntryError):
        await coord._async_update_data()


async def test_backoff_caps_at_30_minutes(hass: HomeAssistant) -> None:
    api = AsyncMock()
    api.get_snapshot.side_effect = UnavailableError("offline")
    coord = SolarMatrixCoordinator(hass, api, "sid", 0)
    for _ in range(20):
        with pytest.raises(UpdateFailed):
            await coord._async_update_data()
    assert coord.update_interval <= BACKOFF_CAP
    assert coord.update_interval >= BACKOFF_FLOOR
