"""
The Game protocol every game class must implement to plug into the
multi-game runtime. See CONTEXT.md for the lifecycle contract.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Literal, TYPE_CHECKING

if TYPE_CHECKING:
    from .cues import CueEvent

# The set of input channels a game can declare interest in. Pucks send
# the union of these every tick; games receive an InputEvent already
# normalised to floats / bools regardless of firmware revision.
InputKind = Literal[
    "tilt_x",
    "tilt_y",
    "shake",
    "button_tap",
    "button_hold",
    "gyro_z",
]


@dataclass
class Player:
    """One puck at the table.

    puck_uuid is the Supabase pucks.id (UUID) used for persistence.
    puck_index is the small 1..8 firmware-facing id used by the game logic
    and the TV state snapshot. Both are required because the runtime
    bridges firmware and Supabase.
    """

    puck_uuid: str
    puck_index: int
    name: str
    color: str
    is_active: bool = True


@dataclass
class InputEvent:
    """Single puck input frame, normalised."""

    puck_index: int
    tilt_x: float = 0.0
    tilt_y: float = 0.0
    shake: float = 0.0
    button_tap: bool = False
    button_hold: bool = False
    gyro_z: float = 0.0


@dataclass
class ScoreEvent:
    """One score change to persist. Emitted by on_input or tick.

    event_type:
        - "round" — a mid-match score update (e.g. correct answer, lap
          completed). Many of these per match per puck.
        - "final" — the puck's final score. Exactly one per match per
          puck, enforced by the uniq_final_score_per_match_puck index
          in Supabase.
    """

    puck_index: int
    round_number: int
    score_delta: int
    score_total: int
    event_type: Literal["round", "final"] = "round"


@dataclass
class StateUpdate:
    """Returned by on_input and tick. Bundles the new state snapshot for
    the TV with any score events the manager should persist and any
    cues to play.

    is_final flags that the game has reached its terminal state; the
    MatchManager will run finalisation (emit any remaining final scores,
    update matches.status to 'finished').
    """

    state: dict[str, Any]
    score_events: list[ScoreEvent] = field(default_factory=list)
    cues: list["CueEvent"] = field(default_factory=list)
    is_final: bool = False


class Game(ABC):
    """Base class every game inherits from.

    Class attributes describe the game to the registry. Instance methods
    define its lifecycle. The runtime never touches instance internals
    directly — it goes through these methods so any game can plug in
    without engine changes.
    """

    # === Class-level metadata. Subclasses must override. ===
    slug: str = ""
    display_name: str = ""
    min_players: int = 1
    max_players: int = 8
    input_schema: tuple[InputKind, ...] = ()

    # === Lifecycle. ===

    @abstractmethod
    def __init__(self, players: list[Player], **options: Any) -> None:
        """Set up initial state from the joined player list."""

    @abstractmethod
    def on_input(self, event: InputEvent) -> StateUpdate:
        """Process one puck input frame. Return the new state snapshot
        plus any score events to persist."""

    def tick(self) -> StateUpdate:
        """Called by the manager at a fixed cadence (e.g. 10 Hz) for
        time-based progression — countdowns, idle players, hazards.

        Default no-op. Override for time-driven games (racing, brawler).
        """
        return StateUpdate(state=self.get_state())

    @abstractmethod
    def get_state(self) -> dict[str, Any]:
        """Return the full game state for the TV view. Must be
        JSON-serialisable."""

    @abstractmethod
    def is_over(self) -> bool:
        """Whether the game has reached terminal state."""

    @abstractmethod
    def final_scores(self) -> dict[int, int]:
        """Map puck_index -> final score. Called by the manager exactly
        once when the match finalises."""
