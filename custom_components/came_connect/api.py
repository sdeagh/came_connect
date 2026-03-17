from __future__ import annotations

import base64
import hashlib
import secrets
import string
import time
import asyncio
import socket
import ssl
import aiohttp
import logging
import json
import contextlib
import re
import uuid

from dataclasses import dataclass
from urllib.parse import urlencode

from typing import Any, Dict, Optional, Callable, Awaitable, Mapping

from .const import (
    API_BASE,
    CONF_BPT_DEVICE_TOKEN,
    CONF_BPT_KEYCODE,
    CONF_BPT_PANEL_ADDR,
    CONF_BPT_SIP_HA1,
    CONF_BPT_SIP_PASSWORD,
    CONF_BPT_SIP_USER,
    CONF_BPT_SRC_ADDR,
    CONF_BPT_SUBJECT_LABEL,
    CONF_BPT_TARGET_USER,
    DEFAULT_BPT_APP_NAME,
    DEFAULT_BPT_AUTH_PASSWORD_PREFIX,
    DEFAULT_BPT_LANG,
    DEFAULT_BPT_OS_TYPE,
    DEFAULT_BPT_PANEL_ADDR,
    DEFAULT_BPT_SIP_PROXY_HOST,
    DEFAULT_BPT_SIP_PROXY_PORT,
    DEFAULT_BPT_TARGET_USER,
)

_LOGGER = logging.getLogger(__name__)
WS_LOGGER = logging.getLogger(__name__ + ".ws")  

class CameAuthError(Exception):
    """Authentication/authorization failure (bad creds or rejected token)."""

class CameApiError(Exception):
    """Non-auth API failure (bad request/server error/etc.)."""

class CameRateLimitError(Exception):
    """429 rate limit (we'll use this later)."""


MOBILE_APP_FEATURE_ID = 4
OPEN_DOOR_FEATURE_ID = 2
ENTRY_PANEL_AUX_FEATURE_IDS = tuple(range(8, 18))
ENTRY_PANEL_MODULE_ID = 1
UNIT_MODULE_ID = 2
SETTING_SIP_USER = 1
SETTING_L3_ADDR = 2
SETTING_TARGET_USER = 3
SETTING_PANEL_ADDR = 4
SETTING_ENABLED = 5
SETTING_ICON = 6


@dataclass(frozen=True)
class BptDiscovery:
    keycode: str
    sip_user: str
    src_addr: str
    subject_label: str
    target_user: str
    panel_addr: str
    device_token: str = ""


@dataclass(frozen=True)
class BptMobileSlot:
    sip_user: str
    src_addr: str
    subject_label: str


@dataclass(frozen=True)
class BptSipAccount:
    device_token: str
    sip_user: str
    src_addr: str
    keycode: str
    sip_password: str | None = None


@dataclass(frozen=True)
class BptDoorConfig:
    keycode: str
    sip_user: str
    src_addr: str
    subject_label: str
    device_token: str
    sip_password: str | None = None
    sip_ha1: str | None = None
    target_user: str = DEFAULT_BPT_TARGET_USER
    panel_addr: str = DEFAULT_BPT_PANEL_ADDR
    app_name: str = DEFAULT_BPT_APP_NAME
    os_type: str = DEFAULT_BPT_OS_TYPE
    app_lang: str = DEFAULT_BPT_LANG
    proxy_host: str = DEFAULT_BPT_SIP_PROXY_HOST
    proxy_port: int = DEFAULT_BPT_SIP_PROXY_PORT
    auth_password_prefix: str = DEFAULT_BPT_AUTH_PASSWORD_PREFIX

    @property
    def sip_domain(self) -> str:
        return f"{self.keycode}.xip.cameconnect.net"

    @property
    def auth_password(self) -> str | None:
        if not self.sip_password:
            return None
        return f"{self.auth_password_prefix}{self.sip_password}"

    @staticmethod
    def has_credentials(data: Mapping[str, Any]) -> bool:
        sip_password = data.get(CONF_BPT_SIP_PASSWORD)
        sip_ha1 = data.get(CONF_BPT_SIP_HA1)
        return bool(sip_password or sip_ha1)

    @classmethod
    def from_mapping(
        cls,
        data: Mapping[str, Any],
        discovery: BptDiscovery | None = None,
    ) -> "BptDoorConfig | None":
        def _clean(key: str, default: str = "") -> str:
            value = data.get(key, default)
            return value.strip() if isinstance(value, str) else default

        keycode = _clean(CONF_BPT_KEYCODE) or (discovery.keycode if discovery else "")
        sip_user = _clean(CONF_BPT_SIP_USER) or (discovery.sip_user if discovery else "")
        sip_password = _clean(CONF_BPT_SIP_PASSWORD)
        sip_ha1 = _clean(CONF_BPT_SIP_HA1)
        src_addr = _clean(CONF_BPT_SRC_ADDR) or (discovery.src_addr if discovery else "")
        subject_label = _clean(CONF_BPT_SUBJECT_LABEL) or (discovery.subject_label if discovery else "")
        device_token = _clean(CONF_BPT_DEVICE_TOKEN) or (discovery.device_token if discovery else "")
        target_user = _clean(CONF_BPT_TARGET_USER) or (
            discovery.target_user if discovery and discovery.target_user else DEFAULT_BPT_TARGET_USER
        )
        panel_addr = _clean(CONF_BPT_PANEL_ADDR) or (
            discovery.panel_addr if discovery and discovery.panel_addr else DEFAULT_BPT_PANEL_ADDR
        )

        if not all([keycode, sip_user, src_addr, subject_label, device_token]):
            return None
        if not (sip_password or sip_ha1):
            return None

        return cls(
            keycode=keycode,
            sip_user=sip_user,
            sip_password=sip_password or None,
            sip_ha1=sip_ha1 or None,
            src_addr=src_addr,
            target_user=target_user,
            panel_addr=panel_addr,
            subject_label=subject_label,
            device_token=device_token,
        )


@dataclass(frozen=True)
class BptAuxFeature:
    aux_code: int
    feature_id: int
    name: str
    label: str
    icon: str | None = None


