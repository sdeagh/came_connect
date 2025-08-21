
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN, CONF_CLIENT_ID, CONF_CLIENT_SECRET, CONF_USERNAME, CONF_PASSWORD, CONF_REDIRECT_URI, CONF_DEVICE_ID, CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL

STEP_USER_DATA_SCHEMA = vol.Schema({
    vol.Required(CONF_CLIENT_ID): str,
    vol.Required(CONF_CLIENT_SECRET): str,
    vol.Required(CONF_USERNAME): str,
    vol.Required(CONF_PASSWORD): str,
    vol.Required(CONF_REDIRECT_URI): str,
    vol.Required(CONF_DEVICE_ID): str,
    vol.Optional(CONF_POLL_INTERVAL, default=DEFAULT_POLL_INTERVAL): int,
})

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        errors = {}
        if user_input is not None:
            try:
                int(user_input[CONF_POLL_INTERVAL])
            except Exception:
                errors["base"] = "invalid_poll"
            if not errors:
                return self.async_create_entry(
                    title="CAME Connect",
                    data={
                        "client_id": user_input["client_id"],
                        "client_secret": user_input["client_secret"],
                        "username": user_input["username"],
                        "password": user_input["password"],
                        "redirect_uri": user_input["redirect_uri"],
                        "device_id": user_input["device_id"],
                    },
                    options={"poll_interval": user_input["poll_interval"]},
                )
        return self.async_show_form(step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors)
