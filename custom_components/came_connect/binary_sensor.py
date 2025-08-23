from __future__ import annotations

from typing import Any, Optional

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

PHASE_OPEN = 16
PHASE_CLOSED = 17
PHASE_OPENING = 32
PHASE_CLOSING = 33


class _BaseBS(CoordinatorEntity, BinarySensorEntity):
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

    @property
    def device_info(self) -> dict[str, Any]:
        return {"identifiers": {(DOMAIN, self._device_id)}, "name": "Gate", "manufacturer": "CAME", "model": "CAME Connect"}


class CameMovingBinarySensor(_BaseBS):
    """True while the gate is moving."""

    def __init__(self, coordinator, device_id: str):
        super().__init__(coordinator, device_id, "Gate Moving", "moving")
        self._attr_device_class = BinarySensorDeviceClass.MOVING

    @property
    def is_on(self) -> bool | None:
        ph = self._phase()
        if ph in (PHASE_OPENING, PHASE_CLOSING):
            return True
        if ph in (PHASE_OPEN, PHASE_CLOSED):
            return False
        # Unknown phase → unknown
        return None

    @property
    def extra_state_attributes(self) -> dict:
        ph = self._phase()
        direction = "opening" if ph == PHASE_OPENING else "closing" if ph == PHASE_CLOSING else None
        return {"phase": ph, "direction": direction, "raw_data": self._raw()}


class CameHubOnlineBinarySensor(_BaseBS):
    """Connectivity status of the cloud hub."""

    def __init__(self, coordinator, device_id: str):
        super().__init__(coordinator, device_id, "Gate Hub Online", "online")
        self._attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    @property
    def is_on(self) -> bool | None:
        val = (self.coordinator.data or {}).get("Online")
        return bool(val) if val is not None else None


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    device_id = data["device_id"]
    async_add_entities(
        [
            CameMovingBinarySensor(coordinator, device_id),
            CameHubOnlineBinarySensor(coordinator, device_id),
        ]
    )
