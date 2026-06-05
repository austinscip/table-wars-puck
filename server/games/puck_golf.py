"""
Puck Golf — second game on the runtime. Turn-based putting across a 3-hole
course (9-hole course design lands later with course generation).

Physics is intentionally trivial for the skeleton — straight-line
trajectory with deterministic distance from power. Real ball physics
(trajectory, wind, terrain) replaces this when F2 polish lands.

Inputs:
- tilt_x / tilt_y       set aim direction. Latched on most recent
                        non-trivial tilt above MIN_TILT.
- shake                 sets shot power 0-100. Decays slowly so the
                        player can build up by shaking then commit.
- button_tap            commits the shot at the current aim + power.

Turn flow:
- Round-robin within a hole: each puck takes one shot in turn.
- When a puck holes out OR exceeds MAX_STROKES, they're "done" with
  this hole; turn passes to the next undone puck.
- When every puck is done with the current hole, advance to the next.
- After the last hole, finalise. Lowest strokes wins.

Scoring convention:
- Per-stroke ScoreEvents emit score_delta = -1, so score_total counts
  down (negative). The leaderboards trigger uses GREATEST() on
  score_total, which means the LEAST-negative number rises to the
  top — i.e. fewest strokes wins. No leaderboards schema change.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any

from runtime import (
    Game,
    Player,
    InputEvent,
    ScoreEvent,
    StateUpdate,
    Cue,
    CueEvent,
    cue_match_start,
    cue_match_end,
    cue_round_start,
    registry,
)


# ============================================================================
# Course data
# ============================================================================


@dataclass
class Hole:
    number: int
    distance: float  # straight-line yards from tee to cup
    par: int
    hole_radius: float = 5.0  # how close counts as "in"


DEFAULT_COURSE: list[Hole] = [
    Hole(number=1, distance=50.0, par=2),
    Hole(number=2, distance=80.0, par=3),
    Hole(number=3, distance=120.0, par=3),
]


# ============================================================================
# Tuning constants
# ============================================================================

MIN_TILT = 12.0           # tilts below this don't change aim
MAX_STROKES = 6           # cap per hole; ball "freezes" at this count
POWER_PER_SHAKE = 8.0     # how much one shake unit adds to held power
POWER_DECAY_PER_SEC = 12.0  # power drains while the player hesitates
POWER_MAX = 100.0
DISTANCE_PER_POWER = 1.4  # yards moved per power unit

# Penalty score per stroke, used so leaderboards.high_score gives
# fewest-strokes-wins via GREATEST() (e.g. -5 > -8).
STROKE_PENALTY = -1


@dataclass
class PlayerState:
    puck_index: int
    aim_x: float = 0.0            # current latched tilt vector
    aim_y: float = 1.0            # default "north" so a fresh puck has a sensible aim
    power: float = 0.0
    last_power_update: float = field(default_factory=time.monotonic)
    # Per-hole progress (one entry per played hole).
    holes_strokes: list[int] = field(default_factory=list)
    hole_done: bool = False
    distance_remaining: float = 0.0
    ball_x: float = 0.0
    ball_y: float = 0.0


# ============================================================================
# Game class
# ============================================================================


class PuckGolf(Game):
    slug = "puck_golf"
    display_name = "Puck Golf"
    min_players = 1
    max_players = 8
    input_schema = ("tilt_x", "tilt_y", "shake", "button_tap")

    def __init__(
        self,
        players: list[Player],
        course: list[Hole] | None = None,
        **_options: Any,
    ) -> None:
        self.players = players
        self.course = list(course) if course else list(DEFAULT_COURSE)
        self.hole_index = 0
        self.turn_queue: list[int] = [p.puck_index for p in players]
        self.turn_index = 0
        self.player_state: dict[int, PlayerState] = {
            p.puck_index: PlayerState(puck_index=p.puck_index) for p in players
        }
        self._reset_hole_state()
        self.finished = False
        # Queue match_start + first hole_start for the first state
        # update so the TV gets the right beat before any shot.
        self._pending_cues: list[CueEvent] = [
            cue_match_start(),
            cue_round_start(
                round_number=self.current_hole.number,
                par=self.current_hole.par,
                distance=self.current_hole.distance,
            ),
        ]

    # === Lifecycle ===

    def on_input(self, event: InputEvent) -> StateUpdate:
        cues: list[CueEvent] = []
        score_events: list[ScoreEvent] = []
        cues.extend(self._drain_pending())

        if self.finished:
            return StateUpdate(state=self.get_state())

        if not self._is_current_turn(event.puck_index):
            return StateUpdate(state=self.get_state(), cues=cues)

        state = self.player_state[event.puck_index]
        self._decay_power(state)

        if event.tilt_x != 0.0 or event.tilt_y != 0.0:
            new_aim = _normalised_aim(event.tilt_x, event.tilt_y)
            if new_aim is not None:
                state.aim_x, state.aim_y = new_aim

        if event.shake > 0:
            state.power = min(POWER_MAX, state.power + event.shake * POWER_PER_SHAKE / 10.0)
            state.last_power_update = time.monotonic()

        if event.button_tap:
            score_events, shot_cues = self._take_shot(event.puck_index)
            cues.extend(shot_cues)

        cues.extend(self._drain_pending())
        return StateUpdate(
            state=self.get_state(),
            cues=cues,
            score_events=score_events,
            is_final=self.finished,
        )

    def tick(self) -> StateUpdate:
        cues = self._drain_pending()
        if self.finished:
            return StateUpdate(state=self.get_state(), cues=cues)
        # Decay power for whoever's holding to give the player a beat-
        # accurate visual on the TV. No score events on tick.
        if self.turn_queue:
            current = self.turn_queue[self.turn_index]
            self._decay_power(self.player_state[current])
        cues.extend(self._drain_pending())
        return StateUpdate(state=self.get_state(), cues=cues)

    def is_over(self) -> bool:
        return self.finished

    def final_scores(self) -> dict[int, int]:
        # Sum of per-hole strokes as a NEGATIVE total so leaderboards
        # interprets fewer strokes = higher score.
        return {
            p.puck_index: sum(self.player_state[p.puck_index].holes_strokes) * STROKE_PENALTY
            for p in self.players
        }

    def get_state(self) -> dict[str, Any]:
        hole = self.current_hole if not self.finished else None
        current = self.turn_queue[self.turn_index] if self.turn_queue else None
        return {
            "game_slug": self.slug,
            "hole_number": hole.number if hole else None,
            "hole_par": hole.par if hole else None,
            "hole_distance": hole.distance if hole else None,
            "hole_radius": hole.hole_radius if hole else None,
            "current_turn_puck_index": current,
            "finished": self.finished,
            "players": [
                {
                    "puck_index": s.puck_index,
                    "aim": {"x": round(s.aim_x, 3), "y": round(s.aim_y, 3)},
                    "power": round(s.power, 1),
                    "ball": {"x": round(s.ball_x, 2), "y": round(s.ball_y, 2)},
                    "distance_remaining": round(s.distance_remaining, 2),
                    "hole_strokes": s.holes_strokes[self.hole_index]
                    if not self.finished and self.hole_index < len(s.holes_strokes)
                    else 0,
                    "hole_done": s.hole_done,
                    "total_strokes": sum(s.holes_strokes),
                }
                for s in self.player_state.values()
            ],
        }

    # === Shot mechanics ===

    def _take_shot(self, puck_index: int) -> tuple[list[ScoreEvent], list[CueEvent]]:
        state = self.player_state[puck_index]
        # Strokes are 1-indexed per hole; this puck's stroke for the
        # current hole increments now.
        if len(state.holes_strokes) <= self.hole_index:
            state.holes_strokes.append(0)
        state.holes_strokes[self.hole_index] += 1
        stroke = state.holes_strokes[self.hole_index]

        # Shot trajectory: distance moved = power * DISTANCE_PER_POWER.
        # Direction is the latched aim vector.
        distance = state.power * DISTANCE_PER_POWER
        state.ball_x += state.aim_x * distance
        state.ball_y += state.aim_y * distance
        state.distance_remaining = self._distance_to_cup(state)
        state.power = 0.0  # consumed

        hole = self.current_hole
        in_hole = state.distance_remaining <= hole.hole_radius
        timed_out = stroke >= MAX_STROKES and not in_hole

        cues: list[CueEvent] = [
            CueEvent(
                cue=Cue.PLAYER_LOCKED_IN,
                target=puck_index,
                payload={
                    "stroke": stroke,
                    "distance_remaining": round(state.distance_remaining, 2),
                    "in_hole": in_hole,
                },
            ),
        ]

        # One stroke -> one negative-delta score event so leaderboards
        # tallies properly even mid-match.
        running_total = sum(state.holes_strokes) * STROKE_PENALTY
        score_events = [
            ScoreEvent(
                puck_index=puck_index,
                round_number=hole.number,
                score_delta=STROKE_PENALTY,
                score_total=running_total,
                event_type="round",
            )
        ]

        if in_hole or timed_out:
            state.hole_done = True
            cues.append(
                CueEvent(
                    cue=Cue.ROUND_END,
                    target=puck_index,
                    payload={
                        "hole_number": hole.number,
                        "hole_strokes": stroke,
                        "made": in_hole,
                    },
                )
            )

        # Advance turn. If every puck is done with this hole, advance
        # the hole. If we just finished the last hole, finalise.
        self._advance_turn()
        return score_events, cues

    def _advance_turn(self) -> None:
        # Round-robin: bump to next puck. If that puck is already done
        # with the hole, keep skipping. If everyone is done, advance hole.
        n = len(self.turn_queue)
        for _ in range(n):
            self.turn_index = (self.turn_index + 1) % n
            puck = self.turn_queue[self.turn_index]
            if not self.player_state[puck].hole_done:
                return
        # All done with this hole.
        self.hole_index += 1
        if self.hole_index >= len(self.course):
            self.finished = True
            # Winner = least strokes (highest final score since we
            # negate).
            finals = self.final_scores()
            winner_index = max(finals.items(), key=lambda kv: kv[1])[0]
            self._pending_cues.append(cue_match_end(winner_index=winner_index))
            return
        # Next hole: reset per-hole state, queue hole_start cue.
        self._reset_hole_state()
        self.turn_index = 0
        self._pending_cues.append(
            cue_round_start(
                round_number=self.current_hole.number,
                par=self.current_hole.par,
                distance=self.current_hole.distance,
            )
        )

    # === Internals ===

    @property
    def current_hole(self) -> Hole:
        return self.course[self.hole_index]

    def _reset_hole_state(self) -> None:
        hole = self.current_hole
        for state in self.player_state.values():
            state.hole_done = False
            state.ball_x = 0.0
            state.ball_y = 0.0
            state.distance_remaining = hole.distance
            state.power = 0.0
            state.last_power_update = time.monotonic()

    def _is_current_turn(self, puck_index: int) -> bool:
        return (
            bool(self.turn_queue)
            and self.turn_queue[self.turn_index] == puck_index
        )

    def _decay_power(self, state: PlayerState) -> None:
        now = time.monotonic()
        dt = now - state.last_power_update
        if dt > 0 and state.power > 0:
            state.power = max(0.0, state.power - dt * POWER_DECAY_PER_SEC)
        state.last_power_update = now

    def _distance_to_cup(self, state: PlayerState) -> float:
        hole = self.current_hole
        # Cup sits straight up at (0, distance).
        return math.hypot(state.ball_x - 0.0, state.ball_y - hole.distance)

    def _drain_pending(self) -> list[CueEvent]:
        if not self._pending_cues:
            return []
        out = self._pending_cues
        self._pending_cues = []
        return out


# ============================================================================
# Helpers
# ============================================================================


def _normalised_aim(tilt_x: float, tilt_y: float) -> tuple[float, float] | None:
    magnitude = math.hypot(tilt_x, tilt_y)
    if magnitude < MIN_TILT:
        return None
    return (tilt_x / magnitude, tilt_y / magnitude)


# ============================================================================
# Registry hookup
# ============================================================================

registry.register(PuckGolf)
