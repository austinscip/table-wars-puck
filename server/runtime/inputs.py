"""
Normalisation between raw puck HTTP payloads and the runtime's
InputEvent dataclass.

The Flask app receives wildly inconsistent input JSON across game routes
today (tilt_x vs tilt vs tx, shake vs shake_intensity, button_held vs
button_hold). This module is the one place those aliases collapse so
every game sees a single canonical shape.
"""

from __future__ import annotations

from typing import Any

from .game import InputEvent


def event_from_dict(puck_index: int, data: dict[str, Any]) -> InputEvent:
    return InputEvent(
        puck_index=puck_index,
        tilt_x=float(data.get("tilt_x", data.get("tilt") or 0)),
        tilt_y=float(data.get("tilt_y", 0)),
        shake=float(data.get("shake", data.get("shake_intensity", 0))),
        button_tap=bool(data.get("button_tap", False)),
        button_hold=bool(
            data.get("button_hold", data.get("button_held", False))
        ),
        gyro_z=float(data.get("gyro_z", 0)),
    )
