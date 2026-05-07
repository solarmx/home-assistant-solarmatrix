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
    EnergyTotals,
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


def _energy() -> EnergyTotals:
    return EnergyTotals(
        solar_generation_mws=0,
        microinverter_output_mws=0,
        grid_import_mws=0,
        grid_export_mws=0,
        battery_charge_mws=0,
        battery_discharge_mws=0,
    )


def _snap() -> Snapshot:
    return Snapshot(0, 1, 1, 1, 1, 1, 50, _energy())


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


async def test_setup_entry_runs(hass: HomeAssistant, mock_entry, monkeypatch) -> None:
    from custom_components.solarmatrix.api import EnergyTotals, Snapshot
    from custom_components.solarmatrix.const import DOMAIN

    async def fake_first_refresh(self):
        self.data = Snapshot(
            0, 1, 1, 1, 1, 1, 50,
            EnergyTotals(0, 0, 0, 0, 0, 0),
        )
        self.last_update_success = True

    monkeypatch.setattr(
        "custom_components.solarmatrix.coordinator.SolarMatrixCoordinator.async_config_entry_first_refresh",
        fake_first_refresh,
        raising=False,
    )
    mock_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_entry.entry_id)
    await hass.async_block_till_done()
    assert mock_entry.entry_id in hass.data[DOMAIN]
