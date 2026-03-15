# Coding Conventions

**Analysis Date:** 2026-03-15

## Naming Patterns

**Files:**
- Lowercase with underscores for module names: `api.py`, `hub.py`, `cover.py`, `config_flow.py`
- Private modules prefixed with underscore in class context only
- Home Assistant platform files: `{platform}.py` (e.g., `cover.py`, `sensor.py`, `binary_sensor.py`)

**Functions:**
- camelCase with `async_` prefix for async functions: `async_setup_entry`, `async_open_cover`, `async_get_device_status`
- Private functions prefixed with underscore: `_basic_header()`, `_random_string()`, `_fetch_auth_code()`
- Internal helper methods: `_ensure_shape()`, `_raw()`, `_parse_frame()`

**Variables:**
- snake_case for local variables and parameters: `client_id`, `code_verifier`, `device_id`, `ws_url`
- UPPER_CASE for constants: `API_BASE`, `DOMAIN`, `DEFAULT_REDIRECT_URI`, `PHASE_OPEN`, `PHASE_CLOSED`
- Private class attributes with leading underscore: `self._session`, `self._access_token`, `self._lock`
- Class properties with underscore prefix: `self._device_id`, `self._phase`, `self._last_pos`

**Types:**
- Type hints used consistently via `from __future__ import annotations`
- Union types with `|` syntax (Python 3.10+): `int | str`, `int | None`, `str | None`
- Dictionary type hints: `Dict[str, Any]` and `dict[str, str]` (both styles present)
- Optional types: `Optional[int]`, `Optional[str]` imported from typing

**Home Assistant Entity Attributes:**
- Private attributes with `_attr_` prefix: `_attr_name`, `_attr_unique_id`, `_attr_device_info`, `_attr_device_class`
- Property names matching Home Assistant conventions: `is_closed`, `is_opening`, `is_closing`, `current_cover_position`

## Code Style

**Formatting:**
- No explicit formatter configured (no `.prettierrc`, `pyproject.toml`, or `.flake8` in repo)
- Implicit style: 4-space indentation, PEP 8 alignment
- Import blocks separated: future imports → stdlib → third-party → local
- Line length: appears to follow ~120-character guideline (some lines reach this)

**Linting:**
- No linting config present in repo
- Code appears clean to PEP 8 standards without configured enforcement
- Type hints present throughout but not strictly enforced

## Import Organization

**Order:**
1. `from __future__ import annotations` (always first)
2. Standard library imports: `logging`, `json`, `asyncio`, `base64`, `hashlib`, `secrets`, `string`, `time`
3. Third-party imports: `aiohttp`, `voluptuous`, `homeassistant.*`
4. Local imports: relative imports with dot notation (`.api`, `.const`, `.hub`)

**Path Aliases:**
- No path aliases configured; relative imports used for same-package modules
- Example: `from .const import DOMAIN, PLATFORMS`

**Module-level Loggers:**
- Loggers created at module level: `_LOGGER = logging.getLogger(__name__)`
- Specialized loggers for subsystems: `WS_LOGGER = logging.getLogger(__name__ + ".ws")`
- Coordinator logger: `COORD_LOGGER = logging.getLogger(f"{__name__}.coordinator")`

## Error Handling

**Patterns:**
- Broad `except Exception:` used for defensive parsing to avoid crashes on malformed data
- Custom exception classes for expected error conditions:
  - `CameAuthError` — Authentication/authorization failures (bad credentials, rejected token)
  - `CameApiError` — Non-auth API failures (bad request, server error)
  - `CameRateLimitError` — Rate limit errors (429 response)
- HTTP status code checks before raising exceptions (e.g., `if resp.status != 200`)
- Home Assistant integration pattern: `raise UpdateFailed(str(e)) from e`

**WebSocket error handling:**
- Graceful degradation: frame parse failures log warning but don't crash
- WS reconnection on error with exponential backoff (1s → 30s max)
- Exception handling wrapped with `contextlib.suppress()` for cancellation cleanup
- `exc_info=True` parameter used for logging stack traces on unusual errors

