"""SolarMatrix HACS integration entry point."""

from __future__ import annotations

import asyncio
import logging
import random

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .api import SolarMatrixAPI
from .const import (
    CONF_API_KEY,
    CONF_BASE_URL,
    CONF_HID,
    CONF_SID,
    DEFAULT_BASE_URL,
    DOMAIN,
    JITTER_SECONDS,
)
from .coordinator import SolarMatrixCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]
_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up SolarMatrix from a config entry."""
    # Dedicated session per entry → ensures one keep-alive TCP/TLS conn.
    session = async_create_clientsession(hass)
    api = SolarMatrixAPI(
        session,
        entry.data.get(CONF_BASE_URL, DEFAULT_BASE_URL),
        entry.data[CONF_API_KEY],
    )

    coordinator = SolarMatrixCoordinator(
        hass, api, entry.data[CONF_SID], entry.data[CONF_HID]
    )

    # ±JITTER_SECONDS on the first refresh to de-sync independent installs.
    jitter = random.uniform(-JITTER_SECONDS, JITTER_SECONDS)
    if jitter > 0:
        await asyncio.sleep(jitter)

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unloaded
