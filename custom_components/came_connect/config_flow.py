from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import BptSetupPreview, CameApiError, CameAuthError, CameConnectClient
from .const import (
    CONF_BPT_DEVICE_TOKEN,
    CONF_BPT_KEYCODE,
    CONF_BPT_PANEL_ADDR,
    CONF_BPT_SIP_HA1,
    CONF_BPT_SIP_PASSWORD,
    CONF_BPT_SIP_USER,
    CONF_BPT_SRC_ADDR,
    CONF_BPT_SUBJECT_LABEL,
    CONF_BPT_TARGET_USER,
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_DEVICE_ID,
    CONF_PASSWORD,
    CONF_REDIRECT_URI,
    CONF_USERNAME,
    CONF_WEBSOCKET_URL,
    DEFAULT_REDIRECT_URI,
    DEFAULT_WEBSOCKET_URL,
    DOMAIN,
)

BPT_OPTION_KEYS = (
    CONF_BPT_KEYCODE,
    CONF_BPT_SIP_USER,
    CONF_BPT_SIP_PASSWORD,
    CONF_BPT_SIP_HA1,
    CONF_BPT_SRC_ADDR,
    CONF_BPT_TARGET_USER,
    CONF_BPT_PANEL_ADDR,
    CONF_BPT_SUBJECT_LABEL,
    CONF_BPT_DEVICE_TOKEN,
)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_CLIENT_ID): str,
        vol.Required(CONF_CLIENT_SECRET): str,
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Required(CONF_DEVICE_ID): str,
    }
)


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
    def _clean(self, user_input: dict, key: str) -> str:
        value = user_input.get(key, "")
        return value.strip() if isinstance(value, str) else ""

    def _current_options(self) -> dict[str, str]:
        entry = self.config_entry
        current_options = {
            CONF_REDIRECT_URI: (
                entry.options.get(CONF_REDIRECT_URI)
                or entry.data.get(CONF_REDIRECT_URI)
                or DEFAULT_REDIRECT_URI
            ),
            CONF_WEBSOCKET_URL: entry.options.get(CONF_WEBSOCKET_URL, DEFAULT_WEBSOCKET_URL),
        }
        for key in BPT_OPTION_KEYS:
            current_options[key] = entry.options.get(key, "")
        return current_options

    def _has_bpt_options(self) -> bool:
        current = self._current_options()
        return any(current.get(key, "") for key in BPT_OPTION_KEYS)

    def _build_options(
        self,
        *,
        updates: dict[str, str] | None = None,
        clear_bpt: bool = False,
    ) -> dict[str, str]:
        options = self._current_options()
        if updates:
            options.update(updates)
        if clear_bpt:
            for key in BPT_OPTION_KEYS:
                options[key] = ""
        return options

    @staticmethod
    def _text_selector() -> selector.TextSelector:
        return selector.TextSelector(
            selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
        )

    @staticmethod
    def _password_selector() -> selector.TextSelector:
        return selector.TextSelector(
            selector.TextSelectorConfig(
                type=selector.TextSelectorType.PASSWORD,
                autocomplete="current-password",
            )
        )

    def _make_client(self, options: dict[str, str]) -> CameConnectClient:
        entry = self.config_entry
        session = async_get_clientsession(self.hass)
        redirect_uri = (options.get(CONF_REDIRECT_URI) or DEFAULT_REDIRECT_URI).strip()
        return CameConnectClient(
            session,
            entry.data[CONF_CLIENT_ID],
            entry.data[CONF_CLIENT_SECRET],
            entry.data[CONF_USERNAME],
            entry.data[CONF_PASSWORD],
            redirect_uri,
        )

    async def _async_get_bpt_preview(
        self,
        options: dict[str, str],
    ) -> tuple[BptSetupPreview | None, str | None]:
        try:
            preview = await self._make_client(options).async_get_bpt_setup_preview(
                self.config_entry.data[CONF_DEVICE_ID],
                options,
            )
            return preview, None
        except (CameApiError, CameAuthError) as err:
            return None, str(err)
        except Exception as err:
            return None, f"Live BPT discovery is unavailable right now: {err}"

    @staticmethod
    def _slot_label(slot_sip_user: str, preview: BptSetupPreview | None) -> str:
        if preview is None:
            return slot_sip_user
        matched = next((slot for slot in preview.slots if slot.sip_user == slot_sip_user), None)
        if matched is None:
            return slot_sip_user
        return f"{matched.subject_label} ({matched.sip_user})"

    def _build_bpt_placeholders(
        self,
        preview: BptSetupPreview | None,
        discovery_message: str | None,
    ) -> dict[str, str]:
        if preview is None:
            return {
                "discovery_status": discovery_message
                or "Live BPT discovery is unavailable right now. You can still enter the Mobile App slot manually if needed.",
                "selected_sip_user": "Not resolved yet",
                "device_name": "Not resolved yet",
                "entry_panel_name": "Not resolved yet",
                "open_door_label": "Not resolved yet",
                "token_source": "Not resolved yet",
            }

        if preview.selected_slot is not None:
            selected_sip_user = f"{preview.selected_slot.subject_label} ({preview.selected_slot.sip_user})"
        elif len(preview.slots) == 1:
            slot = preview.slots[0]
            selected_sip_user = f"{slot.subject_label} ({slot.sip_user})"
        elif preview.slots:
            selected_sip_user = "Choose a Mobile App slot below"
        else:
            selected_sip_user = "Not resolved yet"

        if len(preview.slots) == 1:
            discovery_status = "One Mobile App slot was detected and will be used automatically."
        elif len(preview.slots) > 1:
            discovery_status = f"{len(preview.slots)} Mobile App slots were detected. Choose one below."
        else:
            discovery_status = (
                discovery_message
                or "BPT metadata was loaded, but no selectable Mobile App slots were resolved."
            )

        token_source = (
            "Manual device token override"
            if preview.token_source == "manual_override"
            else "Detected from /api/sipaccounts"
        )

        return {
            "discovery_status": discovery_status,
            "selected_sip_user": selected_sip_user,
            "device_name": preview.metadata.device_name,
            "entry_panel_name": preview.metadata.entry_panel_name,
            "open_door_label": preview.metadata.open_door_label,
            "token_source": token_source,
        }

    def _build_bpt_schema(
        self,
        current: dict[str, str],
        preview: BptSetupPreview | None,
    ) -> vol.Schema:
        schema: dict = {
            vol.Optional(CONF_BPT_SIP_PASSWORD, default=current[CONF_BPT_SIP_PASSWORD]):
                self._password_selector(),
        }

        current_sip_user = current[CONF_BPT_SIP_USER]
        if preview is None or not preview.slots:
            schema[
                vol.Optional(CONF_BPT_SIP_USER, default=current_sip_user)
            ] = self._text_selector()
            return vol.Schema(schema)

        slot_values = [slot.sip_user for slot in preview.slots]
        if len(preview.slots) == 1 and not current_sip_user:
            return vol.Schema(schema)

        if current_sip_user and current_sip_user not in slot_values:
            schema[
                vol.Optional(CONF_BPT_SIP_USER, default=current_sip_user)
            ] = self._text_selector()
            return vol.Schema(schema)

        select_options = [
            selector.SelectOptionDict(
                value=slot.sip_user,
                label=f"{slot.subject_label} ({slot.sip_user})",
            )
            for slot in preview.slots
        ]
        default_sip_user = current_sip_user or (
            preview.selected_slot.sip_user if preview.selected_slot is not None else ""
        )
        schema[
            vol.Optional(CONF_BPT_SIP_USER, default=default_sip_user)
        ] = selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=select_options,
                mode=selector.SelectSelectorMode.DROPDOWN,
            )
        )
        return vol.Schema(schema)

    async def async_step_init(self, user_input: dict | None = None) -> FlowResult:
        menu_options = ["cloud", "bpt", "bpt_advanced"]
        if self._has_bpt_options():
            menu_options.append("disable_bpt")
        return self.async_show_menu(step_id="init", menu_options=menu_options)

    async def async_step_cloud(self, user_input: dict | None = None) -> FlowResult:
        if user_input is not None:
            updates = {
                CONF_REDIRECT_URI: self._clean(user_input, CONF_REDIRECT_URI),
                CONF_WEBSOCKET_URL: self._clean(user_input, CONF_WEBSOCKET_URL),
            }
            return self.async_create_entry(data=self._build_options(updates=updates))

        current = self._current_options()
        return self.async_show_form(
            step_id="cloud",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_REDIRECT_URI, default=current[CONF_REDIRECT_URI]):
                        self._text_selector(),
                    vol.Required(CONF_WEBSOCKET_URL, default=current[CONF_WEBSOCKET_URL]):
                        self._text_selector(),
                }
            ),
        )

    async def async_step_bpt(self, user_input: dict | None = None) -> FlowResult:
        current = self._current_options()
        errors: dict[str, str] = {}

        if user_input is not None:
            selected_sip_user = self._clean(user_input, CONF_BPT_SIP_USER)
            preview_options = self._build_options(
                updates={CONF_BPT_SIP_USER: selected_sip_user}
            )
            preview, _ = await self._async_get_bpt_preview(preview_options)

            if preview is not None and len(preview.slots) == 1 and not selected_sip_user:
                selected_sip_user = preview.slots[0].sip_user

            if preview is not None and len(preview.slots) > 1 and not selected_sip_user:
                errors["base"] = "slot_required"
            else:
                updates = {
                    CONF_BPT_SIP_PASSWORD: self._clean(user_input, CONF_BPT_SIP_PASSWORD),
                    CONF_BPT_SIP_USER: selected_sip_user,
                }
                return self.async_create_entry(data=self._build_options(updates=updates))

        preview, discovery_message = await self._async_get_bpt_preview(current)
        return self.async_show_form(
            step_id="bpt",
            data_schema=self._build_bpt_schema(current, preview),
            errors=errors,
            description_placeholders=self._build_bpt_placeholders(preview, discovery_message),
        )

    async def async_step_bpt_advanced(self, user_input: dict | None = None) -> FlowResult:
        if user_input is not None:
            updates = {
                CONF_BPT_SIP_HA1: self._clean(user_input, CONF_BPT_SIP_HA1),
                CONF_BPT_DEVICE_TOKEN: self._clean(user_input, CONF_BPT_DEVICE_TOKEN),
                CONF_BPT_KEYCODE: self._clean(user_input, CONF_BPT_KEYCODE),
                CONF_BPT_SRC_ADDR: self._clean(user_input, CONF_BPT_SRC_ADDR),
                CONF_BPT_SUBJECT_LABEL: self._clean(user_input, CONF_BPT_SUBJECT_LABEL),
                CONF_BPT_TARGET_USER: self._clean(user_input, CONF_BPT_TARGET_USER),
                CONF_BPT_PANEL_ADDR: self._clean(user_input, CONF_BPT_PANEL_ADDR),
            }
            return self.async_create_entry(data=self._build_options(updates=updates))

        current = self._current_options()
        return self.async_show_form(
            step_id="bpt_advanced",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_BPT_SIP_HA1, default=current[CONF_BPT_SIP_HA1]):
                        self._password_selector(),
                    vol.Optional(CONF_BPT_DEVICE_TOKEN, default=current[CONF_BPT_DEVICE_TOKEN]):
                        self._password_selector(),
                    vol.Optional(CONF_BPT_KEYCODE, default=current[CONF_BPT_KEYCODE]):
                        self._text_selector(),
                    vol.Optional(CONF_BPT_SRC_ADDR, default=current[CONF_BPT_SRC_ADDR]):
                        self._text_selector(),
                    vol.Optional(CONF_BPT_SUBJECT_LABEL, default=current[CONF_BPT_SUBJECT_LABEL]):
                        self._text_selector(),
                    vol.Optional(CONF_BPT_TARGET_USER, default=current[CONF_BPT_TARGET_USER]):
                        self._text_selector(),
                    vol.Optional(CONF_BPT_PANEL_ADDR, default=current[CONF_BPT_PANEL_ADDR]):
                        self._text_selector(),
                }
            ),
        )

    async def async_step_disable_bpt(self, user_input: dict | None = None) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(data=self._build_options(clear_bpt=True))

        return self.async_show_form(step_id="disable_bpt", data_schema=vol.Schema({}))
