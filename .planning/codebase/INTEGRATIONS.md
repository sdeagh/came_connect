# External Integrations

**Analysis Date:** 2026-03-15

## APIs & External Services

**CAME Connect Cloud API:**
- OAuth2 PKCE endpoint: `https://app.cameconnect.net/oauth/auth-code`, `/oauth/token`
  - SDK/Client: `aiohttp.ClientSession` (custom implementation in `api.py`)
  - Auth: OAuth2 PKCE with client ID/secret extracted from web app

- REST API endpoints: `https://app.cameconnect.net/api/`
  - SDK/Client: `aiohttp` POST/GET
  - `GET /devicestatus?devices=[id]` - Initial device state (phase, position, online status, error codes)
  - `POST /automations/{device_id}/commands/{command_id}` - Gate control (open=2, close=5, stop=129)
  - Auth: Bearer token (JWT) from OAuth2

- WebSocket: `wss://app.cameconnect.net/api/events-real-time`
  - SDK/Client: `aiohttp.ClientSession.ws_connect()`
  - Auth: JWT passed as WebSocket subprotocol
  - Flow: Subscribe to device events → receive `EventId=21` frames with `[phase, position]` updates
  - Reconnect: Exponential backoff (1s→30s) on server close or error
  - Frame format: JSON nested structure with `Data.EventId` and `Data.Data` (JSON-as-string containing `Payload`)

## Data Storage

**Databases:**
- None - stateless push-based coordinator

**File Storage:**
- None - integration uses only in-memory state

**Caching:**
- Home Assistant Data Update Coordinator (`DataUpdateCoordinator`)
  - In-memory snapshot of device state
  - Seeded once from REST `/devicestatus` on startup
  - Updated on every WebSocket event (EventId=21)
  - No persistent cache between restarts

**State Management:**
- `CameEventHub` (`hub.py`) - in-memory snapshot of `/devicestatus` response
  - Tracks: phase (16/17/32/33/19), position (0-100%), last seen timestamp, online status, error codes
  - Updated by WebSocket frames; returned to coordinator for entity updates

## Authentication & Identity

**Auth Provider:**
- CAME Connect Cloud (OAuth2 PKCE)
  - Implementation: `CameConnectClient` in `api.py`
  - Flow:
    1. POST `/oauth/auth-code` with PKCE challenge (SHA256 code_challenge)
    2. POST `/oauth/token` with auth code + code_verifier → receive JWT access_token
    3. Token auto-refresh when expired (60 seconds early, minimum 30s TTL)
    4. Lock-protected refresh to prevent concurrent token races
  - Credentials stored in HA config entry data: client_id, client_secret, username, password
  - Error handling: 401→token refresh, 400 with error_in {invalid_grant, invalid_client}→CameAuthError

**SIP (BPT XTS7 tools only — not integrated into main component):**
- Local: SIP Digest Auth (MD5) over UDP:5060 to Asterisk
- Cloud: SIP over TLS to cloud SIP proxy (104.239.174.100:5061) via `/push/xipregister` endpoint

## Monitoring & Observability

**Error Tracking:**
- None (integration logs directly to Home Assistant logger)

**Logs:**
- Home Assistant structured logging
  - Module logger: `logging.getLogger(__name__)` per file
  - WebSocket logger: `logging.getLogger(__name__ + ".ws")`
  - Coordinator logger: `logging.getLogger(f"{__name__}.coordinator")`
  - Debug log names (enable in HA): `custom_components.came_connect`, `custom_components.came_connect.api.ws`, `custom_components.came_connect.coordinator`
  - Log levels used: debug (frames, reconnects), info (WS connected), warning (WS closed, frame parse), exception (connection errors)

## CI/CD & Deployment

**Hosting:**
- CAME Connect Cloud (`app.cameconnect.net`, SIP proxy `104.239.174.100:5061`)
- User's Home Assistant instance (any platform)

**CI Pipeline:**
- None configured
- Manual distribution via GitHub/HACS

## Environment Configuration

**Required env vars:**
- None (all credentials via Home Assistant config entry UI)

**Secrets location:**
- Home Assistant's config entry data storage (encrypted at rest by HA)
- Secrets: `client_id`, `client_secret`, `username`, `password`

**Config flow options (modifiable after setup):**
- `redirect_uri` - OAuth redirect target (default: `https://app.cameconnect.net/role`)
- `websocket_url` - WebSocket endpoint (default: `wss://app.cameconnect.net/api/events-real-time`)

## Webhooks & Callbacks

**Incoming:**
- WebSocket push from CAME Connect: EventId=21 (VarcoStatusUpdate) with phase + position
  - Handler: `CameWebsocketClient._on_event` callback → coordinator update → entity state propagation

**Outgoing:**
- None (read-only except for control commands via REST)

## Device Integration Points

**CAME Connect Devices:**
- Single gate/door controller via CAME Connect cloud API
- Device identified by: `device_id` (numeric, e.g., "764729...")
- State endpoints: `/devicestatus` returns full snapshot including `States[]` array with phase/position/error
- Command endpoints: `/automations/{device_id}/commands/{cmd_id}` for open/close/stop

**BPT XTS7 WiFi Intercom (planned future, tools present):**
- Device: CAME BPT XTS7 v6.0, connected to X1 BPT system
- Cloud integration: Via CameConnect (`2B8EED6C49FCD387.xip.cameconnect.net`)
- Local intercom HTTP API: `http://192.168.1.88` (no door-open endpoint; cloud-only)
- Local Asterisk SIP: `192.168.1.88:5060` (accessible, but XIP message format proprietary/undocumented)
- Tools available:
  - `tools/sip_open_door.py` - Local SIP MESSAGE with Digest auth
  - `tools/sip_cloud_opendoor.py` - Cloud SIP proxy via CameConnect
  - `tools/try_ami.py` - Asterisk AMI (ports 5038, 8088) for manager actions
  - `tools/probe_local_api.py` - Local HTTP API endpoint discovery

## Third-Party Reverse Engineering

**API Surface:**
- All CAME Connect endpoints reverse-engineered from web app network traffic
- OAuth client credentials (ID/Secret) extracted by user from browser dev tools
- WebSocket frame format inferred from captured traffic
- SIP message structure proprietary (XIP protocol)

**Stability Risk:**
- CAME can change endpoints, response formats, or OAuth credentials without notice
- Integration has mitigation: configurable redirect_uri and websocket_url in options

---

*Integration audit: 2026-03-15*
