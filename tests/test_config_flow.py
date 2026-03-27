from __future__ import annotations

import unittest
from unittest.mock import AsyncMock

from _support import (
    ROOT,
    ensure_custom_component_packages,
    install_homeassistant_stubs,
    install_voluptuous_stub,
    load_module,
)

ensure_custom_component_packages()
install_homeassistant_stubs()
install_voluptuous_stub()

const_module = load_module(
    "custom_components.came_connect.const",
    ROOT / "custom_components" / "came_connect" / "const.py",
)
api_module = load_module(
    "custom_components.came_connect.api",
    ROOT / "custom_components" / "came_connect" / "api.py",
)
config_flow_module = load_module(
    "custom_components.came_connect.config_flow",
    ROOT / "custom_components" / "came_connect" / "config_flow.py",
)

from homeassistant.config_entries import ConfigEntry

BptDeviceMetadata = api_module.BptDeviceMetadata
BptMobileSlot = api_module.BptMobileSlot
BptSetupPreview = api_module.BptSetupPreview
CameConnectOptionsFlow = config_flow_module.CameConnectOptionsFlow
CONF_BPT_SIP_PASSWORD = const_module.CONF_BPT_SIP_PASSWORD
CONF_BPT_SIP_USER = const_module.CONF_BPT_SIP_USER
CONF_CLIENT_ID = const_module.CONF_CLIENT_ID
CONF_CLIENT_SECRET = const_module.CONF_CLIENT_SECRET
CONF_DEVICE_ID = const_module.CONF_DEVICE_ID
CONF_PASSWORD = const_module.CONF_PASSWORD
CONF_USERNAME = const_module.CONF_USERNAME

DUMMY_DEVICE_ID = "dummy-device-id-1"
DUMMY_DEVICE_NAME = "Example Indoor Monitor"
DUMMY_ENTRY_PANEL_NAME = "Example Entry Panel"
DUMMY_UNIT_NAME = "Example Unit"
DUMMY_OPEN_DOOR_LABEL = "Example Open Door"
DUMMY_SIP_USER_ONE = "dummy_sip_user_1"
DUMMY_SIP_USER_TWO = "dummy_sip_user_2"
DUMMY_SRC_ADDR_ONE = "dummy-src-1"
DUMMY_SRC_ADDR_TWO = "dummy-src-2"
DUMMY_SLOT_ONE_LABEL = "Demo Mobile Slot 1"
DUMMY_SLOT_TWO_LABEL = "Demo Mobile Slot 2"
DUMMY_PASSWORD = "dummy-password"


def _metadata() -> BptDeviceMetadata:
    return BptDeviceMetadata(
        device_name=DUMMY_DEVICE_NAME,
        entry_panel_name=DUMMY_ENTRY_PANEL_NAME,
        unit_name=DUMMY_UNIT_NAME,
        open_door_label=DUMMY_OPEN_DOOR_LABEL,
        aux_features=(),
        model="CAME BPT X1",
    )


def _preview(slots: tuple[BptMobileSlot, ...], selected_slot: BptMobileSlot | None = None) -> BptSetupPreview:
    return BptSetupPreview(
        slots=slots,
        selected_slot=selected_slot,
        metadata=_metadata(),
        token_source="sipaccounts",
    )


def _flow(options: dict[str, str] | None = None) -> CameConnectOptionsFlow:
    flow = CameConnectOptionsFlow()
    flow.hass = object()
    flow.config_entry = ConfigEntry(
        data={
            CONF_CLIENT_ID: "client",
            CONF_CLIENT_SECRET: "secret",
            CONF_USERNAME: "user",
            CONF_PASSWORD: "pass",
            CONF_DEVICE_ID: DUMMY_DEVICE_ID,
        },
        options=options or {},
        entry_id="entry-id",
    )
    return flow


def _schema_value(schema, key: str):
    for marker, value in schema.schema.items():
        if getattr(marker, "schema", None) == key:
            return value
    return None


