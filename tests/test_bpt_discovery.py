from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import types
from unittest.mock import AsyncMock
import unittest

ROOT = Path(__file__).resolve().parents[1]

custom_components_pkg = types.ModuleType("custom_components")
custom_components_pkg.__path__ = [str(ROOT / "custom_components")]
sys.modules.setdefault("custom_components", custom_components_pkg)

came_connect_pkg = types.ModuleType("custom_components.came_connect")
came_connect_pkg.__path__ = [str(ROOT / "custom_components" / "came_connect")]
sys.modules.setdefault("custom_components.came_connect", came_connect_pkg)


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


const_module = _load_module(
    "custom_components.came_connect.const",
    ROOT / "custom_components" / "came_connect" / "const.py",
)
api_module = _load_module(
    "custom_components.came_connect.api",
    ROOT / "custom_components" / "came_connect" / "api.py",
)

BptDoorConfig = api_module.BptDoorConfig
BptSipAccount = api_module.BptSipAccount
CameApiError = api_module.CameApiError
_extract_bpt_discovery = api_module._extract_bpt_discovery
_extract_bpt_device_metadata = api_module._extract_bpt_device_metadata
_extract_bpt_mobile_slots = api_module._extract_bpt_mobile_slots
_extract_bpt_sip_accounts = api_module._extract_bpt_sip_accounts
_filter_bpt_sip_accounts = api_module._filter_bpt_sip_accounts
_find_device_record = api_module._find_device_record
_build_aux_xml = api_module._build_aux_xml

from custom_components.came_connect.const import (
    CONF_BPT_SIP_HA1,
    CONF_BPT_SIP_PASSWORD,
    CONF_BPT_SIP_USER,
)

DUMMY_DEVICE_ID = 424242
DUMMY_SITE_ID = 313131
DUMMY_DEVICE_NAME = "Example Indoor Monitor"
DUMMY_UNIT_NAME = "Example Unit"
DUMMY_ENTRY_PANEL_NAME = "Example Entry Panel"
DUMMY_OPEN_DOOR_LABEL = "Example Open Door"
DUMMY_AUX_ONE_LABEL = "Demo Aux One"
DUMMY_KEYCODE = "EXAMPLEKEYCODE01"
DUMMY_SECONDARY_KEYCODE = "EXAMPLEKEYCODE99"
DUMMY_SRC_ADDR_ONE = "dummy-src-1"
DUMMY_SRC_ADDR_TWO = "dummy-src-2"
DUMMY_SRC_ADDR_OTHER = "dummy-src-9"
DUMMY_PANEL_ADDR = "dummy-panel-addr"
DUMMY_TARGET_USER = "dummy-target-user"
DUMMY_SIP_USER_ONE = "dummy_sip_user_1"
DUMMY_SIP_USER_TWO = "dummy_sip_user_2"
DUMMY_OTHER_SIP_USER = "dummy_sip_user_9"
DUMMY_DEVICE_TOKEN = "dummy-device-token-1"
DUMMY_OTHER_DEVICE_TOKEN = "dummy-device-token-2"
DUMMY_PASSWORD = "dummy-password"
DUMMY_OTHER_PASSWORD = "other-dummy-password"
DUMMY_EMAIL = "example@example.test"
DUMMY_SLOT_ONE_LABEL = "Demo Mobile Slot 1"
DUMMY_SLOT_TWO_LABEL = "Demo Mobile Slot 2"


