# Architecture

**Analysis Date:** 2026-03-15

## Pattern Overview

**Overall:** Push-based coordinator with hybrid REST/WebSocket state management.

**Key Characteristics:**
- Initial state seeded from REST API (`/devicestatus` endpoint)
- Real-time state updates pushed via WebSocket (EventId=21 VarcoStatusUpdate frames)
- No periodic polling; all state updates come from external events
- Single device per integration instance (multi-device support planned)
- Home Assistant `DataUpdateCoordinator` used for entity synchronization, not polling
- Async/await throughout; pure Python with no external dependencies beyond HA framework

## Layers

**Authentication Layer:**
- Purpose: Handle OAuth2 PKCE flow and token lifecycle management
- Location: `custom_components/came_connect/api.py` (`CameConnectClient`)
- Contains: OAuth code exchange, JWT token refresh, rate-limit-aware token validation
- Depends on: aiohttp for HTTP requests
- Used by: `CameWebsocketClient` (for token retrieval), REST API calls in `__init__.py`

**API Integration Layer:**
- Purpose: Communicate with CAME Connect cloud services over REST and WebSocket
- Location: `custom_components/came_connect/api.py` (`CameConnectClient`, `CameWebsocketClient`)
- Contains: HTTP request/response handling, WebSocket frame parsing, automatic token refresh on 401
- Depends on: Authentication layer for token management
- Used by: Hub, Coordinator, Entities

**State Management Layer:**
- Purpose: Maintain in-memory snapshot of device state and apply incremental updates
- Location: `custom_components/came_connect/hub.py` (`CameEventHub`)
- Contains: Snapshot initialization from REST payload, phase/position state tracking, event application logic
- Depends on: Phase constants from `const.py`
- Used by: Coordinator push callback in `__init__.py`

**Coordinator Layer:**
- Purpose: Synchronize state changes across all entities, trigger updates without polling
- Location: `custom_components/came_connect/__init__.py` (DataUpdateCoordinator instantiation)
- Contains: Initial seed fetch, WS event callback registration, push-based update triggering
- Depends on: API layer, State management layer
- Used by: All entity platforms (cover, sensor, binary_sensor)

**Entity Layers:**
- Purpose: Expose gate state and controls to Home Assistant
- Locations:
  - `custom_components/came_connect/cover.py` (gate entity with open/close/stop commands)
  - `custom_components/came_connect/sensor.py` (phase, position %, last-seen, error sensors)
  - `custom_components/came_connect/binary_sensor.py` (moving state, hub connectivity)
- Depends on: Coordinator for state updates
- Used by: Home Assistant entity registry

**Configuration Layer:**
- Purpose: Handle user input and options flow for integration setup
- Location: `custom_components/came_connect/config_flow.py`
- Contains: Initial OAuth credentials collection, redirect URI and WebSocket URL options
- Used by: Home Assistant config entry system

## Data Flow

**Initialization Sequence:**

1. `async_setup_entry` in `__init__.py` is invoked by HA when integration is added
2. OAuth credentials and device ID are extracted from `entry.data`
3. `CameConnectClient` instance is created with OAuth credentials
4. `DataUpdateCoordinator` is created with `_async_update_data` method (one-shot REST call)
5. Coordinator performs initial seed via `async_config_entry_first_refresh()`:
   - `CameConnectClient.ensure_token()` acquires OAuth2 JWT
   - `CameConnectClient.get_device_status(device_id)` fetches `/devicestatus` REST endpoint
   - State snapshot stored in `coordinator.data`
6. `CameEventHub` is seeded from REST payload (`hub.seed_from_devicestatus()`)
7. `CameWebsocketClient` is instantiated with token getter and event callback
8. WS client connects and begins listening for frames
9. Entry data (client, coordinator, hub, ws_client) is stored in `hass.data[DOMAIN][entry_id]`
10. Platform setup is forwarded to cover, sensor, binary_sensor platforms
11. Each platform creates its entities with references to the shared coordinator

**Real-Time Update Flow:**

1. CAME cloud pushes WebSocket frame (EventId=21: VarcoStatusUpdate with `[phase, percent]`)
2. `CameWebsocketClient._run()` receives TEXT frame, calls `_parse_frame()`
3. `_parse_frame()` extracts EventId, validates it's 21, extracts `[phase, percent]` from payload
4. If valid, `_on_ws_event(code, value)` callback is invoked (code=phase, value=percent)
5. Callback calls `hub.apply_event(code, value)`:
   - Validates phase against `_VALID_PHASES`
   - Updates internal `_phase` and `_pos` tracking
   - Returns updated snapshot (or None if ignored)
6. If snapshot changed, `coordinator.async_set_updated_data(new_snapshot)` is called
7. Coordinator notifies all listening entities via `_handle_coordinator_update()`
8. Entities recalculate properties from snapshot and trigger HA state update

**State Management:**

