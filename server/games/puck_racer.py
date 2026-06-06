"""
Puck Racer — third game on the runtime. Real-time 3-lane drag race.

Mike flagged this as the riskiest of the four pilot games (real-time
multiplayer over bar Wi-Fi at <100ms latency). The plan's mitigation
is to ship a simpler racing model first — single direction, 3 lanes,
straight to a finish line — and only expand to full Mario Kart-style
tracks if latency holds. That's what this skeleton is.

Crucially different from SpeedPyramid + PuckGolf:
- Real-time, not turn-based or simultaneous-but-discrete. State
  advances on tick(), not just on_input. on_input only mutates the
  desired input state (target lane, throttle held, boost requested);
  tick() reads that state and integrates.
- Tick is the primary action path. The scheduler (10 Hz) drives the
  whole race. on_input is for input changes only.
- Highest-position-at-end wins (back to standard high-is-better
  scoring, unlike PuckGolf's inverted convention).

Inputs:
- tilt_x         target lane: < -MIN_TILT -> left, > MIN_TILT -> right,
                 else center. Hard-locked to {0, 1, 2}; lane change
                 is instant (no inter-lane coast for the skeleton).
- button_hold    throttle pedal. Held -> accelerate to MAX_SPEED.
                 Released -> coast down to base speed.
- shake          one-shot boost trigger when shake > BOOST_SHAKE_THRESH
                 and a boost charge is available.

Race ends when:
- The first puck crosses FINISH_DISTANCE, OR
- MAX_RACE_SECONDS elapsed since start (race-over flag set even if
  no puck has finished).
After the first finish, the race keeps running for a short
GRACE_SECONDS window so trailing pucks still get a result, then
finalises.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Optional

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
    cue_timer_warning,
    registry,
)


# ============================================================================
# Tuning
# ============================================================================

LANES = 3
MIN_TILT = 12.0                # lane-change threshold
FINISH_DISTANCE = 500.0        # yards
MAX_RACE_SECONDS = 60.0
# TUNING: invented, not playtested. The grace window after the first
# finisher should be validated against real races (too short cuts off
# close finishes; too long stalls the table).
GRACE_SECONDS_AFTER_FIRST_FINISH = 8.0
MAX_SPEED = 60.0               # yards/sec at full throttle
BASE_SPEED = 8.0               # idle drift forward so non-throttling pucks still move
ACCEL = 24.0                   # yards/sec^2 while throttle held
DECEL = 18.0                   # yards/sec^2 when released
BOOST_MULT = 1.8
BOOST_DURATION = 1.6           # seconds
BOOST_SHAKE_THRESH = 15.0
BOOSTS_PER_RACE = 3
TICK_HZ = 10                   # matches runtime.TickScheduler
TICK_DT = 1.0 / TICK_HZ

LANE_POSITIONS: dict[int, str] = {0: "left", 1: "center", 2: "right"}
TIMER_WARNING_AT = 10.0        # TUNING: seconds-left warning, unvalidated


# ============================================================================
# Per-puck state
# ============================================================================


@dataclass
class RacerState:
    puck_index: int
    lane: int = 1
    position: float = 0.0
    speed: float = BASE_SPEED
    throttle_held: bool = False
    boosts_remaining: int = BOOSTS_PER_RACE
    boost_until: Optional[float] = None  # seconds since race_start
    finished: bool = False
    finish_time: Optional[float] = None   # seconds since race_start
    # A disconnected racer is frozen at its current position and out of
    # contention — it never crosses the line, so it ranks by distance
    # covered, always behind anyone who actually finished.
    disconnected: bool = False


# ============================================================================
# Game class
# ============================================================================


class PuckRacer(Game):
    slug = "puck_racer"
    display_name = "Puck Racer"
    min_players = 2
    max_players = 8
    input_schema = ("tilt_x", "shake", "button_hold")
    serializable = True

    def __init__(self, players: list[Player], **_options: Any) -> None:
        self.players = players
        self.racers: dict[int, RacerState] = {
            p.puck_index: RacerState(puck_index=p.puck_index) for p in players
        }
        # Race time is the sum of the REAL dt of each tick (gap #5b), so a
        # lagging box runs the race at wall-clock speed instead of slow
        # motion. Tests pass the nominal dt, so they stay deterministic.
        # tick_count is kept purely as a frame counter for telemetry.
        self.tick_count = 0
        self.elapsed_s = 0.0
        self.first_finish_time: Optional[float] = None
        self.finished = False
        self.warning_fired = False
        self._pending_cues: list[CueEvent] = [
            cue_match_start(),
            cue_round_start(
                round_number=1,
                lanes=LANES,
                finish_distance=FINISH_DISTANCE,
                race_seconds=MAX_RACE_SECONDS,
            ),
        ]

    # === Lifecycle ===

    def on_input(self, event: InputEvent) -> StateUpdate:
        cues = self._drain_pending()
        if self.finished:
            return StateUpdate(state=self.get_state(), cues=cues)
        racer = self.racers.get(event.puck_index)
        if racer is None or racer.finished:
            return StateUpdate(state=self.get_state(), cues=cues)

        # Lane select from tilt_x. Below threshold -> center.
        if event.tilt_x > MIN_TILT:
            racer.lane = 2
        elif event.tilt_x < -MIN_TILT:
            racer.lane = 0
        else:
            racer.lane = 1

        racer.throttle_held = event.button_hold

        if (
            event.shake > BOOST_SHAKE_THRESH
            and racer.boosts_remaining > 0
            and racer.boost_until is None
        ):
            racer.boosts_remaining -= 1
            racer.boost_until = self._race_time + BOOST_DURATION
            cues.append(
                CueEvent(
                    cue=Cue.SCORE_COMBO,
                    target=event.puck_index,
                    payload={"boosts_remaining": racer.boosts_remaining},
                )
            )

        return StateUpdate(state=self.get_state(), cues=cues)

    def tick(self, dt: float = TICK_DT) -> StateUpdate:
        cues = self._drain_pending()
        if self.finished:
            return StateUpdate(state=self.get_state(), cues=cues)

        self.tick_count += 1
        self.elapsed_s += dt
        race_t = self._race_time

        # Time-based warning beat.
        if (
            not self.warning_fired
            and race_t >= MAX_RACE_SECONDS - TIMER_WARNING_AT
        ):
            self.warning_fired = True
            cues.append(cue_timer_warning(seconds_left=int(TIMER_WARNING_AT)))

        score_events: list[ScoreEvent] = []
        for racer in self.racers.values():
            if racer.finished or racer.disconnected:
                continue
            self._integrate(racer, race_t, dt)
            if racer.position >= FINISH_DISTANCE and not racer.finished:
                racer.finished = True
                racer.finish_time = race_t
                if self.first_finish_time is None:
                    self.first_finish_time = race_t
                cues.append(
                    CueEvent(
                        cue=Cue.PLAYER_VICTORY,
                        target=racer.puck_index,
                        payload={
                            "finish_time_sec": round(race_t, 2),
                            "position": round(racer.position, 2),
                        },
                    )
                )

        # Race-over conditions. A disconnected racer counts as "done" for
        # the all-done check — it will never finish, so the race
        # shouldn't wait on it.
        time_up = race_t >= MAX_RACE_SECONDS
        all_finished = all(
            r.finished or r.disconnected for r in self.racers.values()
        )
        grace_done = (
            self.first_finish_time is not None
            and race_t - self.first_finish_time >= GRACE_SECONDS_AFTER_FIRST_FINISH
        )
        if time_up or all_finished or grace_done:
            self._finalize(cues, score_events)

        return StateUpdate(
            state=self.get_state(),
            cues=cues,
            score_events=score_events,
            is_final=self.finished,
        )

    def on_puck_disconnected(self, puck_index: int) -> StateUpdate | None:
        """A real-time racer that goes silent would just coast forward on
        BASE_SPEED forever (its throttle/lane state is frozen at last
        input) and could even win by default. Freeze it instead: mark it
        disconnected so integration skips it and it can't finish. If
        that leaves every racer done, end the race now.
        """
        if self.finished:
            return None
        racer = self.racers.get(puck_index)
        if racer is None or racer.finished or racer.disconnected:
            return None
        racer.disconnected = True
        racer.throttle_held = False

        cues: list[CueEvent] = [
            CueEvent(
                cue=Cue.PLAYER_ELIMINATED,
                target=puck_index,
                payload={"reason": "heartbeat_timeout"},
            )
        ]
        score_events: list[ScoreEvent] = []
        if all(
            r.finished or r.disconnected for r in self.racers.values()
        ):
            self._finalize(cues, score_events)

        return StateUpdate(
            state=self.get_state(),
            cues=cues,
            score_events=score_events,
            is_final=self.finished,
        )

    def on_puck_reconnected(self, puck_index: int) -> StateUpdate | None:
        # Intentionally NON-resumable (audit runtime-games-2026-06-06): a racer
        # frozen for the 8s+ it took to be swept stale is hopelessly behind, so
        # a reconnect does not un-freeze it — it stays a DNF. Explicit override
        # so this is a documented decision, not an accidental inherited no-op.
        return None

    # === Durability ===

    def serialize(self) -> dict[str, Any]:
        # Race time is an accumulated-dt float (absolute), so no clock
        # conversion is needed across a restart.
        return {
            "tick_count": self.tick_count,
            "elapsed_s": self.elapsed_s,
            "first_finish_time": self.first_finish_time,
            "finished": self.finished,
            "warning_fired": self.warning_fired,
            "racers": {
                str(i): {
                    "lane": r.lane,
                    "position": r.position,
                    "speed": r.speed,
                    "throttle_held": r.throttle_held,
                    "boosts_remaining": r.boosts_remaining,
                    "boost_until": r.boost_until,
                    "finished": r.finished,
                    "finish_time": r.finish_time,
                    "disconnected": r.disconnected,
                }
                for i, r in self.racers.items()
            },
        }

    @classmethod
    def deserialize(cls, players: list[Player], data: dict[str, Any]) -> "PuckRacer":
        game = cls(players)
        game._pending_cues = []  # don't replay match_start on restore
        game.tick_count = data["tick_count"]
        game.elapsed_s = data.get("elapsed_s", data["tick_count"] * TICK_DT)
        game.first_finish_time = data["first_finish_time"]
        game.finished = data["finished"]
        game.warning_fired = data["warning_fired"]
        for key, rd in data["racers"].items():
            r = game.racers.get(int(key))
            if r is None:
                continue
            r.lane = rd["lane"]
            r.position = rd["position"]
            r.speed = rd["speed"]
            r.throttle_held = rd["throttle_held"]
            r.boosts_remaining = rd["boosts_remaining"]
            r.boost_until = rd["boost_until"]
            r.finished = rd["finished"]
            r.finish_time = rd["finish_time"]
            r.disconnected = rd["disconnected"]
        return game

    def is_over(self) -> bool:
        return self.finished

    def final_scores(self) -> dict[int, int]:
        # Score = position at race end (clamped to FINISH_DISTANCE).
        # Pucks that finished get a bonus equal to their inverse finish
        # rank so the first finisher always outranks anyone who didn't
        # finish, even if a coaster crossed the line afterwards.
        finishers = sorted(
            (r for r in self.racers.values() if r.finished),
            key=lambda r: r.finish_time or float("inf"),
        )
        finish_bonus_by_index: dict[int, int] = {}
        for rank, racer in enumerate(finishers):
            finish_bonus_by_index[racer.puck_index] = (
                len(finishers) - rank
            ) * 100
        return {
            r.puck_index: int(min(r.position, FINISH_DISTANCE))
            + finish_bonus_by_index.get(r.puck_index, 0)
            for r in self.racers.values()
        }

    def get_state(self) -> dict[str, Any]:
        return {
            "game_slug": self.slug,
            "race_time_sec": round(self._race_time, 2),
            "race_seconds": MAX_RACE_SECONDS,
            "finish_distance": FINISH_DISTANCE,
            "first_finish_time": self.first_finish_time,
            "finished": self.finished,
            "racers": [
                {
                    "puck_index": r.puck_index,
                    "lane": r.lane,
                    "lane_name": LANE_POSITIONS.get(r.lane, "center"),
                    "position": round(r.position, 2),
                    "speed": round(r.speed, 2),
                    "throttle_held": r.throttle_held,
                    "boosts_remaining": r.boosts_remaining,
                    "boost_active": (
                        r.boost_until is not None and r.boost_until > self._race_time
                    ),
                    "finished": r.finished,
                    "disconnected": r.disconnected,
                    "finish_time_sec": (
                        round(r.finish_time, 2)
                        if r.finish_time is not None
                        else None
                    ),
                }
                for r in self.racers.values()
            ],
        }

    # === Internals ===

    @property
    def _race_time(self) -> float:
        return self.elapsed_s

    def _integrate(self, racer: RacerState, race_t: float, dt: float) -> None:
        # Clear an expired boost.
        if racer.boost_until is not None and race_t >= racer.boost_until:
            racer.boost_until = None

        target = MAX_SPEED if racer.throttle_held else BASE_SPEED
        if racer.speed < target:
            racer.speed = min(target, racer.speed + ACCEL * dt)
        elif racer.speed > target:
            racer.speed = max(target, racer.speed - DECEL * dt)

        effective = racer.speed * (BOOST_MULT if racer.boost_until else 1.0)
        racer.position = min(
            FINISH_DISTANCE, racer.position + effective * dt
        )

    def _finalize(
        self,
        cues: list[CueEvent],
        score_events: list[ScoreEvent],
    ) -> None:
        if self.finished:
            return
        self.finished = True
        finals = self.final_scores()
        winner = max(finals.items(), key=lambda kv: kv[1])[0]
        cues.append(cue_match_end(winner_index=winner))

    def _drain_pending(self) -> list[CueEvent]:
        if not self._pending_cues:
            return []
        out = self._pending_cues
        self._pending_cues = []
        return out


# ============================================================================
# Registry hookup
# ============================================================================

registry.register(PuckRacer)