class ConfigFlowTests(unittest.IsolatedAsyncioTestCase):
    async def test_async_step_bpt_auto_picks_single_slot(self) -> None:
        slot = BptMobileSlot(
            sip_user=DUMMY_SIP_USER_TWO,
            src_addr=DUMMY_SRC_ADDR_TWO,
            subject_label=DUMMY_SLOT_TWO_LABEL,
        )
        flow = _flow()
        preview = _preview((slot,), selected_slot=slot)
        flow._async_get_bpt_preview = AsyncMock(return_value=(preview, None))

        result = await flow.async_step_bpt({CONF_BPT_SIP_PASSWORD: DUMMY_PASSWORD})

        self.assertEqual(result["type"], "create_entry")
        self.assertEqual(result["data"][CONF_BPT_SIP_PASSWORD], DUMMY_PASSWORD)
        self.assertEqual(result["data"][CONF_BPT_SIP_USER], DUMMY_SIP_USER_TWO)

    async def test_async_step_bpt_requires_selection_when_multiple_slots_exist(self) -> None:
        slot_one = BptMobileSlot(
            sip_user=DUMMY_SIP_USER_ONE,
            src_addr=DUMMY_SRC_ADDR_ONE,
            subject_label=DUMMY_SLOT_ONE_LABEL,
        )
        slot_two = BptMobileSlot(
            sip_user=DUMMY_SIP_USER_TWO,
            src_addr=DUMMY_SRC_ADDR_TWO,
            subject_label=DUMMY_SLOT_TWO_LABEL,
        )
        flow = _flow()
        preview = _preview((slot_one, slot_two))
        flow._async_get_bpt_preview = AsyncMock(side_effect=[(preview, None), (preview, None)])

        result = await flow.async_step_bpt({CONF_BPT_SIP_PASSWORD: DUMMY_PASSWORD})

        self.assertEqual(result["type"], "form")
        self.assertEqual(result["errors"]["base"], "slot_required")

    async def test_build_bpt_schema_uses_dropdown_for_multiple_slots(self) -> None:
        slot_one = BptMobileSlot(
            sip_user=DUMMY_SIP_USER_ONE,
            src_addr=DUMMY_SRC_ADDR_ONE,
            subject_label=DUMMY_SLOT_ONE_LABEL,
        )
        slot_two = BptMobileSlot(
            sip_user=DUMMY_SIP_USER_TWO,
            src_addr=DUMMY_SRC_ADDR_TWO,
            subject_label=DUMMY_SLOT_TWO_LABEL,
        )
        flow = _flow()

        schema = flow._build_bpt_schema(flow._current_options(), _preview((slot_one, slot_two)))
        field = _schema_value(schema, CONF_BPT_SIP_USER)

        self.assertIsNotNone(field)
        self.assertEqual(field.__class__.__name__, "SelectSelector")
        self.assertEqual(len(field.config.options), 2)
        self.assertEqual(field.config.options[0]["label"], f"{DUMMY_SLOT_ONE_LABEL} ({DUMMY_SIP_USER_ONE})")

    async def test_build_bpt_placeholders_report_detected_token_source(self) -> None:
        slot = BptMobileSlot(
            sip_user=DUMMY_SIP_USER_TWO,
            src_addr=DUMMY_SRC_ADDR_TWO,
            subject_label=DUMMY_SLOT_TWO_LABEL,
        )
        flow = _flow()

        placeholders = flow._build_bpt_placeholders(_preview((slot,), selected_slot=slot), None)

        self.assertEqual(placeholders["device_name"], DUMMY_DEVICE_NAME)
        self.assertEqual(placeholders["entry_panel_name"], DUMMY_ENTRY_PANEL_NAME)
        self.assertEqual(placeholders["open_door_label"], DUMMY_OPEN_DOOR_LABEL)
        self.assertEqual(placeholders["token_source"], "Detected from /api/sipaccounts")


if __name__ == "__main__":
    unittest.main()
