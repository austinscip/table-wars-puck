"""
Normalisation between raw puck HTTP payloads and the runtime's
InputEvent dataclass.

The Flask app receives wildly inconsistent input JSON across game routes
today (tilt_x vs tilt vs tx, shake vs shake_intensity, button_held vs
button_hold). This module is the one place those aliases collapse so
every game sees a single canonical shape.

It is also a TRUST BOUNDARY: the payload is attacker-controllable from any
device on the venue LAN. Every numeric field is parsed defensively —
non-numeric strings, NaN, and Infinity are rejected (default 0.0) and values
are clamped to sane physical ranges — so a malformed `{"shake":"inf"}` can't
drive game physics to infinity or serialise NaN into the snapshot JSON the TV
must parse (audit finding 0.2).
"""

from __future__ import annotations

import math
from typing import Any

from .game import InputEvent

# Sane clamps for the analog channels. Pucks report tilt in degrees and shake
# as an intensity; anything outside these is noise or an attack.
_TILT_LIMIT = 90.0
_SHAKE_LIMIT = 100.0
_GYRO_LIMIT = 2000.0


def _num(value: Any, *, limit: float, default: float = 0.0) -> float:
    """Coerce an arbitrary JSON value to a finite float in [-limit, limit].
    Bad input (non-numeric, NaN, Inf) collapses to `default` rather than
    raising or poisoning the physics with a non-finite value."""
    try:
        f = float(value)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(f):
        return default
    if f > limit:
        return limit
    if f < -limit:
        return -limit
    return f


def event_from_dict(puck_index: int, data: dict[str, Any]) -> InputEvent:
    if not isinstance(data, dict):
        data = {}
    # tilt_x falls back to the legacy `tilt` alias; resolve the raw value
    # first, then coerce (so a non-numeric `tilt` can't slip past).
    raw_tilt_x = data.get("tilt_x", data.get("tilt", 0))
    raw_shake = data.get("shake", data.get("shake_intensity", 0))
    return InputEvent(
        puck_index=puck_index,
        tilt_x=_num(raw_tilt_x, limit=_TILT_LIMIT),
        tilt_y=_num(data.get("tilt_y", 0), limit=_TILT_LIMIT),
        shake=_num(raw_shake, limit=_SHAKE_LIMIT),
        button_tap=bool(data.get("button_tap", False)),
        button_hold=bool(
            data.get("button_hold", data.get("button_held", False))
        ),
        gyro_z=_num(data.get("gyro_z", 0), limit=_GYRO_LIMIT),
    )
