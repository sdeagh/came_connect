from __future__ import annotations


import logging
import asyncio
import time

from homeassistant.components.cover import (
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import DeviceInfo

from .const import (
    DOMAIN,
    DEFAULT_MOVING_POLL_INTERVAL,
    MOTION_TIMEOUT_SECONDS,
    PHASE_OPEN, PHASE_CLOSED, PHASE_OPENING, PHASE_CLOSING, PHASE_PAUSED,
)

from .api import CameConnectClient

_LOGGER = logging.getLogger(__name__)

class CameGateCover(CoordinatorEntity, CoverEntity):
    _attr_name = "Gate"
    _attr_device_class = CoverDeviceClass.GATE
    _attr_supported_features = (
        CoverEntityFeature.OPEN
        | CoverEntityFeature.CLOSE
        | CoverEntityFeature.STOP
    )

    def __init__(self, coordinator, client: CameConnectClient, device_id: str,
                 moving_poll_interval: int, motion_timeout: int):
        super().__init__(coordinator)
        self._client = client
        self._device_id = str(device_id)
        self._attr_unique_id = f"came_gate_{device_id}"
        self._last_pos: int | None = None
        self._phase: int | None = None
        self._direction: str | None = None  # "opening" | "closing" | None

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},   # MUST match the sensors’ identifiers
            name="Gate",
            manufacturer="CAME",
            model="CAME Connect",
            configuration_url="https://app.cameconnect.net/",
        )

        # --- motion watch state ---
        self._moving_task: asyncio.Task | None = None
        self._moving_poll_interval = float(moving_poll_interval)
        self._motion_timeout = float(motion_timeout)

    # ---------- helpers ----------
    def _raw(self) -> list[int]:
        data = self.coordinator.data or {}
        states = data.get("States") or []
        return (states[2].get("Data") or []) if len(states) >= 3 else []

    @staticmethod
    def _pos_from_raw(raw: list[int]) -> int | None:
        if len(raw) >= 2:
            try:
                return int(raw[1])
            except Exception:
                return None
        return None

    @staticmethod
    def _phase_from_raw(raw: list[int]) -> int | None:
        if len(raw) >= 1:
            try:
                return int(raw[0])
            except Exception:
                return None
        return None

    # --- Timing helpers ---

    def _is_moving_phase(self) -> bool:
        return self._phase in (PHASE_OPENING, PHASE_CLOSING)

    def _ensure_motion_watch(self) -> None:
        if self._moving_task is None:
            self._moving_task = asyncio.create_task(self._watch_motion())

    def _cancel_motion_watch(self) -> None:
        if self._moving_task:
            self._moving_task.cancel()
            _LOGGER.info('Stopped motion watch')
            self._moving_task = None

    async def _watch_motion(self) -> None:
        """Poll quickly while the gate is moving; stop on steady phase or timeout."""
        
        deadline = time.monotonic() + self._motion_timeout

        _LOGGER.info('Started motion watch: deadline=%s', deadline)

        try:
            while time.monotonic() < deadline:
                # Ask the coordinator to refresh now
                await self.coordinator.async_refresh()
                # Keep polling during dwell (OPEN/PAUSED) and while moving.
                # Stop only when we reach CLOSED (or when the timeout hits).
                if self._phase == PHASE_CLOSED:
                    break
                await asyncio.sleep(self._moving_poll_interval)
        finally:
            self._moving_task = None

    # --- End of timing helpers ---

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        raw = self._raw()
        self._last_pos = self._pos_from_raw(raw)
        self._phase = self._phase_from_raw(raw)

    @callback
    def _handle_coordinator_update(self) -> None:
        raw = self._raw()
        new_pos = self._pos_from_raw(raw)
        new_phase = self._phase_from_raw(raw)

        # Reset each cycle
        self._direction = None

        # 1) Trust CAME phases first
        if new_phase in (PHASE_OPENING, PHASE_CLOSING):
            self._direction = "opening" if new_phase == PHASE_OPENING else "closing"

        elif new_phase in (PHASE_OPEN, PHASE_CLOSED, PHASE_PAUSED):
            # Idle/steady: explicitly no direction
            self._direction = None

        # 2) Only fall back to % delta when phase didn’t tell us motion
        #    AND the position actually changed.
        elif self._last_pos is not None and new_pos is not None and new_pos != self._last_pos:
            if 0 < new_pos < 100:
                self._direction = "opening" if new_pos > self._last_pos else "closing"
            elif new_pos == 0 and self._last_pos > 0:
                self._direction = "closing"
            elif new_pos == 100 and self._last_pos < 100:
                self._direction = "opening"

        # Commit latest values
        self._last_pos = new_pos
        self._phase = new_phase

        # Start fast polling if we detect movement (external triggers too)
        if self._is_moving_phase():
            self._ensure_motion_watch()

        super()._handle_coordinator_update()

    # ---------- HA properties ----------
    @property
    def current_cover_position(self) -> int | None:
        """Return the last known position (0–100)."""
        return self._last_pos if self._last_pos is not None else self._pos_from_raw(self._raw())

    @property
    def is_closed(self) -> bool | None:
        """Return True if the gate is fully closed."""
        if self._phase == PHASE_CLOSED:
            return True
        if self._phase in (PHASE_OPEN, PHASE_OPENING, PHASE_CLOSING):
            return False
        pos = self.current_cover_position
        return None if pos is None else pos == 0

    @property
    def is_opening(self) -> bool | None:
        """Return True if the gate is opening."""
        if self._phase == PHASE_OPENING:
            return True
        if self._phase == PHASE_CLOSING:
            return False
        return True if self._direction == "opening" else (False if self._direction == "closing" else None)

    @property
    def is_closing(self) -> bool | None:
        """Return True if the gate is closing."""
        if self._phase == PHASE_CLOSING:
            return True
        if self._phase == PHASE_OPENING:
            return False
        return True if self._direction == "closing" else (False if self._direction == "opening" else None)

    @property
    def extra_state_attributes(self) -> dict:
        def _phase_name(p: int | None) -> str:
            if p == PHASE_OPEN: return "open"
            if p == PHASE_CLOSED: return "closed"
            if p == PHASE_OPENING: return "opening"
            if p == PHASE_CLOSING: return "closing"
            if p == PHASE_PAUSED: return "paused"
            return str(p) if p is not None else "unknown"

        return {
            "phase": self._phase,
            "phase_name": _phase_name(self._phase),
            "direction": self._direction,
            "last_pos": self._last_pos,
            "raw_data": self._raw(),  # [phase, position]
        }

    # ---------- actions ----------
    async def async_open_cover(self, **kwargs):
        await self._client.send_command(self._device_id, 2)
        self._ensure_motion_watch()
        await self.coordinator.async_request_refresh()
        

    async def async_close_cover(self, **kwargs):
        await self._client.send_command(self._device_id, 5)
        self._ensure_motion_watch()
        await self.coordinator.async_request_refresh()
        
    async def async_stop_cover(self, **kwargs):
        # STOP = 129
        await self._client.send_command(self._device_id, 129)
        self._cancel_motion_watch()
        await self.coordinator.async_request_refresh()

    async def async_set_cover_position(self, **kwargs):
        # Not implemented; unknown cloud command
        return

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    client: CameConnectClient = data["client"]
    device_id = data["device_id"]
    moving_poll = data.get("moving_poll_interval", DEFAULT_MOVING_POLL_INTERVAL)
    motion_timeout = data.get("motion_timeout", MOTION_TIMEOUT_SECONDS)

    async_add_entities([CameGateCover(coordinator, client, device_id, moving_poll, motion_timeout)])