SAMPLE_DEVICE = {
    "Id": 144565,
    "DeviceId": DUMMY_DEVICE_ID,
    "Name": DUMMY_DEVICE_NAME,
    "PlantType": "X1",
    "Keycode": DUMMY_KEYCODE,
    "Modules": [
        {
            "ModuleId": 2,
            "Name": DUMMY_UNIT_NAME,
            "AliasName": "",
            "Features": [
                {
                    "Name": DUMMY_SLOT_ONE_LABEL,
                    "AliasName": "",
                    "FeatureId": 4,
                    "Settings": [
                        {"SettingId": 2, "Value": DUMMY_SRC_ADDR_ONE},
                        {"SettingId": 1, "Value": DUMMY_SIP_USER_ONE},
                        {"SettingId": 5, "Value": "true"},
                    ],
                },
                {
                    "Name": DUMMY_SLOT_TWO_LABEL,
                    "AliasName": "",
                    "FeatureId": 4,
                    "Settings": [
                        {"SettingId": 2, "Value": DUMMY_SRC_ADDR_TWO},
                        {"SettingId": 1, "Value": DUMMY_SIP_USER_TWO},
                        {"SettingId": 5, "Value": "true"},
                    ],
                },
            ],
        },
        {
            "ModuleId": 1,
            "Name": DUMMY_ENTRY_PANEL_NAME,
            "AliasName": "",
            "Settings": [
                {"SettingId": 4, "Value": DUMMY_PANEL_ADDR},
                {"SettingId": 3, "Value": DUMMY_TARGET_USER},
            ],
            "Features": [
                {
                    "Name": DUMMY_OPEN_DOOR_LABEL,
                    "AliasName": DUMMY_OPEN_DOOR_LABEL,
                    "FeatureId": 2,
                },
                {
                    "Name": "Aux 1",
                    "AliasName": DUMMY_AUX_ONE_LABEL,
                    "FeatureId": 8,
                    "Settings": [{"SettingId": 6, "Value": "light.png"}],
                },
                {
                    "Name": "Aux 2",
                    "AliasName": "",
                    "FeatureId": 9,
                    "Settings": [{"SettingId": 6, "Value": "light.png"}],
                },
                {
                    "Name": "Aux 3",
                    "AliasName": "",
                    "FeatureId": 10,
                    "Settings": [{"SettingId": 6, "Value": "light.png"}],
                },
                {
                    "Name": "Aux 4",
                    "AliasName": "",
                    "FeatureId": 11,
                    "Settings": [{"SettingId": 6, "Value": "light.png"}],
                },
                {
                    "Name": "Aux 5",
                    "AliasName": "",
                    "FeatureId": 12,
                    "Settings": [{"SettingId": 6, "Value": "light.png"}],
                },
                {
                    "Name": "Aux 6",
                    "AliasName": "",
                    "FeatureId": 13,
                    "Settings": [{"SettingId": 6, "Value": "light.png"}],
                },
                {
                    "Name": "Aux 7",
                    "AliasName": "",
                    "FeatureId": 14,
                    "Settings": [{"SettingId": 6, "Value": "light.png"}],
                },
                {
                    "Name": "Aux 8",
                    "AliasName": "",
                    "FeatureId": 15,
                    "Settings": [{"SettingId": 6, "Value": "light.png"}],
                },
                {
                    "Name": "Aux 9",
                    "AliasName": "",
                    "FeatureId": 16,
                    "Settings": [{"SettingId": 6, "Value": "light.png"}],
                },
                {
                    "Name": "Aux 10",
                    "AliasName": "",
                    "FeatureId": 17,
                    "Settings": [{"SettingId": 6, "Value": "light.png"}],
                },
            ],
        },
    ],
}

SAMPLE_SIPACCOUNTS = [
    {
        "DeviceToken": DUMMY_DEVICE_TOKEN,
        "SipUserName": DUMMY_SIP_USER_TWO,
        "SipPassword": DUMMY_PASSWORD,
        "BptL3Addr": DUMMY_SRC_ADDR_TWO,
        "Keycode": DUMMY_KEYCODE,
        "UserEmail": DUMMY_EMAIL,
    },
    {
        "DeviceToken": DUMMY_OTHER_DEVICE_TOKEN,
        "SipUserName": DUMMY_OTHER_SIP_USER,
        "SipPassword": DUMMY_OTHER_PASSWORD,
        "BptL3Addr": DUMMY_SRC_ADDR_OTHER,
        "Keycode": DUMMY_SECONDARY_KEYCODE,
        "UserEmail": DUMMY_EMAIL,
    },
    {
        "DeviceToken": "",
        "SipUserName": "broken",
        "BptL3Addr": "dummy-src-broken",
        "Keycode": "broken",
    },
]


