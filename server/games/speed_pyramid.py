"""
Speed Pyramid — the pilot's flagship trivia game. YDKJ-style multiple
choice with speed-tiered scoring. Ported to the runtime Game protocol;
this is the first concrete game on the new architecture.

Scoring tiers (matches the existing trivia_game_engines.SpeedPyramidGame):
   0 -  3000 ms : LEGENDARY (gold)    -> 1000 pts
3000 -  6000 ms : EXPERT    (silver)  ->  500 pts
6000 - 10000 ms : AVERAGE   (bronze)  ->  200 pts
    10000+ ms / no answer  : TIMEOUT  ->    0 pts

Skeleton scope (Track F1 foundation):
- Hardcoded 3-question fixture so the runtime can be smoke-tested
  without the trivia DB. Real DB integration is later.
- Tilt-to-letter selection: north -> A, east -> B, south -> C, west -> D.
  Threshold-based, latched on the most recent tilt above MIN_TILT.
- button_tap locks the current selection in. After lock-in further input
  from that puck is ignored until the next round.
- Round advance: when every player has locked in OR the round timer
  elapses. Manager fires next round automatically.
- Cues emitted per beat: PLAYER_LOCKED_IN, PLAYER_CORRECT/WRONG,
  SCORE_GOLD/SILVER/BRONZE, ROUND_END, MATCH_END.

Polish layered later: real DB questions, themed rounds, comedy beats,
host VO. None of that touches this class — it lands as Cue subscribers
on the TV or asset swaps under server/assets/.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from runtime import (
    Game,
    Player,
    InputEvent,
    ScoreEvent,
    StateUpdate,
    DEFAULT_TICK_DT,
    Cue,
    CueEvent,
    cue_match_start,
    cue_match_end,
    cue_round_start,
    cue_player_correct,
    cue_player_wrong,
    registry,
)


# An optional cloud-backed question source (ADR 0008), wired by the runtime
# container to a TriviaContentCache.load. It returns rows in the SAME shape
# as the SQLite bank (or None to defer). When unset, we use the legacy local
# SQLite DB, then the built-in defaults — so tests and a first-boot dev box
# work with no content configured.
_question_source = None


def set_question_source(source) -> None:  # noqa: ANN001
    """Install the cloud-backed question source (the container does this).
    Pass None to clear it (tests)."""
    global _question_source
    _question_source = source


def _fetch_rows(
    count: int,
    *,
    difficulty: str | None,
    category_id: int | None,
    exclude_ids: list[int] | None,
) -> list[dict] | None:
    """Question rows from the cloud-backed cache if configured, else the
    legacy local SQLite bank. None when neither yields anything."""
    if _question_source is not None:
        try:
            rows = _question_source(
                count,
                difficulty=difficulty,
                category_id=category_id,
                exclude_ids=exclude_ids,
            )
            if rows:
                return rows
        except Exception:  # noqa: BLE001 — never let content sourcing crash a match
            pass
    try:
        from trivia_database import get_questions
    except Exception:
        return None
    return get_questions(
        count=count,
        difficulty=difficulty,
        category_id=category_id,
        exclude_ids=exclude_ids,
    )


def _load_questions_from_db(
    count: int,
    *,
    difficulty: str | None = None,
    category_id: int | None = None,
    exclude_ids: list[int] | None = None,
) -> list["Question"]:
    """Load N questions and convert each row into a Question dataclass.
    Source order: the cloud-backed cache (ADR 0008) → the legacy local
    SQLite DB → built-in DEFAULT_QUESTIONS — so the box keeps serving trivia
    through an internet drop and a fresh dev box works with no content.

    `exclude_ids` is passed through so a caller can avoid re-serving
    questions a player recently saw. (Sourcing those ids — per-puck answer
    history — is still a separate piece; the runtime doesn't persist
    question_id yet, so today the caller supplies them.)"""
    rows = _fetch_rows(
        count,
        difficulty=difficulty,
        category_id=category_id,
        exclude_ids=exclude_ids,
    )
    if not rows:
        return list(DEFAULT_QUESTIONS)

    questions: list[Question] = []
    for r in rows:
        questions.append(
            Question(
                id=int(r["id"]),
                setup=(r.get("setup_text") or "").strip(),
                question=r["question_text"],
                answers={
                    "A": r["answer_a"],
                    "B": r["answer_b"],
                    "C": r["answer_c"],
                    "D": r["answer_d"],
                },
                correct=r["correct_answer"],
                category=r.get("category_name") or "",
                time_limit_ms=(int(r.get("time_limit") or 15) * 1000),
            )
        )
    return questions


# ============================================================================
# Question data
# ============================================================================


@dataclass
class Question:
    id: int
    setup: str
    question: str
    answers: dict[str, str]  # 'A'|'B'|'C'|'D' -> text
    correct: str             # 'A'|'B'|'C'|'D'
    category: str
    time_limit_ms: int = 10_000


# Skeleton fixture so the runtime is testable without the trivia DB. F1
# polish (real DB integration + content rewrite) replaces this list.
DEFAULT_QUESTIONS: list[Question] = [
    Question(
        id=1,
        setup="The bar is split. Half say the band, half say the year.",
        question="Which band's debut album came out in 1991?",
        answers={
            "A": "Pearl Jam",
            "B": "Soundgarden",
            "C": "Nirvana",
            "D": "Alice in Chains",
        },
        correct="A",
        category="Music",
    ),
    Question(
        id=2,
        setup="A cocktail trivia warm-up to ease the table in.",
        question="What spirit is in a classic Old Fashioned?",
        answers={"A": "Vodka", "B": "Gin", "C": "Bourbon", "D": "Tequila"},
        correct="C",
        category="Drinks",
    ),
    Question(
        id=3,
        setup="Time to test the geography nerds.",
        question="Which of these is NOT a Great Lake?",
        answers={
            "A": "Lake Superior",
            "B": "Lake Champlain",
            "C": "Lake Erie",
            "D": "Lake Huron",
        },
        correct="B",
        category="Geography",
    ),
]


# ============================================================================
# Tilt -> letter mapping
# ============================================================================
# Pucks send raw tilt. Speed Pyramid maps cardinal tilt directions to
# answer letters. Threshold gating keeps small noise from flipping the
# selection.

MIN_TILT = 12.0  # below this we treat the puck as flat
_MAX_QUESTION_COUNT = 50  # clamp on the question_count option (audit 2.7)


def tilt_to_letter(tilt_x: float, tilt_y: float) -> str | None:
    abs_x, abs_y = abs(tilt_x), abs(tilt_y)
    if max(abs_x, abs_y) < MIN_TILT:
        return None
    if abs_y >= abs_x:
        # Vertical tilt dominant.
        return "A" if tilt_y > 0 else "C"  # north / south
    # Horizontal tilt dominant.
    return "B" if tilt_x > 0 else "D"  # east / west


# ============================================================================
# Scoring tiers
# ============================================================================


def tier_for(response_time_ms: int) -> str:
    if response_time_ms < 3000:
        return "LEGENDARY"
    if response_time_ms < 6000:
        return "EXPERT"
    if response_time_ms < 10000:
        return "AVERAGE"
    return "TIMEOUT"


def points_for_tier(tier: str) -> int:
    return {
        "LEGENDARY": 1000,
        "EXPERT": 500,
        "AVERAGE": 200,
        "TIMEOUT": 0,
    }[tier]


TIER_CUE: dict[str, Cue] = {
    "LEGENDARY": Cue.SCORE_GOLD,
    "EXPERT": Cue.SCORE_SILVER,
    "AVERAGE": Cue.SCORE_BRONZE,
    "TIMEOUT": Cue.TIMER_EXPIRED,
}


# ============================================================================
# Game class
# ============================================================================


class SpeedPyramid(Game):
    slug = "speed_pyramid"
    display_name = "Speed Pyramid"
    min_players = 1
    max_players = 8
    input_schema = ("tilt_x", "tilt_y", "button_tap")
    serializable = True

    def __init__(
        self,
        players: list[Player],
        questions: list[Question] | None = None,
        question_count: int = 5,
        difficulty: str | None = None,
        category_id: int | None = None,
        exclude_ids: list[int] | None = None,
        **_options: Any,
    ) -> None:
        self.players = players
        if questions is not None:
            # Explicit fixture, typically used by tests.
            self.questions = list(questions)
        else:
            # Clamp question_count to a sane range (audit 2.7) so a bad option
            # (0, negative, absurd) can't reach random.sample(k<0) or yield an
            # empty question set that IndexErrors in __init__.
            try:
                count = int(question_count)
            except (TypeError, ValueError):
                count = 5
            count = max(1, min(count, _MAX_QUESTION_COUNT))
            # Production path: pull from the trivia DB at match creation
            # time. Falls back to DEFAULT_QUESTIONS when the DB is empty
            # or unavailable. exclude_ids lets the caller avoid re-serving
            # recently-seen questions (dedup across matches).
            self.questions = _load_questions_from_db(
                count=count,
                difficulty=difficulty,
                category_id=category_id,
                exclude_ids=exclude_ids,
            )
        self.scores: dict[int, int] = {p.puck_index: 0 for p in players}
        self.round_index = 0
        self.round_started_at: float = 0.0
        self.selected: dict[int, str | None] = {p.puck_index: None for p in players}
        self.locked: dict[int, dict | None] = {
            p.puck_index: None for p in players
        }
        # Pucks the runtime has told us disconnected. They're force-locked
        # as TIMEOUT every round so a permanent disconnect never makes a
        # later round wait out the full timer (the heartbeat sweep only
        # reports a disconnect once, on the round it happens).
        self.disconnected: set[int] = set()
        self.finished = False
        # Match-start cue queued for the first state update so the TV
        # gets a beat before any input. Emitted on next on_input/tick.
        self._pending_cues: list[CueEvent] = [
            cue_match_start(),
            cue_round_start(round_number=1, category=self.current_question.category),
        ]
        self.round_started_at = time.monotonic()

    # === Lifecycle ===

    def on_input(self, event: InputEvent) -> StateUpdate:
        cues: list[CueEvent] = []
        score_events: list[ScoreEvent] = []
        if self._pending_cues:
            cues.extend(self._pending_cues)
            self._pending_cues = []

        if self.finished:
            return StateUpdate(state=self.get_state())

        puck = event.puck_index
        if puck not in self.scores:
            # Stray puck not in the match; ignore.
            return StateUpdate(state=self.get_state(), cues=cues)

        # Already locked in for this round.
        if self.locked.get(puck) is not None:
            return StateUpdate(state=self.get_state(), cues=cues)

        # Update tentative selection from tilt.
        letter = tilt_to_letter(event.tilt_x, event.tilt_y)
        if letter is not None:
            self.selected[puck] = letter

        if event.button_tap and self.selected[puck] is not None:
            score_events, lock_cues = self._lock_in(puck)
            cues.extend(lock_cues)
            if self._all_locked():
                cues.extend(self._end_round_cues())
                self._advance_round()

        # A live player's lock-in must not be held up waiting on a puck
        # that already left — settle any known disconnects so the round
        # can still resolve.
        se2, c2 = self._settle_disconnected()
        score_events.extend(se2)
        cues.extend(c2)

        # Flush any cues queued during this update (round_start for the
        # new round, match_end on finalisation) so the snapshot the TV
        # receives contains the full beat list. Without this, match_end
        # would sit in _pending_cues forever because the match is over
        # and no further on_input runs.
        if self._pending_cues:
            cues.extend(self._pending_cues)
            self._pending_cues = []

        return StateUpdate(
            state=self.get_state(),
            cues=cues,
            score_events=score_events,
            is_final=self.finished,
        )

    def tick(self, dt: float = DEFAULT_TICK_DT) -> StateUpdate:
        # The question timer is measured from time.monotonic() (real
        # wall-clock), so it's already fidelity-correct; dt is accepted for
        # the uniform tick contract but unused.
        cues: list[CueEvent] = []
        score_events: list[ScoreEvent] = []
        if self._pending_cues:
            cues.extend(self._pending_cues)
            self._pending_cues = []

        if self.finished:
            return StateUpdate(state=self.get_state())

        # Settle any known-disconnected pucks first so a permanent
        # disconnect is force-locked at the top of every round rather
        # than stalling it until the timer expires.
        se2, c2 = self._settle_disconnected()
        score_events.extend(se2)
        cues.extend(c2)
        if self.finished:
            return StateUpdate(
                state=self.get_state(),
                cues=cues,
                score_events=score_events,
                is_final=True,
            )

        elapsed_ms = int((time.monotonic() - self.round_started_at) * 1000)
        if elapsed_ms < self.current_question.time_limit_ms:
            # No timer expiry this tick. Still return whatever cues/score
            # events the disconnect settle produced (else they're lost
            # and the manager writes no snapshot for them).
            return StateUpdate(
                state=self.get_state(), cues=cues, score_events=score_events
            )

        # Time expired — lock in TIMEOUT for everyone who didn't pick.
        for puck in list(self.scores):
            if self.locked[puck] is None:
                self.selected[puck] = self.selected[puck]  # may still be None
                evs, lock_cues = self._lock_in(puck, forced_timeout=True)
                score_events.extend(evs)
                cues.extend(lock_cues)
        cues.extend(self._end_round_cues())
        self._advance_round()
        # Same flush as on_input — drain pending cues queued by
        # _advance_round so match_end / next round_start land in the
        # snapshot.
        if self._pending_cues:
            cues.extend(self._pending_cues)
            self._pending_cues = []

        return StateUpdate(
            state=self.get_state(),
            cues=cues,
            score_events=score_events,
            is_final=self.finished,
        )

    def on_puck_disconnected(self, puck_index: int) -> StateUpdate | None:
        """A silent puck would otherwise hang the round forever — the
        round only advances when every puck has locked in or the round
        timer elapses, and a disconnected puck never locks. Remember the
        disconnect and force-lock it as a TIMEOUT (0 points, same as the
        round-timer path) so this and every later round can resolve.
        """
        if self.finished or puck_index not in self.scores:
            return None
        if puck_index in self.disconnected:
            # Already retired — nothing new to do.
            return None
        self.disconnected.add(puck_index)

        score_events, cues = self._settle_disconnected()
        if not score_events and not cues:
            # Puck had already locked in this round; the disconnect is
            # remembered for later rounds but changes nothing right now.
            return None
        return StateUpdate(
            state=self.get_state(),
            cues=cues,
            score_events=score_events,
            is_final=self.finished,
        )

    def _settle_disconnected(self) -> tuple[list[ScoreEvent], list[CueEvent]]:
        """Force-lock every known-disconnected puck that hasn't committed
        the current round, advancing rounds as the locks complete them.
        Idempotent when no disconnected puck is pending. Terminates because
        rounds are finite and self.finished breaks the loop."""
        score_events: list[ScoreEvent] = []
        cues: list[CueEvent] = []
        if not self.disconnected:
            return score_events, cues
        progressed = True
        while progressed and not self.finished:
            progressed = False
            for puck in self.disconnected:
                if self.locked.get(puck) is not None:
                    continue
                evs, lock_cues = self._lock_in(puck, forced_timeout=True)
                score_events.extend(evs)
                cues.extend(lock_cues)
                progressed = True
                if self._all_locked():
                    cues.extend(self._end_round_cues())
                    self._advance_round()
                    # New round (or finish) — restart the scan so the
                    # disconnected pucks get re-locked for it.
                    break
        # Drain cues _advance_round queued (next round_start / match_end).
        if self._pending_cues:
            cues.extend(self._pending_cues)
            self._pending_cues = []
        return score_events, cues

    # === Durability ===

    def serialize(self) -> dict[str, Any]:
        # round_started_at is monotonic — persist it as an elapsed offset
        # and re-base on restore (monotonic doesn't survive a restart).
        round_elapsed_ms = (
            0
            if self.finished
            else int((time.monotonic() - self.round_started_at) * 1000)
        )
        return {
            "questions": [
                {
                    "id": q.id,
                    "setup": q.setup,
                    "question": q.question,
                    "answers": q.answers,
                    "correct": q.correct,
                    "category": q.category,
                    "time_limit_ms": q.time_limit_ms,
                }
                for q in self.questions
            ],
            "scores": {str(k): v for k, v in self.scores.items()},
            "round_index": self.round_index,
            "round_elapsed_ms": round_elapsed_ms,
            "selected": {str(k): v for k, v in self.selected.items()},
            "locked": {str(k): v for k, v in self.locked.items()},
            "disconnected": sorted(self.disconnected),
            "finished": self.finished,
        }

    @classmethod
    def deserialize(
        cls, players: list[Player], data: dict[str, Any]
    ) -> "SpeedPyramid":
        questions = [Question(**qd) for qd in data["questions"]]
        game = cls(players, questions=questions)
        game._pending_cues = []  # don't replay match_start/round_start
        game.scores = {int(k): v for k, v in data["scores"].items()}
        game.round_index = data["round_index"]
        game.selected = {int(k): v for k, v in data["selected"].items()}
        game.locked = {int(k): v for k, v in data["locked"].items()}
        game.disconnected = set(data["disconnected"])
        game.finished = data["finished"]
        game.round_started_at = (
            time.monotonic() - data["round_elapsed_ms"] / 1000.0
        )
        return game

    def is_over(self) -> bool:
        return self.finished

    def final_scores(self) -> dict[int, int]:
        return dict(self.scores)

    def get_state(self) -> dict[str, Any]:
        q = self.current_question if not self.finished else None
        return {
            "game_slug": self.slug,
            "round_number": self.round_index + 1,
            "total_rounds": len(self.questions),
            "round_elapsed_ms": int(
                (time.monotonic() - self.round_started_at) * 1000
            )
            if not self.finished
            else 0,
            "question": (
                {
                    "id": q.id,
                    "setup": q.setup,
                    "question": q.question,
                    "answers": q.answers,
                    "category": q.category,
                    "time_limit_ms": q.time_limit_ms,
                }
                if q is not None
                else None
            ),
            "selected": dict(self.selected),
            "locked": {k: v for k, v in self.locked.items() if v is not None},
            "scores": dict(self.scores),
            "finished": self.finished,
        }

    # === Internals ===

    @property
    def current_question(self) -> Question:
        return self.questions[self.round_index]

    def _lock_in(
        self, puck: int, forced_timeout: bool = False
    ) -> tuple[list[ScoreEvent], list[CueEvent]]:
        question = self.current_question
        elapsed_ms = int(
            (time.monotonic() - self.round_started_at) * 1000
        )
        if forced_timeout:
            elapsed_ms = max(elapsed_ms, question.time_limit_ms)

        chosen = self.selected[puck]
        is_correct = chosen is not None and chosen == question.correct

        if is_correct:
            tier = tier_for(elapsed_ms)
            points = points_for_tier(tier)
        else:
            tier = "WRONG" if chosen is not None else "TIMEOUT"
            points = 0

        self.scores[puck] += points
        self.locked[puck] = {
            "answer": chosen,
            "is_correct": is_correct,
            "tier": tier,
            "points": points,
            "response_time_ms": elapsed_ms,
        }

        cues: list[CueEvent] = []
        cues.append(
            CueEvent(
                cue=Cue.PLAYER_LOCKED_IN,
                target=puck,
                payload={"answer": chosen, "tier": tier, "points": points},
            )
        )
        if is_correct:
            tier_cue_name = TIER_CUE[tier]
            cues.append(cue_player_correct(puck, tier=tier, points=points))
            cues.append(CueEvent(cue=tier_cue_name, target=puck, payload={"points": points}))
        else:
            cues.append(cue_player_wrong(puck, tier=tier))

        score_events = [
            ScoreEvent(
                puck_index=puck,
                round_number=self.round_index + 1,
                score_delta=points,
                score_total=self.scores[puck],
                event_type="round",
            )
        ]
        return score_events, cues

    def _all_locked(self) -> bool:
        return all(v is not None for v in self.locked.values())

    def _end_round_cues(self) -> list[CueEvent]:
        return [
            CueEvent(
                cue=Cue.ROUND_END,
                payload={
                    "round_number": self.round_index + 1,
                    "correct_answer": self.current_question.correct,
                },
            )
        ]

    def _advance_round(self) -> None:
        self.round_index += 1
        if self.round_index >= len(self.questions):
            self.finished = True
            winner = max(self.scores.items(), key=lambda kv: kv[1])[0]
            self._pending_cues.append(cue_match_end(winner_index=winner))
            return
        # Reset round state.
        for puck in self.scores:
            self.selected[puck] = None
            self.locked[puck] = None
        self.round_started_at = time.monotonic()
        self._pending_cues.append(
            cue_round_start(
                round_number=self.round_index + 1,
                category=self.current_question.category,
            )
        )


# ============================================================================
# Registry hookup
# ============================================================================
# Importing this module registers the game. The package __init__ imports
# every game submodule so a single `import games` boots the registry.

registry.register(SpeedPyramid)
