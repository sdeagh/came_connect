from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.core import callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import selector

from .const import (
    DOMAIN,
    # Setup fields
    CONF_CLIENT_ID, CONF_CLIENT_SECRET, CONF_USERNAME, CONF_PASSWORD, CONF_DEVICE_ID,
    # Options we still expose
    CONF_REDIRECT_URI, DEFAULT_REDIRECT_URI,
    # New WebSocket options
    CONF_WEBSOCKET_URL, DEFAULT_WEBSOCKET_URL,
)

# Initial setup schema: essentials only
STEP_USER_DATA_SCHEMA = vol.Schema({
    vol.Required(CONF_CLIENT_ID): str,
    vol.Required(CONF_CLIENT_SECRET): str,
    vol.Required(CONF_USERNAME): str,
    vol.Required(CONF_PASSWORD): str,
    vol.Required(CONF_DEVICE_ID): str,
})

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(
                title="CAME Connect",
                data={
                    CONF_CLIENT_ID: user_input[CONF_CLIENT_ID],
                    CONF_CLIENT_SECRET: user_input[CONF_CLIENT_SECRET],
                    CONF_USERNAME: user_input[CONF_USERNAME],
                    CONF_PASSWORD: user_input[CONF_PASSWORD],
                    CONF_DEVICE_ID: user_input[CONF_DEVICE_ID],
                },
            )
        return self.async_show_form(step_id="user", data_schema=STEP_USER_DATA_SCHEMA)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry):
        return CameConnectOptionsFlow()


class CameConnectOptionsFlow(config_entries.OptionsFlow):

    async def async_step_init(self, user_input: dict | None = None) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(
                data={
                    CONF_REDIRECT_URI: user_input[CONF_REDIRECT_URI].strip(),
                    CONF_WEBSOCKET_URL: user_input[CONF_WEBSOCKET_URL].strip(),
                }
            )

        entry = self.config_entry

        current_redirect = (
            entry.options.get(CONF_REDIRECT_URI)
            or entry.data.get(CONF_REDIRECT_URI)
            or DEFAULT_REDIRECT_URI
        )
        current_ws_url = entry.options.get(CONF_WEBSOCKET_URL, DEFAULT_WEBSOCKET_URL)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required(CONF_REDIRECT_URI, default=current_redirect):
                    selector.TextSelector(),

                vol.Required(CONF_WEBSOCKET_URL, default=current_ws_url):
                    selector.TextSelector(),
            }),
        )
