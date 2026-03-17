from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch
import unittest

from _support import ROOT, ensure_custom_component_packages, load_module

ensure_custom_component_packages()

load_module(
    "custom_components.came_connect.const",
    ROOT / "custom_components" / "came_connect" / "const.py",
)
api_module = load_module(
    "custom_components.came_connect.api",
    ROOT / "custom_components" / "came_connect" / "api.py",
)

BptDoorConfig = api_module.BptDoorConfig

DUMMY_KEYCODE = "EXAMPLEKEYCODE01"
DUMMY_SIP_USER = "dummy_sip_user_2"
DUMMY_PASSWORD = "dummy-password"
DUMMY_SRC_ADDR = "dummy-src-2"
DUMMY_TARGET_USER = "dummy-target-user"
DUMMY_PANEL_ADDR = "dummy-panel-addr"
DUMMY_SUBJECT_LABEL = "Demo Mobile Slot 2"
DUMMY_DEVICE_TOKEN = "dummy-device-token-1"


def _make_config() -> BptDoorConfig:
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


class BptTransportTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.client = api_module.CameConnectClient(
            session=None,
            client_id="client",
            client_secret="secret",
            username="user",
            password="pass",
            redirect_uri="https://app.cameconnect.net/role",
        )

    async def test_async_open_bpt_door_keeps_xipregister_status_and_subject(self) -> None:
        config = _make_config()
        self.client._request = AsyncMock(return_value=(403, {"error": "forbidden"}))

        async def fake_to_thread(func, *args, **kwargs):
            return func(*args, **kwargs)

        with patch.object(api_module.asyncio, "to_thread", new=fake_to_thread):
            with patch.object(
                self.client,
                "_send_bpt_xml_command",
                return_value={
                    "register_status": "SIP/2.0 200 OK",
                    "message_status": "SIP/2.0 202 Accepted",
                },
            ) as send_mock:
                result = await self.client.async_open_bpt_door(config)

        send_mock.assert_called_once()
        sent_config, sent_body, sent_subject = send_mock.call_args.args
        self.assertIs(sent_config, config)
        self.assertIn("<type>OPEN_DOOR</type>", sent_body)
        self.assertEqual(
            sent_subject,
            api_module._build_subject(config.src_addr, config.panel_addr, config.subject_label),
        )
        self.assertEqual(result["xipregister_status"], 403)
        self.assertEqual(result["message_status"], "SIP/2.0 202 Accepted")

    async def test_async_open_bpt_aux_sends_aux_xml_without_subject(self) -> None:
        config = _make_config()
        self.client._request = AsyncMock(return_value=(200, {"ok": True}))

        async def fake_to_thread(func, *args, **kwargs):
            return func(*args, **kwargs)

        with patch.object(api_module.asyncio, "to_thread", new=fake_to_thread):
            with patch.object(
                self.client,
                "_send_bpt_xml_command",
                return_value={
                    "register_status": "SIP/2.0 200 OK",
                    "message_status": "SIP/2.0 202 Accepted",
                },
            ) as send_mock:
                result = await self.client.async_open_bpt_aux(config, 3)

        send_mock.assert_called_once()
        sent_config, sent_body, sent_subject = send_mock.call_args.args
        self.assertIs(sent_config, config)
        self.assertIn("<type>AUX_COMMAND</type>", sent_body)
        self.assertIn("<aux_code>3</aux_code>", sent_body)
        self.assertIsNone(sent_subject)
        self.assertEqual(result["aux_code"], 3)
        self.assertEqual(result["xipregister_status"], 200)

    def test_build_message_request_omits_subject_when_none(self) -> None:
        config = _make_config()
        request = self.client._build_message_request(
            config,
            local_ip="192.168.1.2",
            local_port=5061,
            call_id="call-id",
            tag="tag-id",
            branch="branch-id",
            cseq=1,
            subject=None,
            body="<xml/>",
        ).decode()

        self.assertIn(f"MESSAGE sip:{DUMMY_TARGET_USER}@{DUMMY_KEYCODE}.xip.cameconnect.net SIP/2.0", request)
        self.assertNotIn("Subject:", request)
        self.assertIn("Content-Type: text/xml", request)


if __name__ == "__main__":
    unittest.main()