class BptDiscoveryTests(unittest.TestCase):
    def test_extract_discovery_uses_selected_sip_user(self) -> None:
        discovery = _extract_bpt_discovery(SAMPLE_DEVICE, preferred_sip_user=DUMMY_SIP_USER_TWO)
        self.assertEqual(discovery.keycode, DUMMY_KEYCODE)
        self.assertEqual(discovery.sip_user, DUMMY_SIP_USER_TWO)
        self.assertEqual(discovery.src_addr, DUMMY_SRC_ADDR_TWO)
        self.assertEqual(discovery.subject_label, DUMMY_SLOT_TWO_LABEL)
        self.assertEqual(discovery.target_user, DUMMY_TARGET_USER)
        self.assertEqual(discovery.panel_addr, DUMMY_PANEL_ADDR)

    def test_extract_discovery_requires_selection_when_multiple_slots_exist(self) -> None:
        with self.assertRaises(CameApiError) as ctx:
            _extract_bpt_discovery(SAMPLE_DEVICE)
        self.assertIn(CONF_BPT_SIP_USER, str(ctx.exception))

    def test_extract_bpt_device_metadata_uses_device_and_feature_labels(self) -> None:
        metadata = _extract_bpt_device_metadata(SAMPLE_DEVICE)
        self.assertEqual(metadata.device_name, DUMMY_DEVICE_NAME)
        self.assertEqual(metadata.unit_name, DUMMY_UNIT_NAME)
        self.assertEqual(metadata.entry_panel_name, DUMMY_ENTRY_PANEL_NAME)
        self.assertEqual(metadata.open_door_label, DUMMY_OPEN_DOOR_LABEL)
        self.assertEqual(len(metadata.aux_features), 10)
        self.assertEqual(metadata.aux_features[0].aux_code, 1)
        self.assertEqual(metadata.aux_features[0].label, DUMMY_AUX_ONE_LABEL)
        self.assertEqual(metadata.aux_features[0].feature_id, 8)
        self.assertEqual(metadata.aux_features[1].aux_code, 2)
        self.assertEqual(metadata.aux_features[-1].name, "Aux 10")
        self.assertEqual(metadata.aux_features[-1].aux_code, 10)
        self.assertEqual(metadata.model, "CAME BPT X1")

    def test_extract_bpt_mobile_slots_returns_enabled_slots(self) -> None:
        slots = _extract_bpt_mobile_slots(SAMPLE_DEVICE)
        self.assertEqual(len(slots), 2)
        self.assertEqual(slots[0].sip_user, DUMMY_SIP_USER_ONE)
        self.assertEqual(slots[1].subject_label, DUMMY_SLOT_TWO_LABEL)

    def test_extract_bpt_device_metadata_keeps_aux_icon_metadata(self) -> None:
        metadata = _extract_bpt_device_metadata(SAMPLE_DEVICE)
        self.assertEqual(metadata.aux_features[0].icon, "light.png")

    def test_build_aux_xml_uses_aux_command_and_index(self) -> None:
        xml = _build_aux_xml(DUMMY_SRC_ADDR_TWO, DUMMY_PANEL_ADDR, 3)
        self.assertIn("<type>AUX_COMMAND</type>", xml)
        self.assertIn("<aux_code>3</aux_code>", xml)
        self.assertIn(f"<src_addr>{DUMMY_SRC_ADDR_TWO}</src_addr>", xml)
        self.assertIn(f"<dst_addr>{DUMMY_PANEL_ADDR}</dst_addr>", xml)

    def test_find_device_record_matches_device_id(self) -> None:
        found = _find_device_record([SAMPLE_DEVICE], str(DUMMY_DEVICE_ID))
        self.assertEqual(found["Keycode"], DUMMY_KEYCODE)

    def test_config_from_mapping_uses_discovered_defaults(self) -> None:
        discovery = _extract_bpt_discovery(SAMPLE_DEVICE, preferred_sip_user=DUMMY_SIP_USER_TWO)
        discovery = api_module.BptDiscovery(
            keycode=discovery.keycode,
            sip_user=discovery.sip_user,
            src_addr=discovery.src_addr,
            subject_label=discovery.subject_label,
            target_user=discovery.target_user,
            panel_addr=discovery.panel_addr,
            device_token=DUMMY_DEVICE_TOKEN,
        )
        config = BptDoorConfig.from_mapping(
            {
                CONF_BPT_SIP_PASSWORD: DUMMY_PASSWORD,
            },
            discovery=discovery,
        )
        assert config is not None
        self.assertEqual(config.sip_domain, f"{DUMMY_KEYCODE}.xip.cameconnect.net")
        self.assertEqual(config.sip_user, DUMMY_SIP_USER_TWO)
        self.assertEqual(config.src_addr, DUMMY_SRC_ADDR_TWO)
        self.assertEqual(config.subject_label, DUMMY_SLOT_TWO_LABEL)
        self.assertEqual(config.device_token, DUMMY_DEVICE_TOKEN)

    def test_extract_sip_accounts_ignores_incomplete_rows(self) -> None:
        accounts = _extract_bpt_sip_accounts(SAMPLE_SIPACCOUNTS)
        self.assertEqual(len(accounts), 2)
        self.assertEqual(accounts[0].device_token, DUMMY_DEVICE_TOKEN)
        self.assertEqual(accounts[0].sip_user, DUMMY_SIP_USER_TWO)
        self.assertEqual(accounts[0].src_addr, DUMMY_SRC_ADDR_TWO)

    def test_filter_sip_accounts_uses_sip_user_preference(self) -> None:
        accounts = _extract_bpt_sip_accounts(SAMPLE_SIPACCOUNTS)
        matches = _filter_bpt_sip_accounts(accounts, preferred_sip_user=DUMMY_SIP_USER_TWO)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].device_token, DUMMY_DEVICE_TOKEN)

    def test_has_credentials_accepts_password_or_ha1_without_device_token(self) -> None:
        self.assertTrue(BptDoorConfig.has_credentials({CONF_BPT_SIP_PASSWORD: "p"}))
        self.assertTrue(BptDoorConfig.has_credentials({CONF_BPT_SIP_HA1: "h"}))
        self.assertFalse(BptDoorConfig.has_credentials({}))