@dataclass(frozen=True)
class BptDeviceMetadata:
    device_name: str
    entry_panel_name: str
    unit_name: str
    open_door_label: str
    aux_features: tuple[BptAuxFeature, ...]
    model: str
    manufacturer: str = "CAME"


@dataclass(frozen=True)
class BptResolvedTarget:
    device_token: str
    device: Mapping[str, Any]
    discovery: BptDiscovery
    sip_account: BptSipAccount | None = None


@dataclass(frozen=True)
class BptSetupPreview:
    slots: tuple[BptMobileSlot, ...]
    selected_slot: BptMobileSlot | None
    metadata: BptDeviceMetadata
    token_source: str


def _coerce_list(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ("Data", "data", "Items", "items"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


def _settings_map(settings: Any) -> dict[int, str]:
    result: dict[int, str] = {}
    if not isinstance(settings, list):
        return result
    for item in settings:
        if not isinstance(item, dict):
            continue
        setting_id = item.get("SettingId")
        value = item.get("Value")
        if isinstance(setting_id, int) and value is not None:
            result[setting_id] = str(value)
    return result


def _display_label(item: Mapping[str, Any], fallback: str = "") -> str:
    return str(item.get("AliasName") or item.get("Name") or fallback).strip()


def _extract_aux_code(
    *,
    feature_id: int,
    name: str,
    label: str,
) -> int:
    for candidate in (name, label):
        match = re.search(r"(\d+)$", candidate.strip())
        if match:
            parsed = int(match.group(1))
            if parsed > 0:
                return parsed

    if feature_id in ENTRY_PANEL_AUX_FEATURE_IDS:
        return feature_id - ENTRY_PANEL_AUX_FEATURE_IDS[0] + 1

    raise CameApiError(f"Unable to determine AUX code for feature {feature_id} ({name or label})")


def _find_device_record(devices_payload: Any, device_id: int | str) -> dict[str, Any] | None:
    wanted = str(device_id)
    for device in _coerce_list(devices_payload):
        if str(device.get("DeviceId", "")) == wanted or str(device.get("Id", "")) == wanted:
            return device
    return None


def _extract_bpt_discovery(
    device: Mapping[str, Any],
    *,
    preferred_sip_user: str = "",
    preferred_subject_label: str = "",
    preferred_src_addr: str = "",
) -> BptDiscovery:
    keycode = str(device.get("Keycode", "")).strip()
    if not keycode:
        raise CameApiError("Missing BPT keycode in device metadata")

    panel_addr = DEFAULT_BPT_PANEL_ADDR
    target_user = DEFAULT_BPT_TARGET_USER

    modules = device.get("Modules")
    if not isinstance(modules, list):
        raise CameApiError("Missing BPT modules in device metadata")

    for module in modules:
        if not isinstance(module, dict):
            continue
        module_id = module.get("ModuleId")
        module_settings = _settings_map(module.get("Settings"))
        if module_id == ENTRY_PANEL_MODULE_ID:
            panel_addr = module_settings.get(SETTING_PANEL_ADDR, panel_addr)
            target_user = module_settings.get(SETTING_TARGET_USER, target_user)

    mobile_slots = _extract_bpt_mobile_slots(device)
    if not mobile_slots:
        raise CameApiError("No enabled BPT mobile app slots found in device metadata")

    selected = _select_bpt_mobile_slot(
        mobile_slots,
        preferred_sip_user=preferred_sip_user,
        preferred_subject_label=preferred_subject_label,
        preferred_src_addr=preferred_src_addr,
        allow_empty=False,
    )
    assert selected is not None

    return BptDiscovery(
        keycode=keycode,
        sip_user=selected.sip_user,
        src_addr=selected.src_addr,
        subject_label=selected.subject_label,
        target_user=target_user,
        panel_addr=panel_addr,
    )


def _extract_bpt_mobile_slots(device: Mapping[str, Any]) -> list[BptMobileSlot]:
    mobile_slots: list[BptMobileSlot] = []
    modules = device.get("Modules")
    if not isinstance(modules, list):
        return mobile_slots

    for module in modules:
        if not isinstance(module, dict):
            continue
        features = module.get("Features")
        if not isinstance(features, list):
            continue
        for feature in features:
            if not isinstance(feature, dict) or feature.get("FeatureId") != MOBILE_APP_FEATURE_ID:
                continue
            settings = _settings_map(feature.get("Settings"))
            sip_user = settings.get(SETTING_SIP_USER, "").strip()
            src_addr = settings.get(SETTING_L3_ADDR, "").strip()
            enabled = settings.get(SETTING_ENABLED, "true").strip().lower()
            if not sip_user or not src_addr or enabled in {"false", "0", "no"}:
                continue
            mobile_slots.append(
                BptMobileSlot(
                    sip_user=sip_user,
                    src_addr=src_addr,
                    subject_label=str(feature.get("AliasName") or feature.get("Name") or sip_user).strip(),
                )
            )
    return mobile_slots


def _select_bpt_mobile_slot(
    mobile_slots: list[BptMobileSlot],
    *,
    preferred_sip_user: str = "",
    preferred_subject_label: str = "",
    preferred_src_addr: str = "",
    allow_empty: bool = False,
) -> BptMobileSlot | None:
    selected = None
    if preferred_sip_user:
        selected = next((item for item in mobile_slots if item.sip_user == preferred_sip_user), None)
        if selected is None:
            raise CameApiError(f"BPT SIP user {preferred_sip_user} was not found in device metadata")
        return selected

    if preferred_src_addr:
        selected = next((item for item in mobile_slots if item.src_addr == preferred_src_addr), None)
        if selected is None:
            raise CameApiError(f"BPT source address {preferred_src_addr} was not found in device metadata")
        return selected

    if preferred_subject_label:
        selected = next((item for item in mobile_slots if item.subject_label == preferred_subject_label), None)
        if selected is None:
            raise CameApiError(f"BPT subject label {preferred_subject_label} was not found in device metadata")
        return selected

    if len(mobile_slots) == 1:
        return mobile_slots[0]

    if allow_empty:
        return None

    choices = ", ".join(item.sip_user for item in mobile_slots)
    raise CameApiError(
        "Multiple enabled BPT mobile app slots were discovered. "
        f"Set {CONF_BPT_SIP_USER} to choose one of: {choices}"
    )


def _extract_bpt_device_metadata(device: Mapping[str, Any]) -> BptDeviceMetadata:
    device_name = _display_label(device, "BPT/X1 Intercom")
    entry_panel_name = "Entry panel"
    unit_name = device_name
    open_door_label = "Open Door"
    aux_features: list[BptAuxFeature] = []

    modules = device.get("Modules")
    if isinstance(modules, list):
        for module in modules:
            if not isinstance(module, dict):
                continue
            module_id = module.get("ModuleId")
            if module_id == ENTRY_PANEL_MODULE_ID:
                entry_panel_name = _display_label(module, entry_panel_name)
                features = module.get("Features")
                if isinstance(features, list):
                    for feature in features:
                        if not isinstance(feature, dict):
                            continue
                        feature_id = feature.get("FeatureId")
                        if feature_id == OPEN_DOOR_FEATURE_ID:
                            open_door_label = _display_label(feature, open_door_label)
                            continue
                        if feature_id not in ENTRY_PANEL_AUX_FEATURE_IDS:
                            continue
                        settings = _settings_map(feature.get("Settings"))
                        icon = settings.get(SETTING_ICON, "").strip() or None
                        aux_name = str(feature.get("Name", "")).strip()
                        aux_label = _display_label(feature, aux_name)
                        aux_features.append(
                            BptAuxFeature(
                                aux_code=_extract_aux_code(
                                    feature_id=int(feature_id),
                                    name=aux_name,
                                    label=aux_label,
                                ),
                                feature_id=int(feature_id),
                                name=aux_name,
                                label=aux_label,
                                icon=icon,
                            )
                        )
            elif module_id == UNIT_MODULE_ID:
                unit_name = _display_label(module, unit_name)

    plant_type = str(device.get("PlantType", "")).strip()
    model = f"CAME BPT {plant_type}" if plant_type else "CAME BPT/X1"
    return BptDeviceMetadata(
        device_name=device_name,
        entry_panel_name=entry_panel_name,
        unit_name=unit_name,
        open_door_label=open_door_label,
        aux_features=tuple(aux_features),
        model=model,
    )


def _extract_bpt_sip_accounts(payload: Any) -> list[BptSipAccount]:
    accounts: list[BptSipAccount] = []
    for item in _coerce_list(payload):
        device_token = str(item.get("DeviceToken", "")).strip()
        sip_user = str(item.get("SipUserName") or item.get("UserName") or "").strip()
        src_addr = str(item.get("BptL3Addr") or item.get("L3Address") or "").strip()
        keycode = str(item.get("Keycode", "")).strip()
        sip_password = str(item.get("SipPassword", "")).strip() or None
        if not all([device_token, sip_user, src_addr, keycode]):
            continue
        accounts.append(
            BptSipAccount(
                device_token=device_token,
                sip_user=sip_user,
                src_addr=src_addr,
                keycode=keycode,
                sip_password=sip_password,
            )
        )
    return accounts


def _filter_bpt_sip_accounts(
    accounts: list[BptSipAccount],
    *,
    preferred_sip_user: str = "",
    preferred_src_addr: str = "",
) -> list[BptSipAccount]:
    if preferred_sip_user:
        matches = [account for account in accounts if account.sip_user == preferred_sip_user]
        if not matches:
            choices = ", ".join(sorted({account.sip_user for account in accounts})) or "none"
            raise CameApiError(
                f"BPT SIP user {preferred_sip_user} was not found in /sipaccounts. "
                f"Available users: {choices}"
            )
        return matches

    if preferred_src_addr:
        matches = [account for account in accounts if account.src_addr == preferred_src_addr]
        if not matches:
            choices = ", ".join(sorted({account.src_addr for account in accounts})) or "none"
            raise CameApiError(
                f"BPT source address {preferred_src_addr} was not found in /sipaccounts. "
                f"Available addresses: {choices}"
            )
        return matches

    return accounts


def _md5(value: str) -> str:
    return hashlib.md5(value.encode("utf-8")).hexdigest()


def _truncate_label(label: str) -> str:
    return label[:24]


def _build_subject(src_addr: str, dst_addr: str, label: str) -> str:
    return f"{src_addr};{dst_addr};00001;;{_truncate_label(label)}"


def _build_open_door_xml(src_addr: str, dst_addr: str) -> str:
    return (
        "<BPT_COMMAND><COMMAND><type>OPEN_DOOR</type>"
        f"<src_addr>{src_addr}</src_addr>"
        f"<dst_addr>{dst_addr}</dst_addr>"
        "</COMMAND></BPT_COMMAND>"
    )


def _build_aux_xml(src_addr: str, dst_addr: str, aux_code: int) -> str:
    return (
        "<BPT_COMMAND><COMMAND><type>AUX_COMMAND</type>"
        f"<aux_code>{aux_code}</aux_code>"
        f"<src_addr>{src_addr}</src_addr>"
        f"<dst_addr>{dst_addr}</dst_addr>"
        "</COMMAND></BPT_COMMAND>"
    )


def _digest_response(
    user: str,
    password: str | None,
    realm: str,
    nonce: str,
    method: str,
    uri: str,
    *,
    ha1_override: str | None = None,
    qop: str | None = None,
    nc: str | None = None,
    cnonce: str | None = None,
) -> str:
    if password is not None:
        ha1 = _md5(f"{user}:{realm}:{password}")
    elif ha1_override:
        ha1 = ha1_override
    else:
        raise ValueError("Missing SIP auth secret")
    ha2 = _md5(f"{method}:{uri}")
    if qop:
        return _md5(f"{ha1}:{nonce}:{nc}:{cnonce}:{qop}:{ha2}")
    return _md5(f"{ha1}:{nonce}:{ha2}")


def _parse_digest_challenge(header: str) -> dict[str, str]:
    _, _, payload = header.partition(":")
    payload = payload.strip()
    if payload.lower().startswith("digest "):
        payload = payload[7:]

    params: dict[str, str] = {}
    for key, value in re.findall(r'(\w+)=(".*?"|[^,\s]+)', payload):
        if value.startswith('"') and value.endswith('"'):
            value = value[1:-1]
        params[key.lower()] = value
    return params


def _pick_qop(qop_value: str) -> str | None:
    if not qop_value:
        return None
    options = [item.strip() for item in qop_value.split(",") if item.strip()]
    if "auth" in options:
        return "auth"
    return options[0] if options else None


def _build_digest_auth_header(
    method_auth: str,
    challenge: Mapping[str, str],
    method: str,
    uri: str,
    sip_user: str,
    password: str | None,
    *,
    ha1_override: str | None = None,
) -> str:
    realm = challenge.get("realm", "")
    nonce = challenge.get("nonce", "")
    qop = _pick_qop(challenge.get("qop", ""))
    nc = "00000001" if qop else None
    cnonce = uuid.uuid4().hex[:16] if qop else None
    response = _digest_response(
        sip_user,
        password,
        realm,
        nonce,
        method,
        uri,
        ha1_override=ha1_override,
        qop=qop,
        nc=nc,
        cnonce=cnonce,
    )

    parts = [
        f'{method_auth}: Digest username="{sip_user}"',
        f'realm="{realm}"',
        f'nonce="{nonce}"',
        f'uri="{uri}"',
        f'response="{response}"',
        "algorithm=MD5",
    ]
    if challenge.get("opaque"):
        parts.append(f'opaque="{challenge["opaque"]}"')
    if qop:
        parts.append(f"qop={qop}")
        parts.append(f"nc={nc}")
        parts.append(f'cnonce="{cnonce}"')
    return ", ".join(parts)

def _basic_header(client_id: str, client_secret: str) -> dict[str, str]:
    token = base64.b64encode(f"{client_id}:{client_secret}".encode("utf-8")).decode("utf-8")
    return {"Authorization": f"Basic {token}", "Accept": "application/json"}


def _random_string(n: int = 64) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(n))


def _generate_code_verifier(n: int = 64) -> str:
    alphabet = string.ascii_letters + string.digits + "-._~"
    return "".join(secrets.choice(alphabet) for _ in range(max(43, min(96, n))))


def _generate_code_challenge(code_verifier: str) -> str:
    digest = hashlib.sha256(code_verifier.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")


class CameConnectClient:
    def __init__(
        self,
        session: aiohttp.ClientSession,
        client_id: str,
        client_secret: str,
        username: str,
        password: str,
        redirect_uri: str,
    ) -> None:
        self._session = session
        self._client_id = client_id
        self._client_secret = client_secret
        self._username = username
        self._password = password
        self._redirect_uri = redirect_uri
        self._access_token: Optional[str] = None
        self._code_verifier: Optional[str] = None
        self._expires_at: float = 0.0  # monotonic deadline for the token
        self._lock = asyncio.Lock()

    # ---------- OAuth helpers ----------
    async def _fetch_auth_code(self) -> str:
        
        code_verifier = _generate_code_verifier(64)
        code_challenge = _generate_code_challenge(code_verifier)
        params = {
            "client_id": self._client_id,
            "response_type": "code",
            "redirect_uri": self._redirect_uri,
            "state": _random_string(16),
            "nonce": _random_string(16),
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        data = {
            "grant_type": "authorization_code",
            "client_id": self._client_id,
            "username": self._username,
            "password": self._password,
        }
        headers = _basic_header(self._client_id, self._client_secret)
        async with self._session.post(f"{API_BASE}/oauth/auth-code", params=params, data=data, headers=headers, timeout=20) as resp:
            
            js = await resp.json(content_type=None)
            # Treat common auth failures as auth errors (CAME sometimes uses 400)
            if resp.status == 401:
                raise CameAuthError("Invalid CAME Connect credentials")
            if resp.status == 400 and isinstance(js, dict) and js.get("error") in {
                "invalid_grant", "invalid_client", "unauthorized_client"
            }:
                raise CameAuthError(f"Auth code rejected: {js}")

            if resp.status != 200 or "code" not in js:
                raise CameApiError(f"auth-code failed: {resp.status} {js}")

            self._code_verifier = code_verifier
            return js["code"]

    async def _fetch_token(self, code: str) -> str:
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self._redirect_uri,
            "code_verifier": self._code_verifier,
        }
        headers = _basic_header(self._client_id, self._client_secret)

        async with self._session.post(f"{API_BASE}/oauth/token", data=data, headers=headers, timeout=20) as resp:
                        
            js = await resp.json(content_type=None)
            # Treat common auth failures as auth errors (CAME sometimes uses 400)
            if resp.status == 401:
                raise CameAuthError("Token exchange rejected (401)")
            if resp.status == 400 and isinstance(js, dict) and js.get("error") in {
                "invalid_grant", "invalid_client", "unauthorized_client"
            }:
                raise CameAuthError(f"Token exchange rejected: {js}")
            if resp.status != 200 or "access_token" not in js:
                raise CameApiError(f"token failed: {resp.status} {js}")

            self._access_token = js["access_token"]
            ttl = int(js.get("expires_in", 0)) or 0
            # refresh a minute early; keep at least 30s to avoid thrashing
            self._expires_at = time.monotonic() + max(30, ttl - 60)
            return self._access_token

    def _token_valid(self) -> bool:
        return bool(self._access_token) and time.monotonic() < self._expires_at

    async def ensure_token(self) -> str:
        if self._token_valid():
            return self._access_token  # type: ignore[return-value]
        async with self._lock:
            if not self._token_valid():
                code = await self._fetch_auth_code()
                await self._fetch_token(code)
            return self._access_token  # type: ignore[return-value]

    # ---------- request helper with 401 retry ----------
    async def _request(self, method: str, url: str, *, json: Any | None = None, params: dict | None = None) -> tuple[int, Any]:
        await self.ensure_token()
        headers = {"Authorization": f"Bearer {self._access_token}", "Accept": "application/json"}
        # try once; on 401 refresh token and retry once
        for attempt in (1, 2):
            async with self._session.request(method, url, headers=headers, json=json, params=params, timeout=20) as resp:
                try:
                    js = await resp.json(content_type=None)
                except Exception:
                    js = {"ok": resp.status}
                if resp.status == 401 and attempt == 1:
                    # token expired on the server; clear and refresh
                    self._access_token = None
                    await self.ensure_token()
                    headers["Authorization"] = f"Bearer {self._access_token}"
                    continue
                return resp.status, js
        # not reached
        return 500, {"error": "unknown"}

    # ---------- public API ----------
    async def get_device_status(self, device_id: int | str) -> Dict[str, Any]:
        status, js = await self._request("GET", f"{API_BASE}/devicestatus", params={"devices": f"[{device_id}]"})
        if status != 200:
            raise RuntimeError(f"devicestatus failed: {status} {js}")
        arr = js.get("Data") or js.get("data") or []
        if not arr:
            raise RuntimeError("No Data from devicestatus")
        return arr[0]

    async def send_command(self, device_id: int | str, command_id: int) -> Any:
        status, js = await self._request("POST", f"{API_BASE}/automations/{device_id}/commands/{command_id}", json={})
        if status not in (200, 202):
            raise RuntimeError(f"command {command_id} failed: {status} {js}")
        return js

    async def async_open_bpt_door(self, config: BptDoorConfig) -> dict[str, Any]:
        xip_result = await self._async_bpt_xipregister(config)
        result = await asyncio.to_thread(
            self._send_bpt_xml_command,
            config,
            _build_open_door_xml(config.src_addr, config.panel_addr),
            _build_subject(config.src_addr, config.panel_addr, config.subject_label),
        )
        result.update(xip_result)
        return result

    async def async_open_bpt_aux(self, config: BptDoorConfig, aux_code: int) -> dict[str, Any]:
        xip_result = await self._async_bpt_xipregister(config)
        result = await asyncio.to_thread(
            self._send_bpt_xml_command,
            config,
            _build_aux_xml(config.src_addr, config.panel_addr, aux_code),
            None,
        )
        result["aux_code"] = aux_code
        result.update(xip_result)
        return result

    async def _async_bpt_xipregister(self, config: BptDoorConfig) -> dict[str, Any]:
        xip_status, xip_body = await self._request(
            "GET",
            f"{API_BASE}/push/xipregister",
            params={
                "sipUri": config.sip_user,
                "sipDomain": config.sip_domain,
                "voipDeviceToken": config.device_token,
                "pushDeviceToken": config.device_token,
                "remoteSrv": 1,
                "appName": config.app_name,
                "osType": config.os_type,
                "lang": config.app_lang,
            },
        )
        if xip_status != 200:
            _LOGGER.warning(
                "xipregister returned %s for sip user %s; continuing with SIP flow",
                xip_status,
                config.sip_user,
            )
        return {
            "xipregister": xip_body,
            "xipregister_status": xip_status,
        }

    async def async_resolve_bpt_door_config(
        self,
        device_id: int | str,
        options: Mapping[str, Any],
    ) -> BptDoorConfig:
        config = BptDoorConfig.from_mapping(options)
        if config is not None:
            return config

        if not BptDoorConfig.has_credentials(options):
            raise CameApiError(
                f"Missing BPT credentials. Set either {CONF_BPT_SIP_PASSWORD} "
                f"or {CONF_BPT_SIP_HA1}."
            )

        device_token = str(options.get(CONF_BPT_DEVICE_TOKEN, "")).strip()
        preferred_sip_user = str(options.get(CONF_BPT_SIP_USER, "")).strip()
        preferred_subject_label = str(options.get(CONF_BPT_SUBJECT_LABEL, "")).strip()
        preferred_src_addr = str(options.get(CONF_BPT_SRC_ADDR, "")).strip()

        resolved = await self.async_resolve_bpt_target(
            device_id,
            options,
            preferred_sip_user=preferred_sip_user,
            preferred_subject_label=preferred_subject_label,
            preferred_src_addr=preferred_src_addr,
        )
        config = BptDoorConfig.from_mapping(options, discovery=resolved.discovery)
        if config is None:
            raise CameApiError("Incomplete BPT configuration after autodiscovery")
        return config

    async def async_get_bpt_device_metadata(
        self,
        device_id: int | str,
        options: Mapping[str, Any],
    ) -> BptDeviceMetadata:
        preferred_sip_user = str(options.get(CONF_BPT_SIP_USER, "")).strip()
        preferred_subject_label = str(options.get(CONF_BPT_SUBJECT_LABEL, "")).strip()
        preferred_src_addr = str(options.get(CONF_BPT_SRC_ADDR, "")).strip()
        resolved = await self.async_resolve_bpt_target(
            device_id,
            options,
            preferred_sip_user=preferred_sip_user,
            preferred_subject_label=preferred_subject_label,
            preferred_src_addr=preferred_src_addr,
        )
        return _extract_bpt_device_metadata(resolved.device)

    async def async_get_bpt_setup_preview(
        self,
        device_id: int | str,
        options: Mapping[str, Any],
    ) -> BptSetupPreview:
        preferred_sip_user = str(options.get(CONF_BPT_SIP_USER, "")).strip()
        preferred_subject_label = str(options.get(CONF_BPT_SUBJECT_LABEL, "")).strip()
        preferred_src_addr = str(options.get(CONF_BPT_SRC_ADDR, "")).strip()
        manual_device_token = str(options.get(CONF_BPT_DEVICE_TOKEN, "")).strip()

        token_candidates: list[tuple[str, BptSipAccount | None]] = []
        if manual_device_token:
            token_candidates.append((manual_device_token, None))

        sip_accounts: list[BptSipAccount] = []
        last_error: Exception | None = None
        try:
            sip_accounts = await self.async_get_sip_accounts()
        except CameApiError as err:
            if not manual_device_token:
                raise
            last_error = err

        token_candidates.extend((account.device_token, account) for account in sip_accounts)

        seen_tokens: set[str] = set()
        for candidate_token, sip_account in token_candidates:
            if not candidate_token or candidate_token in seen_tokens:
                continue
            seen_tokens.add(candidate_token)

            try:
                sites = await self.async_get_sites(candidate_token)
                for site in sites:
                    site_id = site.get("Id") or site.get("SiteId")
                    if site_id is None:
                        continue
                    devices = await self.async_get_site_devices(site_id, candidate_token)
                    device = _find_device_record(devices, device_id)
                    if device is None:
                        continue

                    metadata = _extract_bpt_device_metadata(device)
                    metadata_slots = _extract_bpt_mobile_slots(device)
                    accounts_for_token = [account for account in sip_accounts if account.device_token == candidate_token]

                    if manual_device_token and candidate_token == manual_device_token and sip_account is None:
                        valid_slots = metadata_slots
                        token_source = "manual_override"
                    else:
                        valid_slots = []
                        for account in accounts_for_token:
                            matched = next(
                                (
                                    slot
                                    for slot in metadata_slots
                                    if slot.sip_user == account.sip_user or slot.src_addr == account.src_addr
                                ),
                                None,
                            )
                            valid_slots.append(
                                matched
                                or BptMobileSlot(
                                    sip_user=account.sip_user,
                                    src_addr=account.src_addr,
                                    subject_label=account.sip_user,
                                )
                            )
                        token_source = "sipaccounts"

                    selected_slot = _select_bpt_mobile_slot(
                        valid_slots,
                        preferred_sip_user=preferred_sip_user,
                        preferred_subject_label=preferred_subject_label,
                        preferred_src_addr=preferred_src_addr,
                        allow_empty=True,
                    )

                    return BptSetupPreview(
                        slots=tuple(valid_slots),
                        selected_slot=selected_slot,
                        metadata=metadata,
                        token_source=token_source,
                    )
            except CameApiError as err:
                last_error = err

        if last_error:
            raise last_error
        raise CameApiError(f"BPT device {device_id} was not found during setup preview discovery")

    async def async_resolve_bpt_target(
        self,
        device_id: int | str,
        options: Mapping[str, Any],
        *,
        preferred_sip_user: str = "",
        preferred_subject_label: str = "",
        preferred_src_addr: str = "",
    ) -> BptResolvedTarget:
        device_token = str(options.get(CONF_BPT_DEVICE_TOKEN, "")).strip()

        token_candidates: list[tuple[str, BptSipAccount | None]] = []
        if device_token:
            token_candidates.append((device_token, None))

        sip_accounts: list[BptSipAccount] = []
        last_error: Exception | None = None
        try:
            sip_accounts = _filter_bpt_sip_accounts(
                await self.async_get_sip_accounts(),
                preferred_sip_user=preferred_sip_user,
                preferred_src_addr=preferred_src_addr,
            )
        except CameApiError as err:
            if not device_token:
                raise
            last_error = err

        token_candidates.extend((account.device_token, account) for account in sip_accounts)

        seen_candidates: set[tuple[str, str, str]] = set()
        for candidate_token, sip_account in token_candidates:
            candidate_sip_user = preferred_sip_user or (sip_account.sip_user if sip_account else "")
            candidate_src_addr = preferred_src_addr or (sip_account.src_addr if sip_account else "")
            candidate_key = (candidate_token, candidate_sip_user, candidate_src_addr)
            if not candidate_token or candidate_key in seen_candidates:
                continue
            seen_candidates.add(candidate_key)

            try:
                sites = await self.async_get_sites(candidate_token)
                for site in sites:
                    site_id = site.get("Id") or site.get("SiteId")
                    if site_id is None:
                        continue
                    devices = await self.async_get_site_devices(site_id, candidate_token)
                    device = _find_device_record(devices, device_id)
                    if device is None:
                        continue

                    if sip_account and sip_account.keycode and not device.get("Keycode"):
                        device = dict(device)
                        device["Keycode"] = sip_account.keycode

                    discovery = _extract_bpt_discovery(
                        device,
                        preferred_sip_user=candidate_sip_user,
                        preferred_subject_label=preferred_subject_label,
                        preferred_src_addr=candidate_src_addr,
                    )
                    discovery = BptDiscovery(
                        keycode=discovery.keycode,
                        sip_user=discovery.sip_user,
                        src_addr=discovery.src_addr,
                        subject_label=discovery.subject_label,
                        target_user=discovery.target_user,
                        panel_addr=discovery.panel_addr,
                        device_token=candidate_token,
                    )
                    return BptResolvedTarget(
                        device_token=candidate_token,
                        device=device,
                        discovery=discovery,
                        sip_account=sip_account,
                    )
            except CameApiError as err:
                last_error = err

        if last_error:
            raise last_error
        raise CameApiError(f"BPT device {device_id} was not found during autodiscovery")

    async def async_get_sip_accounts(self) -> list[BptSipAccount]:
        status, js = await self._request("GET", f"{API_BASE}/sipaccounts")
        if status != 200:
            raise CameApiError(f"sipaccounts discovery failed: {status} {js}")
        accounts = _extract_bpt_sip_accounts(js)
        if not accounts:
            raise CameApiError("No BPT SIP accounts returned during autodiscovery")
        return accounts

    async def async_get_sites(self, device_token: str) -> list[dict[str, Any]]:
        status, js = await self._request(
            "GET",
            f"{API_BASE}/evo/v1/sites",
            params={"dt": device_token},
        )
        if status != 200:
            raise CameApiError(f"site discovery failed: {status} {js}")
        sites = _coerce_list(js)
        if not sites:
            raise CameApiError("No sites returned during BPT autodiscovery")
        return sites

    async def async_get_site_devices(self, site_id: int | str, device_token: str) -> list[dict[str, Any]]:
        status, js = await self._request(
            "GET",
            f"{API_BASE}/evo/v1/sites/{site_id}/devices",
            params={"dt": device_token},
        )
        if status != 200:
            raise CameApiError(f"device discovery failed for site {site_id}: {status} {js}")
        return _coerce_list(js)

    def _send_bpt_xml_command(
        self,
        config: BptDoorConfig,
        body: str,
        subject: str | None,
    ) -> dict[str, Any]:
        auth_password = config.auth_password
        ha1_override = config.sip_ha1
        sock = self._tls_connect(config)
        try:
            local_ip, local_port = sock.getsockname()[:2]
            register_call_id = f"{uuid.uuid4().hex}@{local_ip}"
            register_tag = uuid.uuid4().hex[:8]

            first_register = self._build_register_request(
                config,
                local_ip=local_ip,
                local_port=local_port,
                call_id=register_call_id,
                tag=register_tag,
                branch=f"z9hG4bK{uuid.uuid4().hex[:8]}",
                cseq=1,
            )
            sock.sendall(first_register)
            register_response = self._recv_sip_response(sock)
            register_status = self._response_status_line(register_response)

            if "200" not in register_status:
                register_response = self._retry_authenticated_request(
                    sock=sock,
                    response=register_response,
                    method="REGISTER",
                    uri=f"sip:{config.sip_domain}",
                    sip_user=config.sip_user,
                    auth_password=auth_password,
                    ha1_override=ha1_override,
                    request_builder=lambda auth_header, cseq: self._build_register_request(
                        config,
                        local_ip=local_ip,
                        local_port=local_port,
                        call_id=register_call_id,
                        tag=register_tag,
                        branch=f"z9hG4bK{uuid.uuid4().hex[:8]}",
                        cseq=cseq,
                        auth_header=auth_header,
                    ),
                )
                register_status = self._response_status_line(register_response)

            if "200" not in register_status:
                raise CameAuthError(f"SIP REGISTER failed: {register_status}")

            message_call_id = f"{uuid.uuid4().hex}@{local_ip}"
            message_tag = uuid.uuid4().hex[:8]
            first_message = self._build_message_request(
                config,
                local_ip=local_ip,
                local_port=local_port,
                call_id=message_call_id,
                tag=message_tag,
                branch=f"z9hG4bK{uuid.uuid4().hex[:8]}",
                cseq=1,
                subject=subject,
                body=body,
            )
            sock.sendall(first_message)
            message_response = self._recv_sip_response(sock)
            message_status = self._response_status_line(message_response)

            if "200" not in message_status and "202" not in message_status:
                message_response = self._retry_authenticated_request(
                    sock=sock,
                    response=message_response,
                    method="MESSAGE",
                    uri=f"sip:{config.target_user}@{config.sip_domain}",
                    sip_user=config.sip_user,
                    auth_password=auth_password,
                    ha1_override=ha1_override,
                    request_builder=lambda auth_header, cseq: self._build_message_request(
                        config,
                        local_ip=local_ip,
                        local_port=local_port,
                        call_id=message_call_id,
                        tag=message_tag,
                        branch=f"z9hG4bK{uuid.uuid4().hex[:8]}",
                        cseq=cseq,
                        subject=subject,
                        body=body,
                        auth_header=auth_header,
                    ),
                )
                message_status = self._response_status_line(message_response)

            if "200" not in message_status and "202" not in message_status:
                raise CameApiError(f"SIP MESSAGE failed: {message_status}")

            return {
                "register_status": register_status,
                "message_status": message_status,
                "subject": subject,
                "body": body,
            }
        finally:
            sock.close()

    @staticmethod
    def _tls_connect(config: BptDoorConfig) -> ssl.SSLSocket:
        def _build_context(legacy_compat: bool = False) -> ssl.SSLContext:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            if legacy_compat:
                with contextlib.suppress(ssl.SSLError, ValueError):
                    ctx.set_ciphers("DEFAULT:@SECLEVEL=1")
                if hasattr(ssl, "TLSVersion"):
                    with contextlib.suppress(ValueError):
                        ctx.minimum_version = ssl.TLSVersion.TLSv1
            return ctx

        raw = socket.create_connection((config.proxy_host, config.proxy_port), timeout=10)
        try:
            return _build_context().wrap_socket(raw, server_hostname=config.proxy_host)
        except ssl.SSLError as err:
            raw.close()
            _LOGGER.warning(
                "Default SIP TLS handshake failed for %s:%s (%s); retrying with legacy-compatible TLS settings",
                config.proxy_host,
                config.proxy_port,
                err,
            )
            raw = socket.create_connection((config.proxy_host, config.proxy_port), timeout=10)
            return _build_context(legacy_compat=True).wrap_socket(raw, server_hostname=config.proxy_host)

    @staticmethod
    def _recv_sip_response(sock: ssl.SSLSocket) -> str:
        data = b""
        sock.settimeout(5)
        try:
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                data += chunk
                decoded = data.decode(errors="replace")
                if "\r\n\r\n" not in decoded:
                    continue
                match = re.search(r"Content-Length:\s*(\d+)", decoded, re.I)
                content_len = int(match.group(1)) if match else 0
                header_end = decoded.index("\r\n\r\n") + 4
                if len(decoded) - header_end >= content_len:
                    break
        except socket.timeout:
            pass
        return data.decode(errors="replace")

    @staticmethod
    def _response_status_line(response: str) -> str:
        return response.split("\r\n", 1)[0] if response else "No response"

    def _retry_authenticated_request(
        self,
        *,
        sock: ssl.SSLSocket,
        response: str,
        method: str,
        uri: str,
        sip_user: str,
        auth_password: str | None,
        ha1_override: str | None,
        request_builder: Callable[[str, int], bytes],
    ) -> str:
        status_line = self._response_status_line(response)
        if "401" not in status_line and "407" not in status_line:
            return response

        challenge_header = ""
        for line in response.split("\r\n"):
            if line.lower().startswith("www-authenticate:") or line.lower().startswith("proxy-authenticate:"):
                challenge_header = line
                break
        if not challenge_header:
            return response

        challenge = _parse_digest_challenge(challenge_header)
        method_auth = "Authorization" if "401" in status_line else "Proxy-Authorization"
        auth_header = _build_digest_auth_header(
            method_auth,
            challenge,
            method,
            uri,
            sip_user,
            auth_password,
            ha1_override=ha1_override,
        )
        sock.sendall(request_builder(auth_header, 2))
        return self._recv_sip_response(sock)

    @staticmethod
    def _build_register_request(
        config: BptDoorConfig,
        *,
        local_ip: str,
        local_port: int,
        call_id: str,
        tag: str,
        branch: str,
        cseq: int,
        auth_header: str = "",
    ) -> bytes:
        contact = f"sip:{config.sip_user}@{local_ip}:{local_port};transport=tls"
        lines = [
            f"REGISTER sip:{config.sip_domain} SIP/2.0",
            f"Via: SIP/2.0/TLS {local_ip}:{local_port};branch={branch};rport",
            "Max-Forwards: 70",
            f"To: <sip:{config.sip_user}@{config.sip_domain}>",
            f"From: <sip:{config.sip_user}@{config.sip_domain}>;tag={tag}",
            f"Call-ID: {call_id}",
            f"CSeq: {cseq} REGISTER",
            f"Contact: <{contact}>",
            "User-Agent: came-connect-ha/1.3.0",
            "Expires: 300",
            "Content-Length: 0",
        ]
        if auth_header:
            lines.insert(-1, auth_header)
        return ("\r\n".join(lines) + "\r\n\r\n").encode()

    @staticmethod
    def _build_message_request(
        config: BptDoorConfig,
        *,
        local_ip: str,
        local_port: int,
        call_id: str,
        tag: str,
        branch: str,
        cseq: int,
        subject: str | None,
        body: str,
        auth_header: str = "",
    ) -> bytes:
        body_bytes = body.encode()
        to_uri = f"sip:{config.target_user}@{config.sip_domain}"
        lines = [
            f"MESSAGE {to_uri} SIP/2.0",
            f"Via: SIP/2.0/TLS {local_ip}:{local_port};branch={branch};rport",
            "Max-Forwards: 70",
            f"To: <{to_uri}>",
            f"From: <sip:{config.sip_user}@{config.sip_domain}>;tag={tag}",
            f"Call-ID: {call_id}",
            f"CSeq: {cseq} MESSAGE",
            "Content-Type: text/xml",
            "User-Agent: came-connect-ha/1.3.0",
            f"Content-Length: {len(body_bytes)}",
        ]
        if subject:
            lines.insert(-2, f"Subject: {subject}")
        if auth_header:
            lines.insert(-1, auth_header)
        lines.append("")
        lines.append(body)
        return ("\r\n".join(lines) + "\r\n").encode()



class CameWebsocketClient:
    """
    Minimal WS client:
      - Connects with Authorization: Bearer <token>
      - Parses TEXT frames and calls `on_event(code, value)`
      - Reconnects only when the server closes/errors
      - No ping/pong or stale watchdog (by design for now)
    """

    def __init__(
        self,
        session: aiohttp.ClientSession,
        ws_url: str,
        token_getter: Callable[[], Awaitable[str]],
        on_event: Callable[[int, Optional[int]], Awaitable[None]],
    ):
        self._session = session
        self._ws_url = ws_url
        self._token_getter = token_getter
        self._on_event = on_event
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()

    async def start(self) -> None:
        if self._task:
            return
        self._stop.clear()
        self._task = asyncio.create_task(self._run(), name="came_ws_run")

    async def stop(self) -> None:
        self._stop.set()
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None

    async def _run(self) -> None:
        backoff = 1
        while not self._stop.is_set():
            try:
                token = await self._token_getter()  # this should be the raw JWT (no "Bearer " prefix)

                # Build WS URL like the browser (note the language param)
                url = self._ws_url
                q = {"language": "en-US"}
                sep = "&" if "?" in url else "?"
                url = f"{url}{sep}{urlencode(q)}"

                # Web apps send the JWT as a subprotocol
                # aiohttp exposes this via the `protocols` argument
                protocols = [token]

                # Many servers also check Origin
                headers = {"Origin": "https://www.cameconnect.net"}

                async with self._session.ws_connect(
                    url,
                    protocols=protocols,
                    headers=headers,
                    timeout=20,
                ) as ws:
                    WS_LOGGER.info("WS connected")
                    backoff = 1

                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            WS_LOGGER.debug("WS TEXT: %s", msg.data)
                            try:
                                code, value = self._parse_frame(msg.data)
                                if code is not None:
                                    await self._on_event(code, value)
                            except Exception:
                                WS_LOGGER.warning("WS frame parse failed", exc_info=True)
                        elif msg.type in (
                            aiohttp.WSMsgType.CLOSE,
                            aiohttp.WSMsgType.CLOSED,
                            aiohttp.WSMsgType.ERROR,
                        ):
                            WS_LOGGER.warning("WS closed: %s", msg.type)
                            break

            except aiohttp.ClientResponseError as e:
                WS_LOGGER.warning("WS HTTP error %s: %s", e.status, e)
            except asyncio.CancelledError:
                WS_LOGGER.debug("WS task cancelled")
                break
            except Exception:
                WS_LOGGER.exception("WS connect/run error")

            # simple backoff before reconnect
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=backoff)
            except asyncio.TimeoutError:
                pass
            backoff = min(backoff * 2, 30)

    # --- frame parsing ---

    def _parse_frame(self, text: str) -> tuple[int | None, int | None]:
        """
        For EventId=21 (VarcoStatusUpdate), return (phase, percent).
        Everything else → (None, None).
        """
        try:
            outer = json.loads(text)
            data = outer.get("Data") or {}
            event_id = data.get("EventId")

            inner_raw = data.get("Data")  # JSON-as-string
            inner = json.loads(inner_raw) if isinstance(inner_raw, str) else (inner_raw or {})
            payload = inner.get("Payload")

            if event_id == 21 and isinstance(payload, list) and len(payload) >= 2:
                phase = int(payload[0])
                percent = int(payload[1])
                return phase, percent

            # ignore 5/6/23 etc. here; REST fallback will handle if needed
            return None, None
        except Exception:
            WS_LOGGER.exception("WS frame parse failed")
            return None, None
