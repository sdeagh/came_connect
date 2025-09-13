from __future__ import annotations

from typing import Any, Dict, Optional, List
import logging
from homeassistant.util import dt as dt_util
from .const import (
    PHASE_OPEN, PHASE_CLOSED, PHASE_OPENING, PHASE_CLOSING, PHASE_STOPPED,
)

_LOGGER = logging.getLogger(__name__)

_VALID_PHASES = {PHASE_OPEN, PHASE_CLOSED, PHASE_OPENING, PHASE_CLOSING, PHASE_STOPPED}


class CameEventHub:
    """Keeps a /devicestatus-like snapshot and applies WS updates to it."""

    def __init__(self, device_id: str) -> None:
        self._device_id = str(device_id)
        # Seed with a sane default shape (Closed / 0%)
        self._snapshot: Dict[str, Any] = {"States": [{}, {}, {"Data": [PHASE_CLOSED, 0]}]}
        self._phase: Optional[int] = PHASE_CLOSED
        self._pos: Optional[int] = 0

    # --- helpers -------------------------------------------------------------

    def _ensure_shape(self) -> None:
        """Make sure States[2]['Data'] exists and is a 2-item list."""
        states = self._snapshot.get("States")
        if not isinstance(states, list) or len(states) < 3:
            states = [{}, {}, {}]
        if not isinstance(states[2], dict):
            states[2] = {}
        if not isinstance(states[2].get("Data"), list) or len(states[2]["Data"]) < 2:
            states[2]["Data"] = [PHASE_CLOSED, 0]
        self._snapshot["States"] = states

    # --- public API ----------------------------------------------------------

    def seed_from_devicestatus(self, js: Dict[str, Any]) -> None:
        """Initialize snapshot and internal phase/pos from initial REST payload."""
        self._snapshot = dict(js or {})
        self._ensure_shape()
        try:
            data: List[int] = self._snapshot["States"][2].get("Data") or []
            self._phase = int(data[0]) if len(data) > 0 else PHASE_CLOSED
            self._pos   = int(data[1]) if len(data) > 1 else 0
        except Exception:
            _LOGGER.debug("Hub seed: bad payload, falling back to defaults", exc_info=True)
            self._phase, self._pos = PHASE_CLOSED, 0
            self._snapshot["States"][2]["Data"] = [self._phase, self._pos]

    def apply_event(self, phase: Optional[int], percent: Optional[int]) -> Optional[Dict[str, Any]]:
        """
        Apply a VarcoStatusUpdate (phase, percent) into the snapshot.
        Return updated snapshot or None if event not applicable.
        """
        if phase is None or phase not in _VALID_PHASES:
            return None

        # If the event doesn't include a percent, derive it for steady states.
        if percent is None:
            if phase == PHASE_OPEN:
                percent = 100
            elif phase == PHASE_CLOSED:
                percent = 0

        self._phase = int(phase)

        if percent is not None:
            try:
                # clamp 0..100 just in case
                self._pos = max(0, min(100, int(percent)))
            except Exception:
                pass


        self._ensure_shape()
        self._snapshot["States"][2]["Data"] = [self._phase, (self._pos if self._pos is not None else 0)]

        try:
            self._snapshot["LastSeen"] = dt_util.utcnow().isoformat()
        except Exception:
            pass

        return self._snapshot
