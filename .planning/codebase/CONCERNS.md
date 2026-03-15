# Codebase Concerns

**Analysis Date:** 2026-03-15

## Tech Debt

**No automated testing infrastructure:**
- Issue: Zero test coverage. No pytest/unittest config. No CI pipeline. Changes to core logic (OAuth2, WebSocket, command handling) carry risk of breakage.
- Files: `custom_components/came_connect/api.py`, `custom_components/came_connect/__init__.py`, `custom_components/came_connect/cover.py`
- Impact: Regression bugs may go undetected. Manual Home Assistant restart required for each test iteration.
- Fix approach: Add pytest with fixtures for mocking aiohttp, add GitHub Actions CI to run tests on PR, add basic integration tests for OAuth flow and WS message parsing.

**Hardcoded API endpoints and magic constants:**
- Issue: OAuth base URL, WebSocket URL, and command IDs (open=2, close=5, stop=129) are hardcoded in `const.py` and scattered through code. CAME API is reverse-engineered and may change without notice.
- Files: `custom_components/came_connect/const.py`, `custom_components/came_connect/api.py`, `custom_components/came_connect/cover.py`
- Impact: API endpoint or command ID changes will require code updates. No graceful fallback or versioning strategy.
- Fix approach: Document API discovery method; add logging for version/endpoint mismatches; consider feature detection from capabilities endpoint if available.

**Bare except clauses and generic error handling:**
- Issue: Multiple locations use bare `except Exception` or `except:` without specific error types, making debugging difficult and potentially hiding programming errors.
- Files: `custom_components/came_connect/api.py` (lines 159, 261, 309), `custom_components/came_connect/hub.py` (lines 48, 74, 83), `custom_components/came_connect/sensor.py` (lines 59, 68, 125)
- Impact: Silent failures when unexpected conditions occur. Hard to distinguish between API errors, data corruption, and code bugs.
- Fix approach: Replace with specific exception types (ValueError, TypeError, KeyError). Log full traceback for debug.

**No input validation on API responses:**
- Issue: Response JSON is accessed with `.get()` and type-cast to `int()` but never validated for correctness. Malformed data from CAME API could cause silent data loss or incorrect state.
- Files: `custom_components/came_connect/hub.py` (lines 45-47, 62-75), `custom_components/came_connect/cover.py` (lines 58-73), `custom_components/came_connect/sensor.py` (lines 54-69)
- Impact: Corrupted device state snapshot without error notification. Entities may report None/unknown state incorrectly.
- Fix approach: Add strict schema validation (e.g., pydantic or simple dict validation). Log warnings when data doesn't match expected shape.

## Known Bugs

**BPT XTS7 door open blocked (202 Accepted, no action):**
- Symptoms: SIP MESSAGE to entry panel returns 202 Accepted via cloud proxy, but door doesn't actually open.
- Files: `tools/sip_cloud_opendoor.py`, `tools/sip_open_door.py`, `tools/try_ami.py`, `tools/probe_cloud_api.py`, `tools/probe_local_api.py`
- Trigger: POST to cloud API endpoint `/api/evo/v1/sites/{site_id}/devices/{device_id}/opendoor` or SIP MESSAGE with OPEN_DOOR_IND JSON body.
- Current status: Multiple approaches tried (cloud SIP proxy, local SIP, Asterisk AMI). All return 202/success but door mechanism doesn't respond. Root cause unknown.
- Workaround: None. Feature is blocked. Integration is currently incomplete for intercom devices.

**WebSocket reconnection doesn't signal failure to Home Assistant:**
- Symptoms: WS connection drops and reconnects, but if reconnection fails consistently, Home Assistant entities remain at last known state indefinitely. No error feedback to user.
- Files: `custom_components/came_connect/api.py` (lines 226-284)
- Trigger: Long network outage, server-side WS close, DNS resolution failure during reconnect loop.
- Current mitigation: Exponential backoff (1s→30s) prevents thrashing. WS logger shows disconnects at debug level.
- Recommendations: Expose connectivity status via a sensor or diagnostic. Add timeout after 10 failed reconnects to surface error in Home Assistant UI.

**Phase/position state race condition on rapid status updates:**
- Symptoms: If REST `/devicestatus` completes and pushes data to coordinator after WS event 21 completes but before entity reads it, direction detection may be incorrect.
- Files: `custom_components/came_connect/cover.py` (lines 81-112)
- Trigger: Gate moving while WS and REST both fire rapidly (unlikely but possible under network jitter).
- Current mitigation: Phase codes (PHASE_OPENING, PHASE_CLOSING) are trusted over position delta, reducing impact.
- Recommendations: Add timestamp to state snapshot; use most recent update; log when state changes unexpectedly within same cycle.

## Security Considerations

