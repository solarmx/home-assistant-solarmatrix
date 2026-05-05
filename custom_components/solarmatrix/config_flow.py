"""Config flow for SolarMatrix."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import APIError, AuthError, SolarMatrixAPI
from .const import (
    CONF_API_KEY,
    CONF_BASE_URL,
    CONF_HID,
    CONF_HOUSEHOLD_NAME,
    CONF_SID,
    CONF_SYSTEM_NAME,
    DEFAULT_BASE_URL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


def _build_api(session: aiohttp.ClientSession, base_url: str, key: str) -> SolarMatrixAPI:
    return SolarMatrixAPI(session, base_url, key)


class SolarMatrixConfigFlow(ConfigFlow, domain=DOMAIN):
    """Config flow for SolarMatrix."""

    VERSION = 1

    def __init__(self) -> None:
        self._api_key: str | None = None
        self._base_url: str = DEFAULT_BASE_URL
        # candidates is a list of (label, sid, hid, system_name, household_name).
        self._candidates: list[tuple[str, str, int, str, str]] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is None:
            return self._user_form()

        session = async_get_clientsession(self.hass)
        api = _build_api(
            session,
            user_input.get(CONF_BASE_URL, DEFAULT_BASE_URL),
            user_input[CONF_API_KEY],
        )

        try:
            systems = await api.list_systems()
        except AuthError:
            return self._user_form(errors={"base": "invalid_auth"})
        except APIError:
            return self._user_form(errors={"base": "cannot_connect"})

        if not systems:
            return self.async_abort(reason="no_systems")

        candidates: list[tuple[str, str, int, str, str]] = []
        for sys in systems:
            sid = sys["id"]
            system_name = sys.get("display_name") or sys.get("name") or "System"
            for hid in sys.get("household_indices", []):
                try:
                    hh = await api.get_household(sid, int(hid))
                except APIError:
                    continue
                household_name = hh.get("name") or f"Household {hid}"
                label = f"{system_name} — {household_name}"
                candidates.append((label, sid, int(hid), system_name, household_name))

        if not candidates:
            return self.async_abort(reason="no_households")

        self._api_key = user_input[CONF_API_KEY]
        self._base_url = user_input.get(CONF_BASE_URL, DEFAULT_BASE_URL)
        self._candidates = candidates

        # If exactly one household is reachable, skip the pick step.
        if len(candidates) == 1:
            label, sid, hid, _, _ = candidates[0]
            return await self.async_step_pick({"selection": f"{sid}|{hid}"})
        return await self.async_step_pick()

    async def async_step_pick(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        choices = {f"{sid}|{hid}": label for label, sid, hid, _, _ in self._candidates}

        if user_input is None:
            return self.async_show_form(
                step_id="pick",
                data_schema=vol.Schema({vol.Required("selection"): vol.In(choices)}),
            )

        sel = user_input["selection"]
        sid, hid_str = sel.split("|", 1)
        hid = int(hid_str)
        match = next(
            (c for c in self._candidates if c[1] == sid and c[2] == hid),
            None,
        )
        if match is None:
            return self.async_abort(reason="unknown_selection")

        unique_id = f"{sid}:{hid}"
        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured()

        _, _, _, system_name, household_name = match
        return self.async_create_entry(
            title=f"{system_name} — {household_name}",
            data={
                CONF_API_KEY: self._api_key,
                CONF_BASE_URL: self._base_url,
                CONF_SID: sid,
                CONF_HID: hid,
                CONF_SYSTEM_NAME: system_name,
                CONF_HOUSEHOLD_NAME: household_name,
            },
        )

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        entry = self._get_reauth_entry()
        if user_input is None:
            return self.async_show_form(
                step_id="reauth_confirm",
                data_schema=vol.Schema({vol.Required(CONF_API_KEY): str}),
            )

        session = async_get_clientsession(self.hass)
        api = _build_api(session, entry.data[CONF_BASE_URL], user_input[CONF_API_KEY])
        try:
            await api.list_systems()
        except AuthError:
            return self.async_show_form(
                step_id="reauth_confirm",
                data_schema=vol.Schema({vol.Required(CONF_API_KEY): str}),
                errors={"base": "invalid_auth"},
            )

        new_data = {**entry.data, CONF_API_KEY: user_input[CONF_API_KEY]}
        return self.async_update_reload_and_abort(entry, data=new_data)

    def _user_form(
        self, errors: dict[str, str] | None = None
    ) -> ConfigFlowResult:
        schema: dict[Any, Any] = {vol.Required(CONF_API_KEY): str}
        if self.show_advanced_options:
            schema[vol.Optional(CONF_BASE_URL, default=DEFAULT_BASE_URL)] = str
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(schema),
            errors=errors or {},
            description_placeholders={
                "api_keys_url": "https://app.solarmatrix.eu/settings/api-keys",
            },
        )
