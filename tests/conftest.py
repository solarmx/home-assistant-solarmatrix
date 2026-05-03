"""Pytest fixtures for SolarMatrix tests."""

from __future__ import annotations

import asyncio
from typing import Any

import aiohttp
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.solarmatrix.const import (
    CONF_API_KEY,
    CONF_BASE_URL,
    CONF_HID,
    CONF_HOUSEHOLD_NAME,
    CONF_SID,
    CONF_SYSTEM_NAME,
    DOMAIN,
)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: Any) -> Any:
    """Enable custom integration loading for every test."""
    yield


@pytest.fixture
def mock_entry() -> MockConfigEntry:
    """A pre-built ConfigEntry usable by setup/unload tests."""
    return MockConfigEntry(
        domain=DOMAIN,
        unique_id="sid-A:0",
        data={
            CONF_API_KEY: "sm_x",
            CONF_BASE_URL: "https://api.example",
            CONF_SID: "sid-A",
            CONF_HID: 0,
            CONF_SYSTEM_NAME: "House A",
            CONF_HOUSEHOLD_NAME: "WE05",
        },
    )


@pytest.fixture(autouse=True, scope="session")
def _prime_aiohttp_shutdown_thread() -> None:
    """Spin aiohttp's ``_run_safe_shutdown_loop`` daemon once before tests run.

    aiohttp's :py:meth:`ClientSession.close` spawns a long-lived daemon
    thread named ``_run_safe_shutdown_loop`` for graceful TLS shutdowns.
    The HA plugin's ``verify_cleanup`` fixture asserts that no new threads
    appear during a test. Triggering the thread once at session scope
    means it's part of the baseline and will not cause false-positive
    test teardown errors.
    """

    async def _spin() -> None:
        s = aiohttp.ClientSession()
        await s.close()

    asyncio.run(_spin())