class BptResolveConfigTests(unittest.IsolatedAsyncioTestCase):
    async def test_resolve_config_uses_sipaccounts_bootstrap(self) -> None:
        client = api_module.CameConnectClient(
            session=None,
            client_id="client",
            client_secret="secret",
            username="user",
            password="pass",
            redirect_uri="https://app.cameconnect.net/role",
        )
        client.async_get_sip_accounts = AsyncMock(
            return_value=[
                BptSipAccount(
                    device_token=DUMMY_DEVICE_TOKEN,
                    sip_user=DUMMY_SIP_USER_TWO,
                    src_addr=DUMMY_SRC_ADDR_TWO,
                    keycode=DUMMY_KEYCODE,
                    sip_password=DUMMY_PASSWORD,
                )
            ]
        )
        client.async_get_sites = AsyncMock(return_value=[{"Id": DUMMY_SITE_ID}])
        client.async_get_site_devices = AsyncMock(return_value=[SAMPLE_DEVICE])

        config = await client.async_resolve_bpt_door_config(
            str(DUMMY_DEVICE_ID),
            {
                CONF_BPT_SIP_PASSWORD: DUMMY_PASSWORD,
            },
        )

        self.assertEqual(config.device_token, DUMMY_DEVICE_TOKEN)
        self.assertEqual(config.keycode, DUMMY_KEYCODE)
        self.assertEqual(config.sip_user, DUMMY_SIP_USER_TWO)
        self.assertEqual(config.src_addr, DUMMY_SRC_ADDR_TWO)

    async def test_setup_preview_returns_dropdown_context_from_sipaccounts(self) -> None:
        client = api_module.CameConnectClient(
            session=None,
            client_id="client",
            client_secret="secret",
            username="user",
            password="pass",
            redirect_uri="https://app.cameconnect.net/role",
        )
        client.async_get_sip_accounts = AsyncMock(
            return_value=[
                BptSipAccount(
                    device_token=DUMMY_DEVICE_TOKEN,
                    sip_user=DUMMY_SIP_USER_TWO,
                    src_addr=DUMMY_SRC_ADDR_TWO,
                    keycode=DUMMY_KEYCODE,
                    sip_password=DUMMY_PASSWORD,
                )
            ]
        )
        client.async_get_sites = AsyncMock(return_value=[{"Id": DUMMY_SITE_ID}])
        client.async_get_site_devices = AsyncMock(return_value=[SAMPLE_DEVICE])

        preview = await client.async_get_bpt_setup_preview(str(DUMMY_DEVICE_ID), {})

        self.assertEqual(preview.token_source, "sipaccounts")
        self.assertEqual(len(preview.slots), 1)
        self.assertEqual(preview.selected_slot.sip_user, DUMMY_SIP_USER_TWO)
        self.assertEqual(preview.metadata.device_name, DUMMY_DEVICE_NAME)
        self.assertEqual(preview.metadata.entry_panel_name, DUMMY_ENTRY_PANEL_NAME)

    async def test_resolve_config_raises_when_sip_user_is_unknown(self) -> None:
        client = api_module.CameConnectClient(
            session=None,
            client_id="client",
            client_secret="secret",
            username="user",
            password="pass",
            redirect_uri="https://app.cameconnect.net/role",
        )
        client.async_get_sip_accounts = AsyncMock(return_value=_extract_bpt_sip_accounts(SAMPLE_SIPACCOUNTS))

        with self.assertRaises(CameApiError) as ctx:
            await client.async_resolve_bpt_door_config(
                str(DUMMY_DEVICE_ID),
                {
                    CONF_BPT_SIP_PASSWORD: DUMMY_PASSWORD,
                    CONF_BPT_SIP_USER: "dummy_sip_user_missing",
                },
            )

        self.assertIn("/sipaccounts", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