**Plain HTTP fallback for local network (XTS7 probing):**
- Risk: `tools/probe_local_api.py` uses unencrypted HTTP to local device. Session ID passed in JSON request body, not secure headers. If network is compromised, attacker can access device admin panel.
- Files: `tools/probe_local_api.py` (lines 9-27)
- Current mitigation: Tool is development-only, not shipped with integration. Assumes trusted local network.
- Recommendations: Use HTTPS or require admin to secure local network. Document security assumptions in README.

**Credentials embedded in reverse-engineering tools:**
- Risk: Cloud API credentials (CLIENT_ID, CLIENT_SECRET, USERNAME, PASSWORD, DEVICE_TOKEN) are hardcoded in multiple tools.
- Files: `tools/sip_cloud_opendoor.py` (lines 18-24), `tools/probe_cloud_api.py` (lines 20-24), `tools/try_ami.py` (lines 30-33)
- Current mitigation: Tools live in `/tools` directory, not published to public registry. Still checked into git history.
- Recommendations: Remove all real credentials from tools. Use environment variables or .env file. Add `.env` to .gitignore. Regenerate any credentials found in git history.

**OAuth2 client secret hardcoded for reverse-engineering:**
- Risk: CLIENT_ID and CLIENT_SECRET are present in probe tools, allowing anyone with this repo to authenticate as the development account.
- Files: `tools/sip_cloud_opendoor.py` (line 20), `tools/probe_cloud_api.py` (line 21)
- Current mitigation: Development credentials; likely rotated already.
- Recommendations: Use separate test/dev credentials. Document that production credentials should never be checked in. Use GitHub Secrets for CI/CD.

**No HTTPS certificate validation in some tools:**
- Risk: `tools/sip_cloud_opendoor.py` (line 152), `tools/try_ami.py` (line 11) disable SSL verification, allowing MITM attacks.
- Files: `tools/sip_cloud_opendoor.py` (line 150-154), `tools/try_ami.py` (line 10)
- Current mitigation: Tools are for development/exploration only. Not used in production integration.
- Recommendations: Enable certificate validation by default. Allow override only with explicit flag for debugging.

## Performance Bottlenecks

**No exponential backoff or jitter on initial WS connection:**
- Problem: First WS connection attempt uses 1s backoff immediately. If server is slow to respond to TLS handshake, concurrent retries may overwhelm network.
- Files: `custom_components/came_connect/api.py` (lines 227-284)
- Cause: Backoff starts at 1s and doubles only after each failed attempt. First retry is immediate.
- Improvement path: Add 100-200ms jitter, increase initial backoff to 2-3s, cap max backoff at 60s instead of 30s for very long outages.

**Hub state snapshot is not indexed:**
- Problem: `CameEventHub` stores full `/devicestatus` response in memory. Entity classes repeatedly call `_raw()` and parse the same `States[2].Data` on every coordinator update.
- Files: `custom_components/came_connect/hub.py`, `custom_components/came_connect/cover.py`, `custom_components/came_connect/sensor.py`, `custom_components/came_connect/binary_sensor.py`
- Cause: No caching of extracted values. Each entity independently extracts phase/position from raw data structure.
- Improvement path: Cache phase/position/direction in `CameEventHub` as derived properties. Entities read from cache instead of parsing raw JSON each time.

**Coordinator update always serializes full response:**
- Problem: `coordinator.async_set_updated_data()` is called for every WS event 21, even if no data changed (e.g., repeated phase code with same percent).
- Files: `custom_components/came_connect/__init__.py` (line 93)
- Cause: Hub check is done, but coordinator update happens unconditionally.
- Improvement path: Only call `async_set_updated_data()` if `hub.apply_event()` detects actual change. Reduce Home Assistant state_changed event spam.

## Fragile Areas

**Cover direction detection logic is complex:**
- Files: `custom_components/came_connect/cover.py` (lines 81-112)
- Why fragile: Multi-factor decision tree (phase codes → position delta → velocity inference). Easy to get wrong when CAME changes phase semantics or position update frequency. Tests missing.
- Safe modification: Add unit tests covering all phase/position combinations. Document decision tree with examples. Add diagnostics attributes showing why direction was chosen.
- Test coverage: Zero. No test cases for direction logic.

**Hub state shape assumptions are implicit:**
- Files: `custom_components/came_connect/hub.py`, all entity platform files
- Why fragile: All code assumes `/devicestatus` response has structure `States[2].Data = [phase, position]`. If CAME adds/removes fields or reorders structure, code silently falls back to defaults.
- Safe modification: Add schema validation at seed time. Reject invalid shapes. Log full response on mismatch.
- Test coverage: No schema validation tests. Manual testing only.

**WebSocket frame parsing silently ignores unknown EventIds:**
- Files: `custom_components/came_connect/api.py` (lines 288-310)
- Why fragile: Only EventId=21 is processed. EventIds 5, 6, 23, etc. return `(None, None)` and are ignored. If API adds new event types carrying important state, they're silently dropped.
- Safe modification: Log when unknown EventIds arrive (at debug level). Add feature flag/config option to expose new event types.
- Test coverage: No tests for EventId routing.

