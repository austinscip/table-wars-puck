"""
Match — one play-through of a Game. MatchManager owns the lifecycle
(create -> input/tick -> finalise) and persists every interesting state
change to Supabase via the SupabaseWriter.

The TV doesn't poll the manager; it subscribes to Supabase Realtime on
the match's row + its scores. That keeps the latency profile WebSocket-
shaped per Mike's "WebSockets, not POST/reply" advice without us
maintaining a Socket.IO server.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Protocol

from .game import Game, Player, InputEvent, ScoreEvent, StateUpdate
from .cues import Cue, CueEvent
from .heartbeat import HeartbeatTracker
from .idempotency import IdempotencyCache
from .log import get_logger
from .registry import GameRegistry

logger = get_logger("match")


class SupabaseWriterProtocol(Protocol):
    """The slice of SupabaseWriter the manager needs. Keeping it as a
    Protocol means tests can swap in a fake without touching network."""

    def create_match(
        self,
        location_id: str,
        game_slug: str,
        table_number: int,
        pucks: list[tuple[str, str, str | None]],
        snapshot: dict,
    ) -> tuple[str, list[str]]: ...

    def insert_score(
        self,
        match_id: str,
        match_puck_id: str,
        round_number: int,
        score_delta: int,
        score_total: int,
        event_type: str,
    ) -> None: ...

    def update_match_finished(
        self, match_id: str, ended_at: datetime
    ) -> None: ...

    def update_match_abandoned(
        self, match_id: str, ended_at: datetime
    ) -> None: ...

    def update_match_snapshot(
        self, match_id: str, snapshot: dict
    ) -> None: ...


class SchedulerProtocol(Protocol):
    """The slice of TickScheduler the manager calls into on lifecycle
    transitions. Optional dependency — manager works without it for
    tests and games that don't need a tick loop."""

    def register(self, match_id: str) -> None: ...

    def unregister(self, match_id: str) -> None: ...


@dataclass
class Match:
    id: str  # UUID matching Supabase matches.id
    location_id: str
    game_slug: str
    table_number: int
    players: list[Player]
    game: Game
    # puck_index -> match_pucks.id (UUID). Needed because scores
    # reference match_puck_id, not puck_id directly.
    match_puck_ids: dict[int, str] = field(default_factory=dict)
    status: str = "active"
    started_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    ended_at: Optional[datetime] = None
    # Monotonic timestamp of the last input we processed. Seeded at
    # create so a match that never sees input is still measured from
    # creation for the abandoned-match sweep.
    last_input_at: float = field(default_factory=time.monotonic)
    # Per-match monotonic counter stamped onto every cue as it's written
    # to a snapshot. The TV dedupes cues on this strictly-increasing seq
    # instead of a wall-clock ts (which NTP/restart can run backwards).
    cue_seq: int = 0


