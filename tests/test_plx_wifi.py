"""PLX WiFi regression checks with dummy metadata and no network calls."""
from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, Mock, patch

from _support import ROOT, ensure_custom_component_packages, load_module

ensure_custom_component_packages()
c = load_module("custom_components.came_connect.const", ROOT / "custom_components/came_connect/const.py")
a = load_module("custom_components.came_connect.api", ROOT / "custom_components/came_connect/api.py")

OPTIONS = {
    c.CONF_BPT_KEYCODE: "example-keycode",
    c.CONF_BPT_SIP_USER: "example-sip-user",
    c.CONF_BPT_SIP_PASSWORD: "example-sip-password",
    c.CONF_BPT_SRC_ADDR: "example-source",
    c.CONF_BPT_SUBJECT_LABEL: "Example mobile slot",
}
PLANT = {
    "DeviceId": "example-device",
    "Name": "Example PLX WiFi",
    "PlantType": "X1",
    "Modules": [
        {"ModuleId": 1, "Features": [
            {"FeatureId": 2, "Name": "Open door"},
            {"FeatureId": 9, "Name": "Aux 2", "AliasName": "Example gate"},
        ]},
        {"ModuleId": 2, "Features": [
            {"FeatureId": 4, "Name": "Example mobile slot", "Settings": [
                {"SettingId": 1, "Value": "example-sip-user"},
                {"SettingId": 2, "Value": "example-source"},
                {"SettingId": 5, "Value": "true"},
            ]},
        ]},
    ],
}


def client(session=None):
    return a.CameConnectClient(session, "example-client", "example-secret", "example-user", "example-password", "https://app.cameconnect.net/role")


def response(status, payload):
    context = AsyncMock()
    context.__aenter__.return_value.status = status
    context.__aenter__.return_value.json = AsyncMock(return_value=payload)
    return context


class PlxWifiTests(unittest.IsolatedAsyncioTestCase):
    async def test_manual_sip_without_token_skips_push_but_sends_aux2(self):
        api = client()
        config = a.BptDoorConfig.from_mapping(OPTIONS)
        self.assertIsNotNone(config)
        self.assertEqual(config.device_token, "")
        api._request = AsyncMock()
        with patch.object(api, "_send_bpt_xml_command", return_value={"message_status": "SIP/2.0 202 Accepted"}) as send:
            result = await api.async_open_bpt_aux(config, 2)
        api._request.assert_not_called()
        self.assertEqual(result["xipregister_status"], "skipped_no_device_token")
        self.assertIn("<aux_code>2</aux_code>", send.call_args.args[1])
        self.assertIsNone(send.call_args.args[2])

    async def test_web_plants_metadata_and_preview_avoid_sipaccounts(self):
        api = client()
        api._request = AsyncMock(side_effect=[
            (200, [{"Id": "example-site"}]), (200, [PLANT]),
            (200, [{"Id": "example-site"}]), (200, [PLANT]),
        ])
        api.async_get_sip_accounts = AsyncMock(side_effect=AssertionError("Must not use sipaccounts"))
        metadata = await api.async_get_bpt_device_metadata("example-device", OPTIONS)
        preview = await api.async_get_bpt_setup_preview("example-device", OPTIONS)
        self.assertEqual(metadata.aux_features[0].aux_code, 2)
        self.assertEqual(metadata.aux_features[0].label, "Example gate")
        self.assertEqual(preview.selected_slot.sip_user, "example-sip-user")
        self.assertEqual(preview.token_source, "direct_sip")
        self.assertTrue(api._request.call_args_list[0].args[1].endswith("/evo/v1/sites/admin"))
        self.assertTrue(api._request.call_args_list[1].args[1].endswith("/example-site/plants"))
        api.async_get_sip_accounts.assert_not_called()

    async def test_incomplete_manual_config_still_uses_existing_discovery(self):
        api = client()
        api.async_resolve_bpt_target = AsyncMock(side_effect=a.CameApiError("existing discovery"))
        with self.assertRaisesRegex(a.CameApiError, "existing discovery"):
            await api.async_get_bpt_device_metadata("example-device", {c.CONF_BPT_SIP_PASSWORD: "example-password"})
        api.async_resolve_bpt_target.assert_awaited_once()

    async def test_web_discovery_does_not_use_another_device(self):
        api = client()
        api._request = AsyncMock(side_effect=[(200, [{"Id": "example-site"}]), (200, [PLANT])])
        with self.assertRaisesRegex(a.CameApiError, "not found"):
            await api.async_get_bpt_device_metadata("different-device", OPTIONS)

    async def test_legacy_oauth_is_unchanged_when_successful(self):
        session = Mock()
        session.post.side_effect = [response(200, {"code": "example-code"}), response(200, {"access_token": "example-token", "expires_in": 3600})]
        api = client(session)
        code = await api._fetch_auth_code()
        await api._fetch_token(code)
        self.assertTrue(session.post.call_args_list[0].args[0].endswith("/oauth/auth-code"))
        self.assertTrue(session.post.call_args_list[1].args[0].endswith("/oauth/token"))

    async def test_mfa_fallback_exchanges_code_on_same_path_with_matching_pkce(self):
        session = Mock()
        session.post.side_effect = [
            response(400, {"error": "invalid_grant", "error_description": "invalid_request"}),
            response(200, {"code": "example-code"}),
            response(200, {"access_token": "example-token", "expires_in": 3600}),
        ]
        api = client(session)
        code = await api._fetch_auth_code()
        await api._fetch_token(code)
        auth, token = session.post.call_args_list[1:]
        self.assertTrue(auth.args[0].endswith("/oauth/mfa/auth-code"))
        self.assertTrue(token.args[0].endswith("/oauth/mfa/token"))
        self.assertEqual(auth.kwargs["params"]["code_challenge"], a._generate_code_challenge(token.kwargs["data"]["code_verifier"]))

    async def test_mfa_rejection_does_not_loop(self):
        session = Mock()
        rejection = {"error": "invalid_grant", "error_description": "invalid_request"}
        session.post.side_effect = [response(400, rejection), response(400, rejection)]
        with self.assertRaises(a.CameAuthError):
            await client(session)._fetch_auth_code()
        self.assertEqual(session.post.call_count, 2)

    async def test_invalid_client_does_not_try_mfa(self):
        session = Mock()
        session.post.return_value = response(400, {"error": "invalid_client"})
        with self.assertRaises(a.CameAuthError):
            await client(session)._fetch_auth_code()
        self.assertEqual(session.post.call_count, 1)


if __name__ == "__main__":
    unittest.main()
