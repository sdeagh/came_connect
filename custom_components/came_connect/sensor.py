from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .api import CameConnectClient

PHASE_OPEN = 16
PHASE_CLOSED = 17
PHASE_OPENING = 32
PHASE_CLOSING = 33

def _phase_label(code: Optional[int]) -> Optional[str]:
    return {
        PHASE_OPEN: "open",
        PHASE_CLOSED: "closed",
        PHASE_OPENING: "opening",
        PHASE_CLOSING: "closing",
    }.get(code)


class _BaseSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, device_id: str, name: str, slug: str):
        super().__init__(coordinator)
        self._device_id = device_id
        self._attr_name = name
        self._attr_unique_id = f"came_gate_{slug}_{device_id}"

    def _raw(self) -> list[int]:
        data = self.coordinator.data or {}
        states = data.get("States") or []
        return (states[2].get("Data") or []) if len(states) >= 3 else []

    def _phase(self) -> Optional[int]:
        raw = self._raw()
        if len(raw) >= 1:
            try:
                return int(raw[0])
            except Exception:
                pass
        return None

    def _pos(self) -> Optional[int]:
        raw = self._raw()
        if len(raw) >= 2:
            try:
                return int(raw[1])
            except Exception:
                pass
        return None

    @property
    def device_info(self) -> dict[str, Any]:
        return {"identifiers": {(DOMAIN, self._device_id)}, "name": "Gate", "manufacturer": "CAME", "model": "CAME Connect"}


class CamePhaseSensor(_BaseSensor):
    """Human-friendly phase text."""

    def __init__(self, coordinator, device_id: str):
        super().__init__(coordinator, device_id, "Gate Phase", "phase")

    @property
    def native_value(self) -> Optional[str]:
        return _phase_label(self._phase())

    @property
    def extra_state_attributes(self) -> dict:
        raw = self._raw()
        return {"phase_code": self._phase(), "raw_data": raw}


class CamePositionSensor(_BaseSensor):
    """Position % as a sensor."""

    def __init__(self, coordinator, device_id: str):
        super().__init__(coordinator, device_id, "Gate Position", "position")
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> Optional[int]:
        return self._pos()

    @property
    def extra_state_attributes(self) -> dict:
        return {"raw_data": self._raw()}


class CameLastSeenSensor(_BaseSensor):
    """Hub last seen timestamp."""

    def __init__(self, coordinator, device_id: str):
        super().__init__(coordinator, device_id, "Gate Hub Last Seen", "last_seen")
        self._attr_device_class = SensorDeviceClass.TIMESTAMP

    @property
    def native_value(self) -> Optional[datetime]:
        val = (self.coordinator.data or {}).get("LastSeen")
        if not val:
            return None
        try:
            dt = dt_util.parse_datetime(val)
            if dt and dt.tzinfo is None:
                dt = dt_util.as_utc(dt)
            return dt
        except Exception:
            return None


class CameErrorSensor(_BaseSensor):
    """Last non-zero error/response code across state slots."""

    def __init__(self, coordinator, device_id: str):
        super().__init__(coordinator, device_id, "Gate Error", "error")

    @property
    def native_value(self) -> Optional[int]:
        data = self.coordinator.data or {}
        states = data.get("States") or []
        last_nonzero = None
        for s in states:
            ec = s.get("ErrorCode")
            rc = s.get("ResponseCode")
            if isinstance(ec, int) and ec != 0:
                last_nonzero = ec
            if isinstance(rc, int) and rc not in (None, 0):
                last_nonzero = rc
        return last_nonzero

    @property
    def extra_state_attributes(self) -> dict:
        return {"states": (self.coordinator.data or {}).get("States", [])}


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    device_id = data["device_id"]
    async_add_entities(
        [
            CamePhaseSensor(coordinator, device_id),
            CamePositionSensor(coordinator, device_id),
            CameLastSeenSensor(coordinator, device_id),
            CameErrorSensor(coordinator, device_id),
        ]
    )
