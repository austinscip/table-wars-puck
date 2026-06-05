"""
The Game protocol every game class must implement to plug into the
multi-game runtime. See CONTEXT.md for the lifecycle contract.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Literal, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .cues import CueEvent

# Nominal seconds-per-tick at the target 10 Hz cadence. It's the DEFAULT
# `dt` passed to tick(), so synthetic test ticks advance a fixed step (and
# stay deterministic) while the live scheduler passes the REAL elapsed time
# between ticks — so a lagging box runs timed games at wall-clock speed
# instead of slow motion (ADR/handoff gap #5b).
DEFAULT_TICK_DT = 0.1

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

    def tick(self, dt: float = DEFAULT_TICK_DT) -> StateUpdate:
        """Called by the manager at a fixed cadence (e.g. 10 Hz) for
        time-based progression — countdowns, idle players, hazards.

        `dt` is the REAL elapsed seconds since the previous tick (the live
        scheduler measures it; it defaults to the nominal step so synthetic
        test ticks stay deterministic). Time-driven games MUST integrate by
        `dt`, not by a fixed per-tick constant, or they run in slow motion
        when the box can't hold 10 Hz (gap #5b).

        Default no-op. Override for time-driven games (racing, brawler).
        """
        return StateUpdate(state=self.get_state())

    def on_puck_disconnected(self, puck_index: int) -> Optional[StateUpdate]:
        """Called by the MatchManager when the heartbeat sweep marks
        puck_index as stale — the puck stopped talking (battery, Wi-Fi,
        crash). Detection is shared (HeartbeatTracker); the *reaction* is
        per-game, so games override this to keep the match moving instead
        of hanging on a silent puck:

        - SpeedPyramid force-locks the puck as a TIMEOUT so the round can
          resolve instead of waiting on a lock-in that will never arrive.
        - PuckGolf passes the turn / retires the puck so the round-robin
          doesn't stall on a player who left.
        - PuckRacer and Smash mark the puck eliminated so the win
          condition can still be reached.

        Default no-op returns None — a game that genuinely doesn't care
        about disconnects inherits "ignore". When non-None, the returned
        StateUpdate's cues and score_events are folded into the current
        tick, its state replaces the snapshot, and is_final can finalise
        the match (e.g. the last surviving racer). Called exactly once
        per disconnect transition; a puck that re-pings then dies again
        triggers a fresh call.
        """
        return None

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

    # === Durability (optional) ===
    # A serializable game can be persisted to a store (Redis) and rebuilt,
    # so an active match survives a server restart/redeploy and is the
    # foundation for sharing match state across workers. Games opt in by
    # setting serializable=True and implementing the pair below.
    #
    # Time handling: any process-local `time.monotonic()` timestamp held in
    # state must be serialized as an ELAPSED offset and re-based against a
    # fresh monotonic clock on deserialize, since monotonic is meaningless
    # across processes/restarts. Tick-count-based games (Racer, Smash) need
    # no conversion. Transient `_pending_cues` are intentionally NOT
    # persisted — losing a queued polish beat on the rare restart is fine.

    serializable: bool = False

    def serialize(self) -> dict[str, Any]:
        """Return a JSON-serialisable dict capturing the full game state.
        Override in serializable games."""
        raise NotImplementedError(
            f"{type(self).__name__} is not serializable"
        )

    @classmethod
    def deserialize(
        cls, players: list["Player"], data: dict[str, Any]
    ) -> "Game":
        """Rebuild a game from `players` + a dict produced by serialize().
        Override in serializable games."""
        raise NotImplementedError(f"{cls.__name__} is not deserializable")
