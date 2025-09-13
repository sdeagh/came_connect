from __future__ import annotations

import base64
import hashlib
import secrets
import string
import time
import asyncio
import aiohttp
import logging
import json
import contextlib

from urllib.parse import quote, urlencode

from typing import Any, Dict, Optional, Callable, Awaitable

from .const import API_BASE

WS_LOGGER = logging.getLogger(__name__ + ".ws")  

class CameAuthError(Exception):
    """Authentication/authorization failure (bad creds or rejected token)."""

class CameApiError(Exception):
    """Non-auth API failure (bad request/server error/etc.)."""

class CameRateLimitError(Exception):
    """429 rate limit (we'll use this later)."""

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