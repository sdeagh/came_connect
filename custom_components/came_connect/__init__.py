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
    DEFAULT_POLL_INTERVAL, DEFAULT_REDIRECT_URI,
    CONF_MOVING_POLL_INTERVAL, CONF_MOTION_TIMEOUT,         
    DEFAULT_MOVING_POLL_INTERVAL, MOTION_TIMEOUT_SECONDS,
)

from .api import CameConnectClient

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config):
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    # --- ensure defaults / migrate ---
    opts = dict(entry.options) if entry.options else {}
    changed = False

    if CONF_REDIRECT_URI not in opts:
        opts[CONF_REDIRECT_URI] = DEFAULT_REDIRECT_URI
        changed = True

    opt_poll = opts.get(CONF_POLL_INTERVAL)
    if opt_poll is None or str(opt_poll) == "5":
        opts[CONF_POLL_INTERVAL] = DEFAULT_POLL_INTERVAL  # 300
        changed = True

    if CONF_MOVING_POLL_INTERVAL not in opts:
        opts[CONF_MOVING_POLL_INTERVAL] = DEFAULT_MOVING_POLL_INTERVAL  # 2
        changed = True

    if CONF_MOTION_TIMEOUT not in opts:
        opts[CONF_MOTION_TIMEOUT] = MOTION_TIMEOUT_SECONDS  # 120
        changed = True

    if changed:
        hass.config_entries.async_update_entry(entry, options=opts)

    # Use the in-memory opts we just prepared (entry.options may not reflect updates yet)
    current_opts = opts

    # ---- heartbeat / idle poll interval ----
    raw = (current_opts.get(CONF_POLL_INTERVAL)
           or entry.data.get(CONF_POLL_INTERVAL)
           or DEFAULT_POLL_INTERVAL)
    try:
        poll = int(raw)
    except (TypeError, ValueError):
        poll = DEFAULT_POLL_INTERVAL  # 300

    # ---- redirect URI for OAuth ----
    redirect_uri = (
        current_opts.get(CONF_REDIRECT_URI)
        or entry.data.get(CONF_REDIRECT_URI)
        or DEFAULT_REDIRECT_URI
    ).strip()

    moving_poll = int(
        (current_opts.get(CONF_MOVING_POLL_INTERVAL) or DEFAULT_MOVING_POLL_INTERVAL)
    )
    motion_timeout = int(
        (current_opts.get(CONF_MOTION_TIMEOUT) or MOTION_TIMEOUT_SECONDS)
    )

    _LOGGER.debug(
        "CAME Connect: moving_poll=%ss, motion_timeout=%ss",
        moving_poll, motion_timeout
    )

    device_id = entry.data[CONF_DEVICE_ID]

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
            return await client.get_device_status(device_id)
        except Exception as e:
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
        "moving_poll_interval": moving_poll,
        "motion_timeout": motion_timeout,
    }

    # You chose OptionsFlow + update listener (no WithReload)
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