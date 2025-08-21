from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    DOMAIN, PLATFORMS,
    CONF_CLIENT_ID, CONF_CLIENT_SECRET, CONF_USERNAME, CONF_PASSWORD,
    CONF_REDIRECT_URI, CONF_DEVICE_ID, CONF_POLL_INTERVAL,
    DEFAULT_POLL_INTERVAL,
    DEFAULT_REDIRECT_URI, 
)
from .api import CameConnectClient

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config):
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):

    opts = dict(entry.options) if entry.options else {}
    changed = False
    if CONF_REDIRECT_URI not in opts:
        opts[CONF_REDIRECT_URI] = DEFAULT_REDIRECT_URI
        changed = True
    if CONF_POLL_INTERVAL not in opts:
        opts[CONF_POLL_INTERVAL] = DEFAULT_POLL_INTERVAL
        changed = True
    if changed:
        _LOGGER.debug("Seeding default options: %s", opts)
        hass.config_entries.async_update_entry(entry, options=opts)

    # --- Use redirect from options, but stay backward compatible with existing data entries ---
    redirect_uri = entry.options.get(
        CONF_REDIRECT_URI,
        entry.data.get(CONF_REDIRECT_URI, DEFAULT_REDIRECT_URI),
    )

    raw = entry.options.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL)
    try:
        poll = max(5, int(raw))  # don’t let it go lower than 5s
    except (TypeError, ValueError):
        poll = max(5, DEFAULT_POLL_INTERVAL)

    device_id = entry.data[CONF_DEVICE_ID]

    _LOGGER.debug(
        "Setting up entry %s (device_id=%s) with poll=%ss, redirect_uri=%s",
        entry.entry_id, device_id, poll, redirect_uri
    )

    session = async_get_clientsession(hass)
    client = CameConnectClient(
        session,
        entry.data[CONF_CLIENT_ID],
        entry.data[CONF_CLIENT_SECRET],
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
        redirect_uri,
    )

    async def _async_update_data():
        try:
            _LOGGER.debug("Coordinator polling device %s…", device_id)
            data = await client.get_device_status(device_id)
            _LOGGER.debug("Coordinator received status for %s: %s", device_id, data)
            return data
        except Exception as e:
            _LOGGER.warning("Update failed for %s: %s", device_id, e)
            raise UpdateFailed(str(e)) from e

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"{DOMAIN}-{device_id}",
        update_method=_async_update_data,
        update_interval=timedelta(seconds=poll),
    )
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "client": client,
        "coordinator": coordinator,
        "device_id": device_id,
    }

    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry):
    await hass.config_entries.async_reload(entry.entry_id)

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        domain_data = hass.data.get(DOMAIN)
        if domain_data:
            domain_data.pop(entry.entry_id, None)
            if not domain_data:
                hass.data.pop(DOMAIN, None)
    return unload_ok