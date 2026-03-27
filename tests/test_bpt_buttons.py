from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock
import unittest

from _support import ROOT, ensure_custom_component_packages, install_homeassistant_stubs, load_module

ensure_custom_component_packages()
install_homeassistant_stubs()

const_module = load_module(
    "custom_components.came_connect.const",
    ROOT / "custom_components" / "came_connect" / "const.py",
)
api_module = load_module(
    "custom_components.came_connect.api",
    ROOT / "custom_components" / "came_connect" / "api.py",
)
button_module = load_module(
    "custom_components.came_connect.button",
    ROOT / "custom_components" / "came_connect" / "button.py",
)

from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import HomeAssistantError

DOMAIN = const_module.DOMAIN
CONF_BPT_SIP_PASSWORD = const_module.CONF_BPT_SIP_PASSWORD

BptAuxFeature = api_module.BptAuxFeature
BptDeviceMetadata = api_module.BptDeviceMetadata
BptDoorConfig = api_module.BptDoorConfig
CameBptAuxButton = button_module.CameBptAuxButton
CameBptDoorButton = button_module.CameBptDoorButton

DUMMY_DEVICE_ID = "dummy-device-id-1"
DUMMY_DEVICE_NAME = "Example Indoor Monitor"
DUMMY_ENTRY_PANEL_NAME = "Example Entry Panel"
DUMMY_UNIT_NAME = "Example Unit"
DUMMY_OPEN_DOOR_LABEL = "Example Open Door"
DUMMY_AUX_ONE_LABEL = "Demo Aux One"
DUMMY_KEYCODE = "EXAMPLEKEYCODE01"
DUMMY_SIP_USER = "dummy_sip_user_2"
DUMMY_PASSWORD = "dummy-password"
DUMMY_SRC_ADDR = "dummy-src-2"
DUMMY_TARGET_USER = "dummy-target-user"
DUMMY_PANEL_ADDR = "dummy-panel-addr"
DUMMY_SUBJECT_LABEL = "Demo Mobile Slot 2"
DUMMY_DEVICE_TOKEN = "dummy-device-token-1"


def _metadata() -> BptDeviceMetadata:
    return BptDeviceMetadata(
        device_name=DUMMY_DEVICE_NAME,
        entry_panel_name=DUMMY_ENTRY_PANEL_NAME,
        unit_name=DUMMY_UNIT_NAME,
        open_door_label=DUMMY_OPEN_DOOR_LABEL,
        aux_features=(
            BptAuxFeature(aux_code=1, feature_id=8, name="Aux 1", label=DUMMY_AUX_ONE_LABEL, icon="light.png"),
            BptAuxFeature(aux_code=2, feature_id=9, name="Aux 2", label="Aux 2", icon="light.png"),
        ),
        model="CAME BPT X1",
    )


def _config() -> BptDoorConfig:
    return BptDoorConfig(
        keycode=DUMMY_KEYCODE,
        sip_user=DUMMY_SIP_USER,
        sip_password=DUMMY_PASSWORD,
        src_addr=DUMMY_SRC_ADDR,
        target_user=DUMMY_TARGET_USER,
        panel_addr=DUMMY_PANEL_ADDR,
        subject_label=DUMMY_SUBJECT_LABEL,
        device_token=DUMMY_DEVICE_TOKEN,
    )


class BptButtonTests(unittest.IsolatedAsyncioTestCase):
    async def test_async_setup_entry_creates_door_and_aux_buttons(self) -> None:
        metadata = _metadata()
        client = SimpleNamespace(async_get_bpt_device_metadata=AsyncMock(return_value=metadata))
        hass = SimpleNamespace(
            data={
                DOMAIN: {
                    "entry-id": {
                        "client": client,
                        "device_id": DUMMY_DEVICE_ID,
                    }
                }
            }
        )
        entry = ConfigEntry(
            options={CONF_BPT_SIP_PASSWORD: "pw"},
            entry_id="entry-id",
        )
        added: list = []

        await button_module.async_setup_entry(hass, entry, added.extend)

        self.assertEqual(len(added), 3)
        self.assertIsInstance(added[0], CameBptDoorButton)
        self.assertIsInstance(added[1], CameBptAuxButton)
        self.assertEqual(added[1].name, DUMMY_AUX_ONE_LABEL)
        self.assertEqual(added[2].name, "Aux 2")

    async def test_async_setup_entry_falls_back_to_only_door_button_on_metadata_error(self) -> None:
        client = SimpleNamespace(async_get_bpt_device_metadata=AsyncMock(side_effect=RuntimeError("no metadata")))
        hass = SimpleNamespace(
            data={
                DOMAIN: {
                    "entry-id": {
                        "client": client,
                        "device_id": DUMMY_DEVICE_ID,
                    }
                }
            }
        )
        entry = ConfigEntry(
            options={CONF_BPT_SIP_PASSWORD: "pw"},
            entry_id="entry-id",
        )
        added: list = []

        await button_module.async_setup_entry(hass, entry, added.extend)

        self.assertEqual(len(added), 1)
        self.assertIsInstance(added[0], CameBptDoorButton)
        self.assertEqual(added[0].name, "Open Door")

    async def test_aux_button_press_calls_client_and_records_status(self) -> None:
        metadata = _metadata()
        feature = metadata.aux_features[1]
        config = _config()
        client = SimpleNamespace(
            async_resolve_bpt_door_config=AsyncMock(return_value=config),
            async_open_bpt_aux=AsyncMock(
                return_value={
                    "register_status": "SIP/2.0 200 OK",
                    "message_status": "SIP/2.0 202 Accepted",
                    "xipregister_status": 403,
                }
            ),
        )
        button = CameBptAuxButton(client, DUMMY_DEVICE_ID, {CONF_BPT_SIP_PASSWORD: "pw"}, feature, metadata)

        await button.async_press()

        client.async_open_bpt_aux.assert_awaited_once_with(config, 2)
        attrs = button.extra_state_attributes
        self.assertEqual(attrs["last_register_status"], "SIP/2.0 200 OK")
        self.assertEqual(attrs["last_message_status"], "SIP/2.0 202 Accepted")
        self.assertEqual(attrs["last_xipregister_status"], "403")
        self.assertEqual(attrs["bpt_aux_code"], 2)
        self.assertIsNone(attrs["last_error"])

    async def test_door_button_press_failure_sets_last_error(self) -> None:
        metadata = _metadata()
        config = _config()
        client = SimpleNamespace(
            async_resolve_bpt_door_config=AsyncMock(return_value=config),
            async_open_bpt_door=AsyncMock(side_effect=RuntimeError("boom")),
        )
        button = CameBptDoorButton(client, DUMMY_DEVICE_ID, {CONF_BPT_SIP_PASSWORD: "pw"}, metadata)

        with self.assertRaises(HomeAssistantError) as ctx:
            await button.async_press()

        self.assertIn("Open door failed", str(ctx.exception))
        self.assertEqual(button.extra_state_attributes["last_error"], "boom")


if __name__ == "__main__":
    unittest.main()