**Data validation:**
- Defensive extraction with defaults: `js.get("access_token") or 0`
- Type checks before casting: `if isinstance(payload, list) and len(payload) >= 2`
- Safe integer conversion in try-except blocks:
  ```python
  try:
      return int(raw[1])
  except Exception:
      return None
  ```

## Logging

**Framework:** Python's standard `logging` module

**Patterns:**
- `_LOGGER.debug()` for detailed diagnostics (e.g., state changes, frame parsing)
- `_LOGGER.warning()` for recoverable issues (WS connection failures, parse errors)
- `_LOGGER.exception()` for caught exceptions (with full traceback)
- `_LOGGER.info()` rarely used; reserved for lifecycle events (WS connected)

**Examples from codebase:**
- `_LOGGER.debug("Hub seed: bad payload, falling back to defaults", exc_info=True)` — diagnostic with traceback
- `WS_LOGGER.warning("WS closed: %s", msg.type)` — subsystem-specific logger
- `WS_LOGGER.exception("WS connect/run error")` — automatic exc_info=True
- `COORD_LOGGER` used for coordinator-level events

**Sensitive data:** No credentials logged; error messages redact or generalize

## Comments

**When to Comment:**
- Function docstrings for public methods in classes
- Inline comments for non-obvious logic, especially WebSocket frame parsing
- Section headers with `# --- description ---` for grouping related methods
- Comments before complex OAuth/PKCE flows explaining CAME API behavior

**Examples:**
- `# Simple exponential backoff before reconnect`
- `# Token expired on the server; clear and refresh`
- `# Web apps send the JWT as a subprotocol`
- `# Note the language param` — documenting reverse-engineered API requirements

**Docstrings:**
- Class docstrings present for main clients: `CameConnectClient`, `CameWebsocketClient`, `CameEventHub`
- Method docstrings for public API: `async def get_device_status(...)`, `async def apply_event(...)`
- No JSDoc/TSDoc style (Python standard docstring format)

## Function Design

**Size:** Functions tend to be 10–40 lines; larger methods (50–60 lines) broken with helper methods

**Parameters:**
- Type hints on all function signatures: `async def _request(self, method: str, url: str, ...) -> tuple[int, Any]`
- Keyword-only arguments after `*` in request helpers: `async def _request(..., *, json=None, params=None)`
- Defaults applied where sensible: `_generate_code_verifier(n: int = 64)`

**Return Values:**
- Tuple unpacking for multi-value returns: `status, js = await self._request(...)`
- Optional returns with `None` for missing/invalid states: `Optional[int]`, `Optional[str]`
- Dictionary returns for structured data: `Dict[str, Any]`

## Module Design

**Exports:**
- No `__all__` declarations; all public classes and functions are module-level
- Classes imported directly: `from .api import CameConnectClient, CameWebsocketClient`
- Constants exported from `const.py` and imported as needed

**Barrel Files:**
- `const.py` acts as constant barrel (single location for all config/phase codes)
- No index file (`__init__.py` in subdirectories); flat structure preferred

**Class Organization:**
- Public methods follow private helper methods: `# --- helpers ---` then `# --- public API ---`
- Entity classes inherit from Home Assistant base classes first, then add mixins
- Example: `class CameGateCover(CoordinatorEntity, CoverEntity):`

**Base Classes:**
- `_BaseSensor` and `_BaseBS` private base classes for shared entity logic
- Reduces duplication across similar sensor/binary_sensor implementations
- Pattern: subclass with specific name and device_class, override `native_value` property

## Async/Await Conventions

**Async functions:**
- All I/O operations are async: HTTP requests, WebSocket operations, token refresh
- Async locks for critical sections: `async with self._lock:` for token refresh race prevention
- Task creation: `asyncio.create_task()` with explicit name: `asyncio.create_task(self._run(), name="came_ws_run")`
- Timeout wrapping: `asyncio.wait_for(self._stop.wait(), timeout=backoff)`

**Home Assistant integrations:**
- `async_setup_entry()` for config entry setup
- `async_on_unload()` for cleanup registration
- Coordinator methods are async: `async_config_entry_first_refresh()`, `async_set_updated_data()`

---

*Convention analysis: 2026-03-15*
