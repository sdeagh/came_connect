from __future__ import annotations

from time import monotonic
import logging
from homeassistant.components.cover import (
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .api import CameConnectClient

# Phase codes seen in your traces:
# 16=open, 17=closed, 32=opening, 33=closing
PHASE_OPEN = 16
PHASE_CLOSED = 17
PHASE_OPENING = 32
PHASE_CLOSING = 33
PHASE_PAUSED = 19

_LOGGER = logging.getLogger(__name__)

class CameGateCover(CoordinatorEntity, CoverEntity):
    _attr_name = "Gate"
    _attr_device_class = CoverDeviceClass.GATE
    _attr_supported_features = (
        CoverEntityFeature.OPEN
        | CoverEntityFeature.CLOSE
        | CoverEntityFeature.STOP
        | CoverEntityFeature.SET_POSITION
    )

    def __init__(self, coordinator, client: CameConnectClient, device_id: str):
        super().__init__(coordinator)
        self._client = client
        self._device_id = device_id
        self._attr_unique_id = f"came_gate_{device_id}"
        self._last_pos: int | None = None
        self._phase: int | None = None
        self._direction: str | None = None  # "opening" | "closing" | None

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
        await self.coordinator.async_request_refresh()
        

    async def async_close_cover(self, **kwargs):
        await self._client.send_command(self._device_id, 5)
        await self.coordinator.async_request_refresh()
        
    async def async_stop_cover(self, **kwargs):
        # STOP = 129
        await self._client.send_command(self._device_id, 129)
        await self.coordinator.async_request_refresh()

    async def async_set_cover_position(self, **kwargs):
        # Not implemented; unknown cloud command
        return

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    client: CameConnectClient = data["client"]
    device_id = data["device_id"]
    async_add_entities([CameGateCover(coordinator, client, device_id)])
