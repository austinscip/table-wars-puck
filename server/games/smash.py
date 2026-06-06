"""
Smash — fourth and final pilot game. 4-player simultaneous brawler with
damage-percent accumulation + knockback + ring-out KO. Minimum viable
per the plan: 4 characters, 1 stage, simple movesets. Depth lands
post-pilot.

New mechanical territory for the runtime — first game where one puck's
input directly mutates other pucks' state. The runtime didn't have to
change to accommodate: each Game's on_input returns a single
StateUpdate that already supports cross-player effects because the
state dict and score_events list don't constrain who they're about.
Validates Mike's "game 4 just works" prediction.

Inputs:
- tilt_x / tilt_y    movement vector. Magnitude scales 0..1 with how
                     hard the puck is tilted.
- button_tap         basic attack. Hits any opponent within ATTACK_RANGE
                     of the attacker. ATTACK_DAMAGE per hit, knockback
                     scales with the victim's current damage_pct.
- shake              special attack when shake > SPECIAL_SHAKE_THRESH
                     and the special cooldown has expired. Bigger range,
                     bigger damage, SPECIAL_COOLDOWN_SEC between uses.

Combat:
- Each puck spawns at a corner with 0% damage and STOCKS_PER_PLAYER
  stocks.
- A hit deals damage to the victim's damage_pct and applies a
  knockback velocity in the attacker's facing direction. Knockback
  magnitude = KNOCKBACK_BASE + KNOCKBACK_PER_PCT * victim's new
  damage_pct, so 0% damage barely moves you and 150% damage launches
  you off the stage.
- A puck is KO'd when position leaves ARENA bounds. Loses one stock,
  respawns at centre with 0% damage. KO with 0 stocks remaining =
  eliminated.
- Match ends when one puck has stocks left, OR MAX_MATCH_SECONDS
  elapse (timeout: scoreboard ranks by stocks remaining, then KOs
  landed).

Scoring:
- score = stocks_remaining * 1000 + kos_landed * 200
- Highest wins (back to standard direction).
"""

from __future__ import annotations

import math
import random
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
    registry,
)


# ============================================================================
# Tuning
# ============================================================================

ARENA_X = (-50.0, 50.0)
ARENA_Y = (-30.0, 30.0)
ATTACK_RANGE = 9.0
SPECIAL_RANGE = 14.0
ATTACK_DAMAGE = 8.0
SPECIAL_DAMAGE = 20.0
SPECIAL_COOLDOWN_SEC = 3.0
SPECIAL_SHAKE_THRESH = 15.0
KNOCKBACK_BASE = 4.0
KNOCKBACK_PER_PCT = 0.18
KNOCKBACK_DECAY = 0.82          # multiplicative per tick
MOVE_SPEED = 22.0                # units/sec at full tilt magnitude
TILT_SCALE = 45.0                # tilt value that means "full speed"
DAMAGE_MAX = 999.0
STOCKS_PER_PLAYER = 3
MAX_MATCH_SECONDS = 180.0
TICK_HZ = 10
TICK_DT = 1.0 / TICK_HZ

# Four spawn corners; up to 4 pucks. Beyond that we'd cycle.
SPAWN_POSITIONS = [
    (-30.0, 15.0),
    (30.0, 15.0),
    (-30.0, -15.0),
    (30.0, -15.0),
]
RESPAWN_CENTRE = (0.0, 10.0)     # safer than (0, 0) — gives the player a beat


@dataclass
class Fighter:
    puck_index: int
    x: float
    y: float
    damage_pct: float = 0.0
    stocks: int = STOCKS_PER_PLAYER
    facing_x: float = 1.0
    facing_y: float = 0.0
    move_vx: float = 0.0
    move_vy: float = 0.0
    knockback_vx: float = 0.0
    knockback_vy: float = 0.0
    special_ready_at: float = 0.0     # match-time seconds
    kos_landed: int = 0
    eliminated: bool = False
    # Who last dealt damage to this fighter — the KO is credited to them
    # when this fighter rings out. None = self-destruct (no credit).
    last_hit_by: Optional[int] = None