class MatchManager:
    """Owns active matches in memory and writes every state-changing
    event to Supabase. Single-process for now; if we shard across
    workers, store match state in Redis and lock per match_id."""

    # A match with no input AND every puck stale for this long is treated
    # as abandoned (everyone left). Must comfortably exceed the heartbeat
    # stale threshold so a brief Wi-Fi blip never abandons a live table.
    ABANDON_AFTER_S = 120.0

    def __init__(
        self,
        registry: GameRegistry,
        writer: SupabaseWriterProtocol,
        scheduler: Optional[SchedulerProtocol] = None,
        heartbeat: Optional[HeartbeatTracker] = None,
        idempotency: Optional[IdempotencyCache] = None,
        abandon_after_s: Optional[float] = None,
    ) -> None:
        self.registry = registry
        self.writer = writer
        self.scheduler = scheduler
        # One tracker shared across all matches. Each tick sweeps just
        # the current match. If unset (tests, minimal envs), heartbeat
        # logic is skipped entirely.
        self.heartbeat = heartbeat
        # Dedupes retried puck requests. If unset, idempotency is a no-op
        # (every request processed) — fine for tests that don't exercise
        # retries.
        self.idempotency = idempotency
        self.abandon_after_s = (
            abandon_after_s if abandon_after_s is not None else self.ABANDON_AFTER_S
        )
        self.matches: dict[str, Match] = {}

    # === Create ===

    def create(
        self,
        location_id: str,
        game_slug: str,
        table_number: int,
        players: list[Player],
        **game_options,
    ) -> Match:
        game_class = self.registry.get(game_slug)
        n = len(players)
        if not (game_class.min_players <= n <= game_class.max_players):
            raise ValueError(
                f"{game_slug} requires "
                f"{game_class.min_players}-{game_class.max_players} players, "
                f"got {n}"
            )

        # Build the game first so its initial state seeds the snapshot in
        # the SAME transaction as the match + puck rows. A game
        # constructor that rejects its options raises here, before any DB
        # write — no half-created match.
        game = game_class(players=players, **game_options)

        pucks = [
            (p.puck_uuid, "host" if i == 0 else "sibling", p.name)
            for i, p in enumerate(players)
        ]
        # One transaction: matches + match_pucks×N + seed snapshot. If it
        # raises, nothing below runs and the match is never registered —
        # the manager's in-memory state stays consistent with the DB.
        match_id, mp_ids = self.writer.create_match(
            location_id=location_id,
            game_slug=game_slug,
            table_number=table_number,
            pucks=pucks,
            snapshot=game.get_state(),
        )
        match_puck_ids = {
            p.puck_index: mp_ids[i] for i, p in enumerate(players)
        }

        match = Match(
            id=match_id,
            location_id=location_id,
            game_slug=game_slug,
            table_number=table_number,
            players=players,
            game=game,
            match_puck_ids=match_puck_ids,
        )
        self.matches[match_id] = match

        # Seed heartbeat last_seen for every puck so the first sweep
        # doesn't immediately mark them stale.
        if self.heartbeat is not None:
            self.heartbeat.register(
                match_id, [p.puck_index for p in players]
            )

        if self.scheduler is not None:
            self.scheduler.register(match_id)
        logger.info(
            "match %s created: game=%s table=%s players=%d",
            match_id,
            game_slug,
            table_number,
            len(players),
        )
        return match

    # === Drive ===

    def on_input(
        self,
        match_id: str,
        event: InputEvent,
        event_id: Optional[str] = None,
    ) -> StateUpdate:
        match = self._must_get(match_id)

        # Idempotency: a retried request (same logical event_id from the
        # same puck in the same match) replays the first response without
        # re-applying the input. Checked before the status guard so a
        # retry that arrives after the match finished still gets the
        # original result, not a stale snapshot.
        key: Optional[str] = None
        if event_id is not None and self.idempotency is not None:
            key = f"{match_id}:{event.puck_index}:{event_id}"
            cached = self.idempotency.get(key)
            if cached is not None:
                return cached

        if match.status != "active":
            return StateUpdate(state=match.game.get_state())

        match.last_input_at = time.monotonic()
        if self.heartbeat is not None:
            self.heartbeat.ping(match_id, event.puck_index)

        update = match.game.on_input(event)
        self._persist_scores(match, update.score_events)
        # Always write a snapshot on input — every input is, by
        # definition, something the player did that the TV should react
        # to.
        self.writer.update_match_snapshot(
            match_id, self._snapshot_payload(match, update)
        )
        if update.is_final or match.game.is_over():
            self._finalize(match)
        if key is not None:
            self.idempotency.put(key, update)
        return update

    def tick(self, match_id: str) -> StateUpdate:
        match = self._must_get(match_id)
        if match.status != "active":
            return StateUpdate(state=match.game.get_state())

        update = match.game.tick()

        # Heartbeat sweep — any puck that hasn't pinged in
        # STALE_THRESHOLD_S gets a PLAYER_LEFT cue appended to this
        # update. Exactly once per disconnect; re-pings clear the flag.
        # The game then gets a chance to react (force-lock, pass turn,
        # eliminate) so the match doesn't hang on a silent puck. The
        # reaction's cues/score_events/state fold into this same update
        # so one tick both detects and resolves the disconnect.
        if self.heartbeat is not None:
            stale = self.heartbeat.sweep(match_id)
            for puck_index in sorted(stale):
                update.cues.append(
                    CueEvent(
                        cue=Cue.PLAYER_LEFT,
                        target=puck_index,
                        payload={"reason": "heartbeat_timeout"},
                    )
                )
                reaction = match.game.on_puck_disconnected(puck_index)
                if reaction is not None:
                    update.cues.extend(reaction.cues)
                    update.score_events.extend(reaction.score_events)
                    # The reaction mutated game state; adopt its fresh
                    # snapshot so the row the TV reads reflects the
                    # post-disconnect state, not the pre-sweep tick.
                    update.state = reaction.state
                    if reaction.is_final:
                        update.is_final = True

        # Persist score events after the sweep so a disconnect reaction's
        # scores (e.g. SpeedPyramid's forced-TIMEOUT round score) land in
        # the same write path as the tick's own scores.
        self._persist_scores(match, update.score_events)

        # Only persist snapshot on tick if the tick produced score
        # events, fired cues, or finalised the match. Otherwise 10 Hz
        # ticks would spam the matches row with no state change.
        if update.score_events or update.cues or update.is_final:
            self.writer.update_match_snapshot(
                match_id, self._snapshot_payload(match, update)
            )
        if update.is_final or match.game.is_over():
            self._finalize(match)
        elif self._is_abandoned(match):
            # No natural end and the table's gone quiet — close it out as
            # abandoned so it doesn't sit 'active' forever. Checked after
            # finalisation so a game that ends itself wins the race.
            self._abandon(match)
        return update

    # === Finalise ===

    def _finalize(self, match: Match) -> None:
        if match.status == "finished":
            return
        match.status = "finished"
        match.ended_at = datetime.now(timezone.utc)

        finals = match.game.final_scores()
        for puck_index, total in finals.items():
            mp_id = match.match_puck_ids.get(puck_index)
            if mp_id is None:
                # Puck wasn't in the lobby — final score has nowhere to
                # land. Skip silently rather than fail the whole finish.
                continue
            self.writer.insert_score(
                match_id=match.id,
                match_puck_id=mp_id,
                round_number=0,
                score_delta=0,
                score_total=total,
                event_type="final",
            )
        self.writer.update_match_finished(
            match_id=match.id, ended_at=match.ended_at
        )
        if self.scheduler is not None:
            self.scheduler.unregister(match.id)
        if self.heartbeat is not None:
            self.heartbeat.drop_match(match.id)
        logger.info("match %s finished", match.id)

    def _is_abandoned(self, match: Match) -> bool:
        """A still-active match is abandoned when every puck has gone
        stale AND no input has landed for abandon_after_s. The input-age
        gate (on top of all-stale) keeps a match that's merely between
        turns from being reaped."""
        if self.heartbeat is None:
            return False
        if not self.heartbeat.all_stale(match.id):
            return False
        return (time.monotonic() - match.last_input_at) >= self.abandon_after_s

    def _abandon(self, match: Match) -> None:
        if match.status != "active":
            return
        match.status = "abandoned"
        match.ended_at = datetime.now(timezone.utc)
        self.writer.update_match_abandoned(
            match_id=match.id, ended_at=match.ended_at
        )
        if self.scheduler is not None:
            self.scheduler.unregister(match.id)
        if self.heartbeat is not None:
            self.heartbeat.drop_match(match.id)
        logger.info("match %s abandoned (all pucks stale, no input)", match.id)

    # === Internals ===

    def _persist_scores(self, match: Match, events: list[ScoreEvent]) -> None:
        for se in events:
            mp_id = match.match_puck_ids.get(se.puck_index)
            if mp_id is None:
                continue
            self.writer.insert_score(
                match_id=match.id,
                match_puck_id=mp_id,
                round_number=se.round_number,
                score_delta=se.score_delta,
                score_total=se.score_total,
                event_type=se.event_type,
            )

    def _must_get(self, match_id: str) -> Match:
        if match_id not in self.matches:
            raise KeyError(f"Match {match_id} not found")
        return self.matches[match_id]

    def _snapshot_payload(self, match: Match, update: StateUpdate) -> dict:
        """Merge game state with any cues fired this update. Each cue is
        stamped with a per-match monotonic `seq` so the TV can dedupe on
        a strictly-increasing integer rather than a wall-clock `ts` (which
        an NTP adjustment or container restart can run backwards, sticking
        the TV's watermark and dropping every later cue).

        Cues are ephemeral — they don't accumulate in the snapshot across
        updates because each write replaces the column. The seq is what
        lets the TV tell a genuinely new cue from a redelivered one."""
        payload = dict(update.state)
        if update.cues:
            cue_dicts = []
            for cue in update.cues:
                d = cue.to_dict()
                d["seq"] = match.cue_seq
                match.cue_seq += 1
                cue_dicts.append(d)
            payload["cues"] = cue_dicts
        return payload
