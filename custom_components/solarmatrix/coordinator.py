"""SolarMatrix DataUpdateCoordinator with backoff."""

from __future__ import annotations

import logging
from datetime import timedelta

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryError
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .api import (
    AccessError,
    APIError,
    AuthError,
    NotFoundError,
    RateLimitError,
    Snapshot,
    SolarMatrixAPI,
    UnavailableError,
)
from .const import BACKOFF_CAP, BACKOFF_FLOOR, DOMAIN, POLL_INTERVAL

_LOGGER = logging.getLogger(__name__)


class SolarMatrixCoordinator(DataUpdateCoordinator[Snapshot]):
    """Coordinator that polls one household's snapshot every POLL_INTERVAL."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: SolarMatrixAPI,
        sid: str,
        hid: int,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}:{sid}:{hid}",
            update_interval=POLL_INTERVAL,
        )
        self.api = api
        self.sid = sid
        self.hid = hid
        self._consec_fails = 0

    async def _async_update_data(self) -> Snapshot:
        try:
            snap = await self.api.get_snapshot(self.sid, self.hid)
        except RateLimitError as exc:
            self.update_interval = timedelta(seconds=exc.retry_after)
            raise UpdateFailed(f"rate limited; retry_after={exc.retry_after}") from exc
        except AuthError as exc:
            raise ConfigEntryAuthFailed(str(exc)) from exc
        except (AccessError, NotFoundError) as exc:
            raise ConfigEntryError(f"household no longer accessible: {exc}") from exc
        except UnavailableError as exc:
            self._on_failure()
            raise UpdateFailed(f"system unavailable: {exc}") from exc
        except APIError as exc:
            self._on_failure()
            raise UpdateFailed(f"api error: {exc}") from exc
        except (aiohttp.ClientError, TimeoutError) as exc:
            self._on_failure()
            raise UpdateFailed(f"transport error: {exc}") from exc

        self._on_success()
        return snap

    def _on_success(self) -> None:
        if self._consec_fails:
            self._consec_fails = 0
            self.update_interval = POLL_INTERVAL

    def _on_failure(self) -> None:
        self._consec_fails += 1
        secs = int(BACKOFF_FLOOR.total_seconds()) * (2 ** (self._consec_fails - 1))
        if secs > int(BACKOFF_CAP.total_seconds()):
            secs = int(BACKOFF_CAP.total_seconds())
        self.update_interval = timedelta(seconds=secs)
