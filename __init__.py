
from __future__ import annotations

from datetime import timedelta
import logging
import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, PLATFORMS, CONF_CLIENT_ID, CONF_CLIENT_SECRET, CONF_USERNAME, CONF_PASSWORD, CONF_REDIRECT_URI, CONF_DEVICE_ID, CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL
from .api import CameConnectClient

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config):
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    session = aiohttp.ClientSession()
    client = CameConnectClient(
        session,
        entry.data[CONF_CLIENT_ID],
        entry.data[CONF_CLIENT_SECRET],
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
        entry.data[CONF_REDIRECT_URI],
    )

    poll = entry.options.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL)
    device_id = entry.data[CONF_DEVICE_ID]

    async def _async_update_data():
        try:
            return await client.get_device_status(device_id)
        except Exception as e:
            _LOGGER.warning("Update failed: %s", e)
            raise UpdateFailed(str(e)) from e

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=DOMAIN,
        update_method=_async_update_data,
        update_interval=timedelta(seconds=poll),
    )
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "client": client,
        "coordinator": coordinator,
        "device_id": device_id,
        "session": session,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    data = hass.data[DOMAIN].pop(entry.entry_id, None)
    if data and data.get("session"):
        await data["session"].close()
    return unload_ok