- Master state lives in `hub._snapshot` (dict matching `/devicestatus` shape)
- Structure: `{"States": [{}, {}, {"Data": [phase, percent]}], "LastSeen": "...", "Online": bool, ...}`
- Hub tracks explicit `_phase` and `_pos` for fast lookups
- All entities extract state from `coordinator.data["States"][2]["Data"]`
- Phase codes: PHASE_OPEN=16, PHASE_CLOSED=17, PHASE_OPENING=32, PHASE_CLOSING=33, PHASE_STOPPED=19
- Position: 0–100 percentage (0=closed, 100=open)

## Key Abstractions

**CameConnectClient:**
- Purpose: OAuth2 token management and REST API calls
- Examples: `custom_components/came_connect/api.py` lines 51–186
- Pattern: Async lock prevents concurrent token refresh; token validity checked before each request; 401 triggers one-shot refresh and retry

**CameWebsocketClient:**
- Purpose: WebSocket connection lifecycle and frame parsing
- Examples: `custom_components/came_connect/api.py` lines 189–311
- Pattern: Reconnection loop with exponential backoff (1s→30s); token passed as subprotocol; frame parsing extracts EventId and payload; event callback invoked for valid frames

**CameEventHub:**
- Purpose: In-memory device state snapshot and event application
- Examples: `custom_components/came_connect/hub.py` lines 15–87
- Pattern: Snapshot shape validation ensures States[2].Data exists; apply_event returns None for ignored events, new snapshot for state changes

**CoordinatorEntity Subclasses:**
- Purpose: Bind entity properties to coordinator data
- Examples: `cover.py` (CameGateCover), `sensor.py` (_BaseSensor), `binary_sensor.py` (_BaseBS)
- Pattern: Override `_handle_coordinator_update()` to extract state; properties query `self._raw()` (coordinator.data State[2].Data); DeviceInfo shared across all entities with same device_id

## Entry Points

**async_setup_entry:**
- Location: `custom_components/came_connect/__init__.py` lines 27–117
- Triggers: Home Assistant invokes when integration added/reloaded
- Responsibilities:
  - Migrate options (redirect_uri, websocket_url)
  - Instantiate client, coordinator, hub, ws_client
  - Perform initial REST seed
  - Register WS event callback
  - Store shared objects
  - Forward platform setup
  - Register options change listener

**async_unload_entry:**
- Location: `custom_components/came_connect/__init__.py` lines 124–139
- Triggers: Home Assistant invokes when integration removed
- Responsibilities: Unload platforms, stop WS client, clean up hass.data

**async_step_user (ConfigFlow):**
- Location: `custom_components/came_connect/config_flow.py` lines 32–44
- Triggers: User initiates integration add
- Responsibilities: Collect OAuth credentials and device ID

**async_step_init (OptionsFlow):**
- Location: `custom_components/came_connect/config_flow.py` lines 54–81
- Triggers: User opens integration options
- Responsibilities: Allow override of redirect_uri and websocket_url

**Platform async_setup_entry (cover/sensor/binary_sensor):**
- Location: Platform files lines 180–186 (cover), 154–165 (sensor), 80–89 (binary_sensor)
- Triggers: `async_forward_entry_setups` from `__init__.py`
- Responsibilities: Extract shared objects from hass.data, instantiate entities, register with HA

## Error Handling

**Strategy:** Exceptions propagate upward; connection failures trigger reconnect; auth failures raise `CameAuthError` (distinguishes from `CameApiError`).

**Patterns:**

- **OAuth Token Refresh:** `CameConnectClient.ensure_token()` uses async lock to prevent race conditions; 401 response during request triggers token refresh and single retry
- **WebSocket Reconnection:** `CameWebsocketClient._run()` catches all exceptions, sleeps with exponential backoff, then retries connection. Backoff resets on successful connection.
- **Frame Parsing Errors:** `_parse_frame()` wrapped in try/except; logs warning and returns `(None, None)` to skip event
- **Coordinator Updates:** `_async_update_data()` catches all exceptions, wraps in `UpdateFailed` for HA logging
- **Entity Data Extraction:** Defensive null checks and try/except blocks in `_raw()`, `_pos()`, `_phase()` methods to handle malformed snapshots

## Cross-Cutting Concerns

**Logging:**
- Module-level loggers: `_LOGGER` (main), `COORD_LOGGER` (coordinator), `WS_LOGGER` (WebSocket)
- Debug level logs: token refresh, WS frames, ignored events
- Warning level logs: WS reconnection, frame parse errors
- Exception logging: connection failures with stack trace

**Validation:**
- Phase codes checked against `_VALID_PHASES` before applying event
- Position clamped to 0–100 range
- Snapshot shape validated and reconstructed if malformed (`_ensure_shape()`)
- HTTP status codes and JSON structure validated before use

**Authentication:**
- OAuth2 PKCE flow with S256 code challenge
- Token stored in memory (not persisted)
- Token validity checked before each API call; 401 triggers refresh
- JWT passed as WebSocket subprotocol per CAME API design

---

*Architecture analysis: 2026-03-15*