class Smash(Game):
    slug = "smash"
    display_name = "Smash"
    min_players = 2
    max_players = 4
    input_schema = ("tilt_x", "tilt_y", "shake", "button_tap")
    serializable = True

    def __init__(self, players: list[Player], **_options: Any) -> None:
        self.players = players
        self.fighters: dict[int, Fighter] = {}
        for i, p in enumerate(players):
            sx, sy = SPAWN_POSITIONS[i % len(SPAWN_POSITIONS)]
            self.fighters[p.puck_index] = Fighter(
                puck_index=p.puck_index, x=sx, y=sy
            )
        # Match time = sum of real per-tick dt (gap #5b), so the brawl runs
        # at wall-clock speed on a lagging box. tick_count is telemetry only.
        self.tick_count = 0
        self.elapsed_s = 0.0
        self.finished = False
        self.winner_index: Optional[int] = None
        self._pending_cues: list[CueEvent] = [
            cue_match_start(),
            cue_round_start(round_number=1, stocks=STOCKS_PER_PLAYER),
        ]

    # === Lifecycle ===

    def on_input(self, event: InputEvent) -> StateUpdate:
        cues = self._drain_pending()
        if self.finished:
            return StateUpdate(state=self.get_state(), cues=cues)
        fighter = self.fighters.get(event.puck_index)
        if fighter is None or fighter.eliminated:
            return StateUpdate(state=self.get_state(), cues=cues)

        score_events: list[ScoreEvent] = []

        # Movement vector from tilt.
        mx = max(min(event.tilt_x / TILT_SCALE, 1.0), -1.0)
        my = max(min(event.tilt_y / TILT_SCALE, 1.0), -1.0)
        fighter.move_vx = mx * MOVE_SPEED
        fighter.move_vy = my * MOVE_SPEED
        if mx != 0.0 or my != 0.0:
            mag = math.hypot(mx, my) or 1.0
            fighter.facing_x = mx / mag
            fighter.facing_y = my / mag

        if event.button_tap:
            self._resolve_attack(
                fighter,
                damage=ATTACK_DAMAGE,
                attack_range=ATTACK_RANGE,
                cues=cues,
                score_events=score_events,
            )

        if (
            event.shake > SPECIAL_SHAKE_THRESH
            and self._match_time >= fighter.special_ready_at
        ):
            fighter.special_ready_at = self._match_time + SPECIAL_COOLDOWN_SEC
            self._resolve_attack(
                fighter,
                damage=SPECIAL_DAMAGE,
                attack_range=SPECIAL_RANGE,
                cues=cues,
                score_events=score_events,
            )

        return StateUpdate(
            state=self.get_state(),
            cues=cues,
            score_events=score_events,
            is_final=self.finished,
        )

    def tick(self, dt: float = TICK_DT) -> StateUpdate:
        cues = self._drain_pending()
        if self.finished:
            return StateUpdate(state=self.get_state(), cues=cues)

        self.tick_count += 1
        self.elapsed_s += dt
        score_events: list[ScoreEvent] = []
        # Knockback is an exponential per-tick decay; raise it to dt/TICK_DT
        # so the bleed-off keeps the same half-life in wall-time regardless
        # of the real tick interval (gap #5b).
        decay = KNOCKBACK_DECAY ** (dt / TICK_DT)

        # Snapshot who was already out BEFORE this tick. KO credit is voided
        # only for a killer eliminated in a PRIOR tick (a stale marker) — a
        # killer who lands a fatal hit and then dies in this SAME tick still
        # earns the KO. Without this, two fighters who ring each other out on
        # the same tick both lost their KO credit, corrupting the winner
        # (audit games-2026-06-06).
        eliminated_before = {
            idx for idx, f in self.fighters.items() if f.eliminated
        }

        for fighter in self.fighters.values():
            if fighter.eliminated:
                continue
            # Integrate movement + knockback into position (by real dt).
            fighter.x += (fighter.move_vx + fighter.knockback_vx) * dt
            fighter.y += (fighter.move_vy + fighter.knockback_vy) * dt
            # Knockback bleeds off so the fighter recovers.
            fighter.knockback_vx *= decay
            fighter.knockback_vy *= decay
            if (
                abs(fighter.knockback_vx) < 0.1
                and abs(fighter.knockback_vy) < 0.1
            ):
                fighter.knockback_vx = 0.0
                fighter.knockback_vy = 0.0

            # KO check.
            if not self._in_arena(fighter.x, fighter.y):
                self._handle_ko(fighter, cues, score_events, eliminated_before)

        # Win condition: only one fighter left with stocks (or only one
        # not eliminated even if others have stocks — match-time
        # timeout). Match-time cap.
        alive = [f for f in self.fighters.values() if not f.eliminated]
        if len(alive) <= 1 and len(self.fighters) > 1:
            self._finalize(alive[0] if alive else None, cues)
        elif self._match_time >= MAX_MATCH_SECONDS:
            best = max(
                self.fighters.values(),
                key=lambda f: (f.stocks, f.kos_landed),
            )
            self._finalize(best, cues)

        return StateUpdate(
            state=self.get_state(),
            cues=cues,
            score_events=score_events,
            is_final=self.finished,
        )

    def on_puck_disconnected(self, puck_index: int) -> StateUpdate | None:
        """A silent fighter just stands still as a punching bag and, worse,
        keeps the match from ending — the win condition is "one fighter
        left standing", and a frozen-but-not-eliminated puck never gets
        KO'd off the stage on its own. Eliminate it outright (forfeit its
        remaining stocks) so the brawl can resolve. If that leaves one
        fighter, finalise with them as the winner.
        """
        if self.finished:
            return None
        fighter = self.fighters.get(puck_index)
        if fighter is None or fighter.eliminated:
            return None
        fighter.eliminated = True

        cues: list[CueEvent] = [
            CueEvent(
                cue=Cue.PLAYER_ELIMINATED,
                target=puck_index,
                payload={"reason": "heartbeat_timeout"},
            )
        ]
        alive = [f for f in self.fighters.values() if not f.eliminated]
        if len(alive) <= 1 and len(self.fighters) > 1:
            self._finalize(alive[0] if alive else None, cues)

        return StateUpdate(
            state=self.get_state(), cues=cues, is_final=self.finished
        )

    # === Durability ===

    def serialize(self) -> dict[str, Any]:
        # match_time is an accumulated-dt float (absolute); no clock conversion.
        return {
            "tick_count": self.tick_count,
            "elapsed_s": self.elapsed_s,
            "finished": self.finished,
            "winner_index": self.winner_index,
            "fighters": {
                str(i): {
                    "x": f.x, "y": f.y,
                    "damage_pct": f.damage_pct,
                    "stocks": f.stocks,
                    "facing_x": f.facing_x, "facing_y": f.facing_y,
                    "move_vx": f.move_vx, "move_vy": f.move_vy,
                    "knockback_vx": f.knockback_vx, "knockback_vy": f.knockback_vy,
                    "special_ready_at": f.special_ready_at,
                    "kos_landed": f.kos_landed,
                    "eliminated": f.eliminated,
                    "last_hit_by": f.last_hit_by,
                }
                for i, f in self.fighters.items()
            },
        }

    @classmethod
    def deserialize(cls, players: list[Player], data: dict[str, Any]) -> "Smash":
        game = cls(players)
        game._pending_cues = []
        game.tick_count = data["tick_count"]
        game.elapsed_s = data.get("elapsed_s", data["tick_count"] * TICK_DT)
        game.finished = data["finished"]
        game.winner_index = data["winner_index"]
        for key, fd in data["fighters"].items():
            f = game.fighters.get(int(key))
            if f is None:
                continue
            f.x, f.y = fd["x"], fd["y"]
            f.damage_pct = fd["damage_pct"]
            f.stocks = fd["stocks"]
            f.facing_x, f.facing_y = fd["facing_x"], fd["facing_y"]
            f.move_vx, f.move_vy = fd["move_vx"], fd["move_vy"]
            f.knockback_vx, f.knockback_vy = fd["knockback_vx"], fd["knockback_vy"]
            f.special_ready_at = fd["special_ready_at"]
            f.kos_landed = fd["kos_landed"]
            f.eliminated = fd["eliminated"]
            f.last_hit_by = fd["last_hit_by"]
        return game

    def is_over(self) -> bool:
        return self.finished

    def final_scores(self) -> dict[int, int]:
        return {
            idx: f.stocks * 1000 + f.kos_landed * 200
            for idx, f in self.fighters.items()
        }

    def get_state(self) -> dict[str, Any]:
        return {
            "game_slug": self.slug,
            "match_time_sec": round(self._match_time, 2),
            "match_seconds": MAX_MATCH_SECONDS,
            "arena": {"x": list(ARENA_X), "y": list(ARENA_Y)},
            "finished": self.finished,
            "winner_index": self.winner_index,
            "fighters": [
                {
                    "puck_index": f.puck_index,
                    "x": round(f.x, 2),
                    "y": round(f.y, 2),
                    "damage_pct": round(f.damage_pct, 1),
                    "stocks": f.stocks,
                    "facing": {"x": round(f.facing_x, 3), "y": round(f.facing_y, 3)},
                    "kos_landed": f.kos_landed,
                    "eliminated": f.eliminated,
                    "special_ready_in_sec": max(
                        0.0, round(f.special_ready_at - self._match_time, 2)
                    ),
                }
                for f in self.fighters.values()
            ],
        }

    # === Combat ===

    def _resolve_attack(
        self,
        attacker: Fighter,
        *,
        damage: float,
        attack_range: float,
        cues: list[CueEvent],
        score_events: list[ScoreEvent],
    ) -> None:
        for victim in self.fighters.values():
            if (
                victim.puck_index == attacker.puck_index
                or victim.eliminated
            ):
                continue
            if math.hypot(victim.x - attacker.x, victim.y - attacker.y) > attack_range:
                continue

            victim.damage_pct = min(DAMAGE_MAX, victim.damage_pct + damage)
            kb = KNOCKBACK_BASE + KNOCKBACK_PER_PCT * victim.damage_pct
            victim.knockback_vx += attacker.facing_x * kb
            victim.knockback_vy += attacker.facing_y * kb
            # Remember who last hit them so the KO is credited correctly
            # in free-for-alls (the old "opponent with most KOs" heuristic
            # was wrong with 3+ fighters).
            victim.last_hit_by = attacker.puck_index
            cues.append(
                CueEvent(
                    cue=Cue.PLAYER_CORRECT,  # attacker landed a hit
                    target=attacker.puck_index,
                    payload={
                        "victim_index": victim.puck_index,
                        "damage": damage,
                        "victim_total_pct": round(victim.damage_pct, 1),
                    },
                )
            )

    def _handle_ko(
        self,
        fighter: Fighter,
        cues: list[CueEvent],
        score_events: list[ScoreEvent],
        eliminated_before: Optional[set[int]] = None,
    ) -> None:
        fighter.stocks -= 1
        fighter.damage_pct = 0.0
        fighter.knockback_vx = 0.0
        fighter.knockback_vy = 0.0
        # Respawn at centre, or eliminate if no stocks left.
        if fighter.stocks <= 0:
            fighter.eliminated = True
            cues.append(
                CueEvent(
                    cue=Cue.PLAYER_ELIMINATED,
                    target=fighter.puck_index,
                )
            )
        else:
            fighter.x, fighter.y = RESPAWN_CENTRE
            cues.append(
                CueEvent(
                    cue=Cue.PLAYER_TIMEOUT,  # rough fit: "lost a stock"
                    target=fighter.puck_index,
                    payload={"stocks_left": fighter.stocks},
                )
            )

        # Credit the KO to whoever last dealt damage to this fighter. This
        # is correct in free-for-alls; a self-destruct (no last hitter, or
        # the last hitter being yourself/already eliminated) credits no
        # one. Reset the marker so a respawn starts clean.
        killer_index = fighter.last_hit_by
        fighter.last_hit_by = None
        if killer_index is not None and killer_index != fighter.puck_index:
            credited = self.fighters.get(killer_index)
            # Credit unless the killer was already out at the START of this tick
            # (a stale marker). A killer eliminated in this same tick still
            # earns the KO. `eliminated_before` is None only on legacy/direct
            # calls — fall back to the live flag then.
            killer_was_out = (
                killer_index in eliminated_before
                if eliminated_before is not None
                else (credited.eliminated if credited else True)
            )
            if credited is not None and not killer_was_out:
                credited.kos_landed += 1
                score_events.append(
                    ScoreEvent(
                        puck_index=credited.puck_index,
                        round_number=1,
                        score_delta=200,
                        score_total=credited.stocks * 1000 + credited.kos_landed * 200,
                        event_type="round",
                    )
                )

    def _finalize(
        self, winner: Optional[Fighter], cues: list[CueEvent]
    ) -> None:
        if self.finished:
            return
        self.finished = True
        if winner is not None:
            self.winner_index = winner.puck_index
            cues.append(cue_match_end(winner_index=winner.puck_index))
        else:
            cues.append(cue_match_end(winner_index=None))

    # === Internals ===

    @property
    def _match_time(self) -> float:
        return self.elapsed_s

    @staticmethod
    def _in_arena(x: float, y: float) -> bool:
        return (
            ARENA_X[0] <= x <= ARENA_X[1]
            and ARENA_Y[0] <= y <= ARENA_Y[1]
        )

    def _drain_pending(self) -> list[CueEvent]:
        if not self._pending_cues:
            return []
        out = self._pending_cues
        self._pending_cues = []
        return out


# ============================================================================
# Registry hookup
# ============================================================================

registry.register(Smash)