**OAuth2 token refresh uses hardcoded 60-second early refresh:**
- Files: `custom_components/came_connect/api.py` (line 135)
- Why fragile: Token expiry is assumed to be in `expires_in` field, with 60s safety margin. If CAME changes token format or expiry semantics, refresh may fail.
- Safe modification: Validate token format. Add configurable refresh margin in options. Log token expiry time at setup.
- Test coverage: No OAuth flow tests.

## Scaling Limits

**Single device only:**
- Current capacity: One CAME controller per Home Assistant instance (or rather, one config entry per controller, but architecture assumes single device context).
- Limit: Multi-device setups would require multi-entry coordinator management and entity ID deduplication.
- Scaling path: Refactor `__init__.py` to accept device list. Create coordinator per device. Scope all entity IDs to device_id. Test with 2-3 devices in parallel.

**In-memory state snapshot with no cleanup:**
- Current capacity: One `/devicestatus` response stored in `CameEventHub`. No memory bounds.
- Limit: If `/devicestatus` response grows (more state slots, more metadata), memory usage grows unbounded.
- Scaling path: Implement response size check. Log warning if response > 1MB. Implement snapshot history retention limit (e.g., keep last 100 snapshots for diagnostics).

## Dependencies at Risk

**No external dependencies, but aiohttp implicit:**
- Risk: Home Assistant's aiohttp is used directly. No version pinning. If HA drops aiohttp support, integration breaks.
- Impact: Unlikely short-term, but integration is deeply coupled to HA's HTTP stack.
- Migration plan: If aiohttp drops, refactor to use httpx or urllib3. Abstract HTTP client behind interface.

**CAME API is reverse-engineered and may change:**
- Risk: Endpoints, command IDs, response formats are not documented by CAME and could change without notice.
- Impact: OAuth base URL change breaks login. Command ID change breaks gate control. Response format change breaks state parsing.
- Migration plan: Document all discovered endpoints/commands in comments. Add feature detection (ask device for capabilities). Subscribe to CAME updates or API changelogs if available.

## Missing Critical Features

**No set-position support:**
- Problem: Cover entity doesn't support `async_set_cover_position()`. Users can't move gate to intermediate position (e.g., 50%).
- Blocks: Partial gate opening for access control. Energy-efficient gate positioning.
- Files: `custom_components/came_connect/cover.py` (lines 176-178)
- Reason: Unknown CAME cloud command ID for incremental movement. Would require reverse-engineering.

**No multi-device support:**
- Problem: Integration designed for single device. Adding second controller requires manual config entry duplication or hacking.
- Blocks: Multi-site setups. Coordinating multiple gates.
- Files: `custom_components/came_connect/__init__.py`, `custom_components/came_connect/hub.py`
- Reason: Architecture assumes single `device_id`. Refactor needed.

**BPT XTS7 intercom not integrated:**
- Problem: Door open command is blocked (202 Accepted, no action). Cannot complete intercom feature.
- Blocks: Smart door unlock via Home Assistant.
- Files: `tools/sip_cloud_opendoor.py`, `tools/sip_open_door.py` (research scripts only)
- Reason: Unknown SIP/Asterisk configuration or API endpoint. Multiple approaches tried; none work.

## Test Coverage Gaps

**No unit tests for OAuth2 flow:**
- What's not tested: Token refresh, PKCE code generation, 401 retry logic, auth error detection.
- Files: `custom_components/came_connect/api.py` (lines 51-148)
- Risk: Regression in login would go undetected until user reports it.
- Priority: High

**No unit tests for WebSocket parsing:**
- What's not tested: EventId=21 frame parsing, unknown EventId handling, malformed JSON resilience, nested JSON-as-string parsing.
- Files: `custom_components/came_connect/api.py` (lines 288-310)
- Risk: API format change silently drops state updates.
- Priority: High

**No integration tests for cover entity state machine:**
- What's not tested: Phase transitions (OPEN → OPENING → CLOSED), position delta direction inference, stop command interruption.
- Files: `custom_components/came_connect/cover.py` (lines 81-147)
- Risk: Direction detection incorrect when phases/positions don't sync.
- Priority: High

**No tests for sensor data extraction:**
- What's not tested: Null/missing field handling, type conversion errors, datetime parsing, state attribute generation.
- Files: `custom_components/came_connect/sensor.py`
- Risk: Entities report unknown state on edge cases.
- Priority: Medium

**No tests for hub state management:**
- What's not tested: Seed from REST, apply WS event, snapshot shape validation, LastSeen timestamp updates.
- Files: `custom_components/came_connect/hub.py`
- Risk: Inconsistent snapshots distributed to entities.
- Priority: Medium

---

*Concerns audit: 2026-03-15*
