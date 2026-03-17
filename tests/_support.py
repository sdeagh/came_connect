from __future__ import annotations

import datetime as dt
import importlib.util
from pathlib import Path
import sys
import types

ROOT = Path(__file__).resolve().parents[1]


def ensure_custom_component_packages() -> None:
    custom_components_pkg = types.ModuleType("custom_components")
    custom_components_pkg.__path__ = [str(ROOT / "custom_components")]
    sys.modules.setdefault("custom_components", custom_components_pkg)

    came_connect_pkg = types.ModuleType("custom_components.came_connect")
    came_connect_pkg.__path__ = [str(ROOT / "custom_components" / "came_connect")]
    sys.modules.setdefault("custom_components.came_connect", came_connect_pkg)


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def install_homeassistant_stubs() -> None:
    if "homeassistant" in sys.modules:
        return

    homeassistant = types.ModuleType("homeassistant")
    sys.modules["homeassistant"] = homeassistant

    components = types.ModuleType("homeassistant.components")
    sys.modules["homeassistant.components"] = components

    button_mod = types.ModuleType("homeassistant.components.button")

    class ButtonEntity:
        @property
        def name(self):
            return getattr(self, "_attr_name", None)

        def async_write_ha_state(self) -> None:
            self._ha_state_written = True

    button_mod.ButtonEntity = ButtonEntity
    sys.modules["homeassistant.components.button"] = button_mod

    config_entries_mod = types.ModuleType("homeassistant.config_entries")

    class ConfigEntry:
        def __init__(self, *, data=None, options=None, entry_id: str = "entry-id"):
            self.data = data or {}
            self.options = options or {}
            self.entry_id = entry_id

    class ConfigFlow:
        def __init_subclass__(cls, **kwargs):
            return super().__init_subclass__()

        def async_show_form(self, *, step_id, data_schema=None, errors=None, description_placeholders=None):
            return {
                "type": "form",
                "step_id": step_id,
                "data_schema": data_schema,
                "errors": errors or {},
                "description_placeholders": description_placeholders,
            }

        def async_create_entry(self, *, title, data):
            return {"type": "create_entry", "title": title, "data": data}

    class OptionsFlow:
        config_entry: ConfigEntry

        def async_show_form(self, *, step_id, data_schema=None, errors=None, description_placeholders=None):
            return {
                "type": "form",
                "step_id": step_id,
                "data_schema": data_schema,
                "errors": errors or {},
                "description_placeholders": description_placeholders,
            }

        def async_create_entry(self, *, data):
            return {"type": "create_entry", "data": data}

        def async_show_menu(self, *, step_id, menu_options):
            return {"type": "menu", "step_id": step_id, "menu_options": menu_options}

    config_entries_mod.ConfigEntry = ConfigEntry
    config_entries_mod.ConfigFlow = ConfigFlow
    config_entries_mod.OptionsFlow = OptionsFlow
    sys.modules["homeassistant.config_entries"] = config_entries_mod

    core_mod = types.ModuleType("homeassistant.core")

    class HomeAssistant:
        pass

    def callback(func):
        return func

    core_mod.HomeAssistant = HomeAssistant
    core_mod.callback = callback
    sys.modules["homeassistant.core"] = core_mod

    data_entry_flow_mod = types.ModuleType("homeassistant.data_entry_flow")
    data_entry_flow_mod.FlowResult = dict
    sys.modules["homeassistant.data_entry_flow"] = data_entry_flow_mod

    exceptions_mod = types.ModuleType("homeassistant.exceptions")

    class HomeAssistantError(Exception):
        pass

    exceptions_mod.HomeAssistantError = HomeAssistantError
    sys.modules["homeassistant.exceptions"] = exceptions_mod

    helpers_mod = types.ModuleType("homeassistant.helpers")
    sys.modules["homeassistant.helpers"] = helpers_mod

    entity_mod = types.ModuleType("homeassistant.helpers.entity")

    class DeviceInfo(dict):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.__dict__.update(kwargs)

    entity_mod.DeviceInfo = DeviceInfo
    sys.modules["homeassistant.helpers.entity"] = entity_mod

    aiohttp_client_mod = types.ModuleType("homeassistant.helpers.aiohttp_client")

    def async_get_clientsession(hass):
        return object()

    aiohttp_client_mod.async_get_clientsession = async_get_clientsession
    sys.modules["homeassistant.helpers.aiohttp_client"] = aiohttp_client_mod

    selector_mod = types.ModuleType("homeassistant.helpers.selector")

    class TextSelectorType:
        TEXT = "text"
        PASSWORD = "password"

    class TextSelectorConfig:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    class TextSelector:
        def __init__(self, config):
            self.config = config

    class SelectSelectorMode:
        DROPDOWN = "dropdown"

    class SelectOptionDict(dict):
        def __init__(self, *, value, label):
            super().__init__(value=value, label=label)

    class SelectSelectorConfig:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    class SelectSelector:
        def __init__(self, config):
            self.config = config

    selector_mod.TextSelectorType = TextSelectorType
    selector_mod.TextSelectorConfig = TextSelectorConfig
    selector_mod.TextSelector = TextSelector
    selector_mod.SelectSelectorMode = SelectSelectorMode
    selector_mod.SelectOptionDict = SelectOptionDict
    selector_mod.SelectSelectorConfig = SelectSelectorConfig
    selector_mod.SelectSelector = SelectSelector
    sys.modules["homeassistant.helpers.selector"] = selector_mod

    util_mod = types.ModuleType("homeassistant.util")
    sys.modules["homeassistant.util"] = util_mod

    dt_mod = types.ModuleType("homeassistant.util.dt")

    def utcnow():
        return dt.datetime.now(dt.timezone.utc)

    dt_mod.utcnow = utcnow
    sys.modules["homeassistant.util.dt"] = dt_mod


def install_voluptuous_stub() -> None:
    if "voluptuous" in sys.modules:
        return

    voluptuous = types.ModuleType("voluptuous")
    sentinel = object()

    class Marker:
        def __init__(self, schema, default=sentinel, required=False):
            self.schema = schema
            self.default = default
            self.required = required

        def __hash__(self):
            return hash((self.schema, self.default, self.required))

        def __eq__(self, other):
            return (
                isinstance(other, Marker)
                and self.schema == other.schema
                and self.default == other.default
                and self.required == other.required
            )

    class Schema:
        def __init__(self, schema):
            self.schema = schema

        def __call__(self, value):
            return value

    def Required(schema, default=sentinel):
        return Marker(schema, default=default, required=True)

    def Optional(schema, default=sentinel):
        return Marker(schema, default=default, required=False)

    voluptuous.Schema = Schema
    voluptuous.Required = Required
    voluptuous.Optional = Optional
    voluptuous.UNDEFINED = sentinel
    sys.modules["voluptuous"] = voluptuous
