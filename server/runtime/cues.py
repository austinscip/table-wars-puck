"""
Cue language — the shared polish vocabulary every game emits to drive
audio, music, SFX, LED patterns, vibration motor, and any future
hardware feedback channel.

Why a cue layer rather than per-game `play("ding.mp3")` calls? Because
every game needs the same handful of beats (someone scored, round
about to end, match started, player eliminated). A cue is a semantic
name; the polish system decides which file plays, which LED palette
flashes, how long the motor buzzes. Asset swaps happen in one place
without touching game logic.

A game emits cues by attaching them to its StateUpdate.cues list. The
MatchManager folds the list into matches.snapshot, the TV diffs the
array across snapshot updates and fires onCue handlers per channel.
Firmware reads its own subset (LED + motor + buzzer) over the puck
HTTP path.

Adding a new cue:
  1. Add a value to Cue below with a one-line comment on intent.
  2. Add asset files at server/assets/<channel>/<cue_name>.<ext>.
  3. Update server/assets/<channel>/assets.yaml with attribution.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class CueChannel(str, Enum):
    """Which feedback layer the cue targets. Subscribers filter on
    channel so an audio-only TV ignores motor cues, etc."""

    VO = "vo"          # Host voice-over line (full sentence, ducks music)
    MUSIC = "music"    # Music bed transitions (start, stop, intensify)
    SFX = "sfx"        # Short ambient effect (ding, buzz, whoosh)
    LED = "led"        # WS2812B ring pattern on the puck
    MOTOR = "motor"    # Vibration motor pulse
    BUZZER = "buzzer"  # Piezo buzzer tone on the puck
    HAPTIC = "haptic"  # Catch-all for combined LED+motor sequences


class Cue(str, Enum):
    """Semantic cue names. The vocabulary is shared across all games so
    polish authors can map cue -> asset once and every game benefits.

    Naming convention: <subject>_<event>. SUBJECTs are PLAYER (the
    puck that triggered), MATCH (the whole match), ROUND, or
    TIMER. EVENTs are concrete moments.
    """

    # Match lifecycle
    MATCH_START = "match_start"
    MATCH_END = "match_end"
    MATCH_RESET = "match_reset"

    # Round structure (used by trivia / golf / racer)
    ROUND_START = "round_start"
    ROUND_END = "round_end"
    ROUND_TRANSITION = "round_transition"

    # Player events
    PLAYER_JOINED = "player_joined"
    PLAYER_LEFT = "player_left"
    PLAYER_CORRECT = "player_correct"      # Right answer, good shot, hit
    PLAYER_WRONG = "player_wrong"          # Wrong answer, miss
    PLAYER_TIMEOUT = "player_timeout"
    PLAYER_LOCKED_IN = "player_locked_in"  # Answer / shot committed
    PLAYER_ELIMINATED = "player_eliminated"
    PLAYER_VICTORY = "player_victory"

    # Score moments
    SCORE_GOLD = "score_gold"        # Top tier (Speed Pyramid <3s)
    SCORE_SILVER = "score_silver"
    SCORE_BRONZE = "score_bronze"
    SCORE_COMBO = "score_combo"      # Multiplier earned

    # Timer beats
    TIMER_TICK = "timer_tick"           # Each second remaining
    TIMER_WARNING = "timer_warning"     # 5 seconds left
    TIMER_EXPIRED = "timer_expired"


@dataclass
class CueEvent:
    """One cue instance fired during a state update.

    target: optional puck_index when the cue is player-specific. None
    means "broadcast" (whole table). Firmware can filter by target so
    only the relevant puck buzzes for player_correct.

    channels: which feedback layers should react. Default is "all" — the
    cue dispatcher decides what each layer's asset is. Authoring a
    cue with a specific channels tuple is the escape hatch for VO-only
    or motor-only beats.

    ts: server-side timestamp at emission. The TV uses this to dedupe
    cues across overlapping snapshot updates.

    payload: optional cue-specific data — score amount, player name,
    question category. Stays small (JSON-serialisable, <100B).
    """

    cue: Cue
    target: Optional[int] = None
    channels: Optional[tuple[CueChannel, ...]] = None
    ts: float = field(default_factory=time.time)
    payload: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "cue": self.cue.value,
            "target": self.target,
            "channels": (
                [c.value for c in self.channels]
                if self.channels is not None
                else None
            ),
            "ts": self.ts,
            "payload": self.payload,
        }


# Convenience constructors so games can emit cues without verbose
# dataclass instantiation:
#
#     update = StateUpdate(state=..., cues=[
#         cue_player_correct(puck_index=3, payload={'tier': 'gold'}),
#         cue_score(puck_index=3, payload={'amount': 1000}),
#     ])


def cue_player_correct(puck_index: int, **payload) -> CueEvent:
    return CueEvent(cue=Cue.PLAYER_CORRECT, target=puck_index, payload=payload)


def cue_player_wrong(puck_index: int, **payload) -> CueEvent:
    return CueEvent(cue=Cue.PLAYER_WRONG, target=puck_index, payload=payload)


def cue_match_start(**payload) -> CueEvent:
    return CueEvent(cue=Cue.MATCH_START, payload=payload)


def cue_match_end(winner_index: Optional[int] = None, **payload) -> CueEvent:
    return CueEvent(
        cue=Cue.MATCH_END,
        target=winner_index,
        payload=payload,
    )


def cue_round_start(round_number: int, **payload) -> CueEvent:
    return CueEvent(
        cue=Cue.ROUND_START,
        payload={"round_number": round_number, **payload},
    )


def cue_timer_warning(seconds_left: int) -> CueEvent:
    return CueEvent(
        cue=Cue.TIMER_WARNING,
        payload={"seconds_left": seconds_left},
    )
