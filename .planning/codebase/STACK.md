# Technology Stack

**Analysis Date:** 2026-03-15

## Languages

**Primary:**
- Python 3.7+ - All custom component code, async/await throughout

**Secondary:**
- YAML - Home Assistant configuration and translations
- JSON - API payloads, manifest, config storage

## Runtime

**Environment:**
- Home Assistant (custom integration framework)
- Requires Home Assistant 2023.9 or later

**Package Manager:**
- pip (Home Assistant manages all dependencies)
- No external Python packages required (pure stdlib + HA internals)

## Frameworks

**Core:**
- Home Assistant Core (`homeassistant.core`, `homeassistant.helpers`) - Configuration management, entity coordination, async lifecycle
- Home Assistant Config Entries API - Setup flow, options management, integration lifecycle
- Home Assistant Data Update Coordinator - Push-based state synchronization with no polling

**Home Assistant Platforms:**
- `homeassistant.components.cover` - Gate control entity (open/close/stop)
- `homeassistant.components.sensor` - Phase, position, timestamp, error code sensors
- `homeassistant.components.binary_sensor` - Moving state, hub online status
- `homeassistant.components.config_entries` - UI-based configuration flow

**Testing:**
- None configured

**Build/Dev:**
- None (copy folder to Home Assistant `custom_components/`)

## Key Dependencies

**Critical:**
- `aiohttp` - HTTP client for OAuth2, REST API, and WebSocket connections (async)
- `voluptuous` - Config schema validation for setup/options flow

**Infrastructure:**
- None - uses only Home Assistant's built-in `aiohttp.ClientSession` (already in HA)

## External Libraries Used (Python stdlib only beyond aiohttp + voluptuous)

- `asyncio` - async/await, task management, locks, events
- `base64` - OAuth2 PKCE code challenge encoding, Basic auth headers
- `hashlib` - SHA256 for code challenge, MD5 for SIP Digest auth (tools only)
- `secrets` - cryptographically secure random for PKCE, nonce, state
- `string` - character sets for random string generation
- `time` - monotonic deadline tracking for token expiry
- `json` - API response/request parsing
- `contextlib` - suppress context manager (WebSocket cleanup)
- `urllib.parse` - URL encoding for OAuth params and WebSocket URL construction
- `logging` - structured logging per module

## Configuration

**Environment:**
- No `.env` file needed - credentials passed via Home Assistant config entry UI
- OAuth2 client ID/secret extracted by user from CAME Connect web app auth headers

**Build:**
- No build system
- No source maps, transpilation, or bundling
- Code copied as-is to Home Assistant

**Home Assistant Configuration Files:**
- `custom_components/came_connect/manifest.json` - Integration metadata (v1.2.0)
  - `domain`: "came_connect"
  - `requirements`: [] (empty — relies on HA's aiohttp)
  - `iot_class`: "cloud_polling" (despite being push-based; HA classification only)
  - Entry point: Config Flow UI

## Platform Requirements

**Development:**
- Python 3.7+
- Home Assistant installation (dev setup via symlink to `custom_components/`)
- Text editor/IDE with Python support
- Browser for OAuth capture (extracting client credentials)

**Production:**
- Home Assistant 2023.9+ running Python 3.7+
- Network access to `*.cameconnect.net` (OAuth, REST, WebSocket)
- Valid CAME Connect account with OAuth credentials

## API Endpoints

**CAME Connect Cloud (reverse-engineered):**
- OAuth: `https://app.cameconnect.net/oauth/auth-code`, `/oauth/token`
- REST: `https://app.cameconnect.net/api/devicestatus`, `/automations/{id}/commands/{id}`
- WebSocket: `wss://app.cameconnect.net/api/events-real-time`

**Local BPT XTS7 Intercom (tools only — not integrated):**
- HTTP API: `http://{device}/sipaccount`, `/credentialsmobile`, etc.
- SIP: `sip://{device}:5060` (Asterisk; SIP MESSAGE protocol)
- AMI: `{device}:5038` (Asterisk Manager Interface) and `:8088` (HTTP)

## Secrets & Auth Management

**OAuth2:**
- PKCE flow with SHA256 code challenge
- Client credentials (ID/Secret) stored in Home Assistant config entry data
- Access token auto-refresh 60 seconds before expiry
- Token passed as Bearer header for REST, as WebSocket subprotocol for WS

**SIP (tools only):**
- Digest authentication (MD5) for local SIP MESSAGE
- Pre-computed HA1 hash from device configuration

---

*Stack analysis: 2026-03-15*
