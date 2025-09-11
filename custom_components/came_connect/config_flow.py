from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.core import callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import selector


from .const import (
    DOMAIN,
    CONF_CLIENT_ID, CONF_CLIENT_SECRET, CONF_USERNAME, CONF_PASSWORD, CONF_DEVICE_ID,
    CONF_REDIRECT_URI, CONF_POLL_INTERVAL,
    DEFAULT_REDIRECT_URI, DEFAULT_POLL_INTERVAL,
    CONF_MOVING_POLL_INTERVAL, CONF_MOTION_TIMEOUT,
)

# Initial setup schema: ONLY essentials (no redirect, no poll)
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
    """Options UI for Redirect URI and Poll Interval."""

    async def async_step_init(self, user_input: dict | None = None) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(
                data={
                    CONF_REDIRECT_URI: user_input[CONF_REDIRECT_URI].strip(),
                    CONF_POLL_INTERVAL: int(user_input[CONF_POLL_INTERVAL]),
                    CONF_MOVING_POLL_INTERVAL: int(user_input[CONF_MOVING_POLL_INTERVAL]),
                    CONF_MOTION_TIMEOUT: int(user_input[CONF_MOTION_TIMEOUT]),
                }
            )

        # Read current values: options → data → defaults
        entry = self.config_entry

        current_redirect = (
            entry.options.get(CONF_REDIRECT_URI)
            or entry.data.get(CONF_REDIRECT_URI)
            or DEFAULT_REDIRECT_URI
        )
        current_poll = (
            entry.options.get(CONF_POLL_INTERVAL)
            or entry.data.get(CONF_POLL_INTERVAL)
            or DEFAULT_POLL_INTERVAL
        )
        current_moving_poll = entry.options.get(CONF_MOVING_POLL_INTERVAL, 2)
        current_motion_timeout = entry.options.get(CONF_MOTION_TIMEOUT, 120)

        try:
            current_poll = int(current_poll)
        except (TypeError, ValueError):
            current_poll = DEFAULT_POLL_INTERVAL
        try:
            current_moving_poll = int(current_moving_poll)
        except (TypeError, ValueError):
            current_moving_poll = 2
        try:
            current_motion_timeout = int(current_motion_timeout)
        except (TypeError, ValueError):
            current_motion_timeout = 120

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                # URL as a proper text field
                vol.Required(CONF_REDIRECT_URI, default=current_redirect):
                    selector.TextSelector(),

                # Idle heartbeat: numeric box (not a slider) with units
                vol.Required(CONF_POLL_INTERVAL, default=current_poll):
                    selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=60, max=3600, step=10,
                            unit_of_measurement="s",
                            mode="slider"           
                        )
                    ),

                # Fast poll while moving: short slider
                vol.Required(CONF_MOVING_POLL_INTERVAL, default=current_moving_poll):
                    selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=1, max=5, step=1,
                            unit_of_measurement="s",
                            mode="slider"        
                        )
                    ),

                # Motion timeout: slider
                vol.Required(CONF_MOTION_TIMEOUT, default=current_motion_timeout):
                    selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=60, max=300, step=5,
                            unit_of_measurement="s",
                            mode="slider"        
                        )
                    ),
            }),
        )

