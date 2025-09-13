from __future__ import annotations

import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    DOMAIN, PLATFORMS,
    # creds & device
    CONF_CLIENT_ID, CONF_CLIENT_SECRET, CONF_USERNAME, CONF_PASSWORD,
    CONF_REDIRECT_URI, CONF_DEVICE_ID, DEFAULT_REDIRECT_URI,
    # websocket options
    CONF_WEBSOCKET_URL, DEFAULT_WEBSOCKET_URL,
)
from .api import CameConnectClient, CameWebsocketClient
from .hub import CameEventHub

COORD_LOGGER = logging.getLogger(f"{__name__}.coordinator")
_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config):
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    # ---- ensure defaults / migrate options ----
    opts = dict(entry.options) if entry.options else {}
    changed = False

    if CONF_REDIRECT_URI not in opts:
        opts[CONF_REDIRECT_URI] = DEFAULT_REDIRECT_URI
        changed = True

    if CONF_WEBSOCKET_URL not in opts:
        opts[CONF_WEBSOCKET_URL] = DEFAULT_WEBSOCKET_URL
        changed = True

    if changed:
        hass.config_entries.async_update_entry(entry, options=opts)

    # Use the in-memory opts we just prepared
    current_opts = opts

    redirect_uri = (current_opts.get(CONF_REDIRECT_URI) or DEFAULT_REDIRECT_URI).strip()
    ws_url = (current_opts.get(CONF_WEBSOCKET_URL) or DEFAULT_WEBSOCKET_URL).strip()

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
        """One-shot/adhoc fetch; no periodic polling."""
        try:
            return await client.get_device_status(device_id)
        except Exception as e:
            raise UpdateFailed(str(e)) from e

    # Coordinator WITHOUT interval: we seed once, then push WS updates into it.
    coordinator = DataUpdateCoordinator(
        hass,
        COORD_LOGGER,
        name=f"{DOMAIN}-{device_id}",
        update_method=_async_update_data,
        update_interval=None,  # no periodic polling
    )

    # Initial seed from REST so entities start with correct state
    await coordinator.async_config_entry_first_refresh()

    # --- WebSocket hub wiring ---
    hub = CameEventHub(device_id)
    hub.seed_from_devicestatus(coordinator.data or {})

    async def _on_ws_event(code: int, value: int | None):
        """Apply WS event; push snapshot only if it represents a state change.
        """
        new_snapshot = hub.apply_event(code, value)
        if new_snapshot is None:
            _LOGGER.debug("WS code=%s value=%r ignored (no state change)", code, value)
            return

        # Push to entities (no await)
        coordinator.async_set_updated_data(new_snapshot)

    ws_client = CameWebsocketClient(
        session=session,
        ws_url=ws_url,
        token_getter=client.ensure_token,
        on_event=_on_ws_event,
    )
    await ws_client.start()

    # Stash shared objects
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "client": client,
        "coordinator": coordinator,
        "device_id": device_id,
        "ws_client": ws_client,
        "hub": hub,
    }

    # Reload the entry automatically on options change
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry):
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    # Unload platforms first
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        entry_data = hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
        if entry_data:
            # Stop WS if running
            ws_client: CameWebsocketClient | None = entry_data.get("ws_client")
            if ws_client:
                try:
                    await ws_client.stop()
                except Exception:
                    _LOGGER.debug("WS stop raised", exc_info=True)
        if not hass.data.get(DOMAIN):
            hass.data.pop(DOMAIN, None)
    return unload_ok
