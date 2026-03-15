# Testing Patterns

**Analysis Date:** 2026-03-15

## Test Framework

**Runner:**
- No formal test framework (pytest, unittest, vitest, etc.)

**Run Commands:**
```bash
# No automated test suite — testing is manual integration only
# To test the integration, copy/symlink to Home Assistant custom_components/ and restart HA
```

## Testing Approach

**Manual Integration Testing:**

1. Copy or symlink `custom_components/came_connect/` into a Home Assistant `custom_components/` directory
2. Restart Home Assistant
3. Add the integration via **Settings → Devices & Services → + Add Integration → CAME Connect**
4. Monitor entities and behavior in Home Assistant UI

**Debug Logging:**

```yaml
logger:
  default: warning
  logs:
    custom_components.came_connect: debug
    custom_components.came_connect.api.ws: debug
    custom_components.came_connect.coordinator: debug
```

## No Unit Tests

**Rationale:**
- Pure Python, async-only code with heavy Home Assistant framework coupling
- API client uses real aiohttp sessions; reverse-engineered against CAME cloud endpoints
- WebSocket parsing depends on actual CAME event frame format
- OAuth2 PKCE flow requires credential verification against real servers
- State management (hub) is simple snapshot logic

**Test Gaps:**
- No OAuth2 token refresh race condition coverage (uses `asyncio.Lock` but untested)
- No WebSocket reconnection backoff testing (exponential 1s→30s untested)
- No frame parsing error tolerance coverage
- No coordinator push-update flow coverage

## Manual Test Scenarios

**On Initial Setup:**
- Credentials accepted (OAuth2 succeeds)
- Device status fetches via REST (initial seed from `/devicestatus`)
- Entities created: cover, sensors, binary sensors
- Phase and position render correctly from initial data

**WebSocket Connection:**
- WS connects with JWT subprotocol
- EventId=21 frames parse correctly (phase + percent extracted)
- Phase/position update in real-time (no polling)
- Incorrect EventId frames are silently ignored
- Malformed frames logged as warning, not fatal

**Commands:**
- `cover.open_cover` sends command ID 2
- `cover.close_cover` sends command ID 5
- `cover.stop_cover` sends command ID 129
- Response codes 200/202 indicate success

**Reconnection Resilience:**
- WS closes → reconnects with backoff (manually: restart HA or check logs)
- 401 token error → refresh and retry once

**Options Flow:**
- Redirect URI change reloads integration without re-entry
- WebSocket URL change reloads integration and reconnects

## Error Handling

**Logging Patterns:**
- `_LOGGER.debug(...)` — routine operations
- `_LOGGER.warning(...)` — recoverable errors (WS closed, frame parse failed)
- `_LOGGER.exception(...)` — unexpected errors with full traceback

**Exception Hierarchy (defined in `api.py`):**
- `CameAuthError` — OAuth2 or token validation failure (401, 400 with `invalid_grant`)
- `CameApiError` — non-auth API failure
- `CameRateLimitError` — 429 rate limit (defined but not yet used)

**UpdateFailed Propagation:**
OAuth or REST failures propagate as `UpdateFailed` to coordinator. Entities handle missing data gracefully with safe defaults.

## Test Coverage Gaps

**Auth/Token:**
- No test for concurrent token refresh (lock prevents race but untested)
- No test for token expiry at deadline

**WebSocket:**
- No test for frame parsing against malformed payloads
- No test for reconnection backoff sequence (1→2→4→8→16→30→30→...)

**Hub State Management:**
- No test for payload with missing `States[2]`
- No test for invalid phase codes

**Config/Options:**
- No test for options migration on first setup
- No test for WebSocket URL change triggering reconnect

**Entities:**
- No test for direction inference from phase + position delta
- No test for entity state class attributes

---

*Testing analysis: 2026-03-15*
