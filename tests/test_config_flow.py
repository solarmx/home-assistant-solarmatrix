"""Tests for the SolarMatrix config flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.solarmatrix.api import AuthError
from custom_components.solarmatrix.const import (
    CONF_API_KEY,
    CONF_HID,
    CONF_HOUSEHOLD_NAME,
    CONF_SID,
    CONF_SYSTEM_NAME,
    DOMAIN,
)


@pytest.fixture
def fake_api():
    api = AsyncMock()
    api.list_systems.return_value = [
        {"id": "sid-A", "display_name": "House A", "household_indices": [0, 1]},
        {"id": "sid-B", "display_name": "House B", "household_indices": [0]},
    ]

    async def get_household(sid: str, hid: int):
        names = {
            ("sid-A", 0): "WE05",
            ("sid-A", 1): "WE07",
            ("sid-B", 0): "Cabin",
        }
        return {"household_id": hid, "name": names[(sid, hid)]}

    api.get_household.side_effect = get_household
    return api


async def test_user_step_invalid_key(hass: HomeAssistant) -> None:
    api = AsyncMock()
    api.list_systems.side_effect = AuthError("nope")
    with patch("custom_components.solarmatrix.config_flow._build_api", return_value=api):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_API_KEY: "bad"}
        )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_full_flow_creates_entry(hass: HomeAssistant, fake_api) -> None:
    with patch("custom_components.solarmatrix.config_flow._build_api", return_value=fake_api):
        first = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
        pick = await hass.config_entries.flow.async_configure(
            first["flow_id"], {CONF_API_KEY: "sm_x"}
        )
        assert pick["type"] == FlowResultType.FORM
        assert pick["step_id"] == "pick"
        # Three options: A:0, A:1, B:0.
        schema_keys = list(pick["data_schema"].schema.keys())
        assert any(
            "sid" in str(k) or "household" in str(k) or "selection" in str(k)
            for k in schema_keys
        )

        result = await hass.config_entries.flow.async_configure(
            pick["flow_id"], {"selection": "sid-A|0"}
        )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_SID] == "sid-A"
    assert result["data"][CONF_HID] == 0
    assert result["data"][CONF_HOUSEHOLD_NAME] == "WE05"
    assert result["data"][CONF_SYSTEM_NAME] == "House A"


async def test_duplicate_household_blocked(hass: HomeAssistant, fake_api) -> None:
    # Pre-create an entry for sid-A:0.
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="House A — WE05",
        data={
            CONF_API_KEY: "sm_x",
            CONF_SID: "sid-A",
            CONF_HID: 0,
            CONF_SYSTEM_NAME: "House A",
            CONF_HOUSEHOLD_NAME: "WE05",
        },
        unique_id="sid-A:0",
    )
    entry.add_to_hass(hass)

    with patch("custom_components.solarmatrix.config_flow._build_api", return_value=fake_api):
        first = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
        pick = await hass.config_entries.flow.async_configure(
            first["flow_id"], {CONF_API_KEY: "sm_x"}
        )
        result = await hass.config_entries.flow.async_configure(
            pick["flow_id"], {"selection": "sid-A|0"}
        )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"
