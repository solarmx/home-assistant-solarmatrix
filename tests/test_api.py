"""Tests for SolarMatrixAPI."""

from __future__ import annotations

import aiohttp
import pytest
from aioresponses import aioresponses

from custom_components.solarmatrix.api import (
    AccessError,
    AuthError,
    NotFoundError,
    RateLimitError,
    Snapshot,
    SolarMatrixAPI,
    UnavailableError,
    UpstreamError,
)


@pytest.fixture
async def session() -> aiohttp.ClientSession:
    connector = aiohttp.TCPConnector(force_close=True, enable_cleanup_closed=False)
    s = aiohttp.ClientSession(connector=connector)
    yield s
    await s.close()
    await connector.close()


async def test_list_systems_happy_path(session: aiohttp.ClientSession) -> None:
    api = SolarMatrixAPI(session, "https://api.example", "sm_x")
    with aioresponses() as m:
        m.get("https://api.example/api/v1/user/systems", payload=[
            {"id": "11111111-1111-1111-1111-111111111111", "name": "MyHouse"}
        ])
        out = await api.list_systems()
    assert out == [{"id": "11111111-1111-1111-1111-111111111111", "name": "MyHouse"}]


async def test_list_households_happy_path(session: aiohttp.ClientSession) -> None:
    api = SolarMatrixAPI(session, "https://api.example", "sm_x")
    with aioresponses() as m:
        m.get(
            "https://api.example/api/v1/systems/11111111-1111-1111-1111-111111111111/households",
            payload=[{"id": 0, "name": "WE05"}, {"id": 1, "name": "WE07"}],
        )
        out = await api.list_households("11111111-1111-1111-1111-111111111111")
    assert out == [{"id": 0, "name": "WE05"}, {"id": 1, "name": "WE07"}]


async def test_get_snapshot_happy_path(session: aiohttp.ClientSession) -> None:
    api = SolarMatrixAPI(session, "https://api.example", "sm_x")
    body = {
        "household_id": 0,
        "ts_ms": 1735000000000,
        "grid_w": 374,
        "mi_out_w": 21,
        "solar_w": 42,
        "battery_w": -41,
        "battery_soc_pct": 45,
        "energy": {
            "solar_generation_mws":     12345678901234,
            "microinverter_output_mws":  9876543210987,
            "grid_import_mws":           2345678901234,
            "grid_export_mws":            123456789012,
            "battery_charge_mws":        5678901234567,
            "battery_discharge_mws":     5345678901234,
        },
    }
    with aioresponses() as m:
        m.get(
            "https://api.example/api/v1/systems/sid-x/households/0/snapshot",
            payload=body,
        )
        snap = await api.get_snapshot("sid-x", 0)
    assert isinstance(snap, Snapshot)
    assert snap.grid_w == 374
    assert snap.battery_soc_pct == 45
    assert snap.energy.solar_generation_mws == 12345678901234
    assert snap.energy.microinverter_output_mws == 9876543210987
    assert snap.energy.grid_import_mws == 2345678901234
    assert snap.energy.grid_export_mws == 123456789012
    assert snap.energy.battery_charge_mws == 5678901234567
    assert snap.energy.battery_discharge_mws == 5345678901234


@pytest.mark.parametrize(
    "status,exc",
    [
        (401, AuthError),
        (403, AccessError),
        (404, NotFoundError),
        (502, UpstreamError),
        (504, UpstreamError),
    ],
)
async def test_get_snapshot_error_mapping(
    session: aiohttp.ClientSession, status: int, exc: type[Exception]
) -> None:
    api = SolarMatrixAPI(session, "https://api.example", "sm_x")
    with aioresponses() as m:
        m.get(
            "https://api.example/api/v1/systems/sid/households/0/snapshot",
            status=status,
            payload={"error": "no"},
        )
        with pytest.raises(exc):
            await api.get_snapshot("sid", 0)


async def test_get_snapshot_503_unavailable(session: aiohttp.ClientSession) -> None:
    api = SolarMatrixAPI(session, "https://api.example", "sm_x")
    with aioresponses() as m:
        m.get(
            "https://api.example/api/v1/systems/sid/households/0/snapshot",
            status=503,
            headers={"Retry-After": "60"},
        )
        with pytest.raises(UnavailableError):
            await api.get_snapshot("sid", 0)


async def test_get_snapshot_429_rate_limit(session: aiohttp.ClientSession) -> None:
    api = SolarMatrixAPI(session, "https://api.example", "sm_x")
    with aioresponses() as m:
        m.get(
            "https://api.example/api/v1/systems/sid/households/0/snapshot",
            status=429,
            headers={"Retry-After": "4"},
        )
        with pytest.raises(RateLimitError) as exc:
            await api.get_snapshot("sid", 0)
        assert exc.value.retry_after == 4


async def test_x_api_key_header_sent(session: aiohttp.ClientSession) -> None:
    api = SolarMatrixAPI(session, "https://api.example", "sm_secret")
    with aioresponses() as m:
        m.get("https://api.example/api/v1/user/systems", payload=[])
        await api.list_systems()
        # aioresponses tracks calls; first request has matching headers.
        request_calls = next(iter(m.requests.values()))
        kwargs = request_calls[0].kwargs
        assert kwargs["headers"]["X-API-Key"] == "sm_secret"
