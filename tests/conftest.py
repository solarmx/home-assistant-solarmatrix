"""Pytest fixtures for SolarMatrix tests."""

from __future__ import annotations

import asyncio
from typing import Any

import aiohttp
import pytest


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: Any) -> Any:
    """Enable custom integration loading for every test."""
    yield


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
