from __future__ import annotations

from datetime import timedelta
import logging
import aiohttp
import asyncio
import time

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DOMAIN, PLATFORMS,
    CONF_CLIENT_ID, CONF_CLIENT_SECRET, CONF_USERNAME, CONF_PASSWORD,
    CONF_REDIRECT_URI, CONF_DEVICE_ID, CONF_POLL_INTERVAL,
    DEFAULT_POLL_INTERVAL,
    DEFAULT_REDIRECT_URI,   # <-- ensure this exists in const.py (Step 1)
)
from .api import CameConnectClient

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config):
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    # --- NEW: seed default options if missing (so Options UI has values and code can read them) ---
    from .const import FAST_POLL_INTERVAL, FAST_POLL_DURATION

    opts = dict(entry.options) if entry.options else {}
    changed = False
    if CONF_REDIRECT_URI not in opts:
        opts[CONF_REDIRECT_URI] = DEFAULT_REDIRECT_URI
        changed = True
    if CONF_POLL_INTERVAL not in opts:
        opts[CONF_POLL_INTERVAL] = DEFAULT_POLL_INTERVAL
        changed = True
    if changed:
        hass.config_entries.async_update_entry(entry, options=opts)

    # --- Use redirect from options, but stay backward compatible with existing data entries ---
    redirect_uri = entry.options.get(
        CONF_REDIRECT_URI,
        entry.data.get(CONF_REDIRECT_URI, DEFAULT_REDIRECT_URI),
    )

    poll = entry.options.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL)
    device_id = entry.data[CONF_DEVICE_ID]

    session = aiohttp.ClientSession()
    client = CameConnectClient(
        session,
        entry.data[CONF_CLIENT_ID],
        entry.data[CONF_CLIENT_SECRET],
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
        redirect_uri,  # <-- was entry.data[CONF_REDIRECT_URI]
    )

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

    async def _start_fast_poll(seconds: int = FAST_POLL_DURATION, interval: int = FAST_POLL_INTERVAL):
        """Burst-poll the coordinator for near-realtime updates, then stop."""
        # Cancel any previous burst
        prior = hass.data[DOMAIN][entry.entry_id].get("fast_task")
        if prior and not prior.done():
            prior.cancel()

        async def _runner():
            end = time.monotonic() + max(1, seconds)
            try:
                while time.monotonic() < end:
                    await coordinator.async_request_refresh()
                    await asyncio.sleep(max(1, interval))
            except asyncio.CancelledError:
                pass
            finally:
                hass.data[DOMAIN][entry.entry_id]["fast_task"] = None

        task = hass.loop.create_task(_runner())
        hass.data[DOMAIN][entry.entry_id]["fast_task"] = task

    # expose the callable so platforms can use it
    hass.data[DOMAIN][entry.entry_id]["start_fast_poll"] = _start_fast_poll

    # --- NEW: auto-reload when Options change (so new poll interval/redirect applies) ---
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry):
    await hass.config_entries.async_reload(entry.entry_id)

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    data = hass.data[DOMAIN].pop(entry.entry_id, None)
    if data and data.get("session"):
        await data["session"].close()
    return unload_ok
