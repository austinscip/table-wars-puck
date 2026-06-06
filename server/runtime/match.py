"""
Match — one play-through of a Game. MatchManager owns the lifecycle
(create -> input/tick -> finalise) and persists every interesting state
change to Supabase via the SupabaseWriter.

The TV renders gameplay local-first (ADR 0004): the manager pushes each
state change to the venue's TV over a LAN Flask-SocketIO connection via an
injected, transport-agnostic `state_sink` (so this module stays free of any
Flask-SocketIO import). The cloud snapshot/score writes are demoted to an
asynchronous persistence/analytics sink + a cold-standby fallback the TV
reads only when the local socket is down. Every snapshot carries a
monotonic `snapshot_seq` so the TV never renders an older frame on failover.
"""

from __future__ import annotations

import functools
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Protocol

from .game import (
    DEFAULT_TICK_DT,
    Game,
    Player,
    InputEvent,
    ScoreEvent,
    StateUpdate,
)
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


class StateSink(Protocol):
    """The local push transport the manager emits each state change to
    (ADR 0004). The app wires this to a Flask-SocketIO room emit; tests
    inject a fake that records envelopes. Implementations MUST NOT raise —
    a transport hiccup must never break gameplay (the manager guards the
    call regardless)."""

    def __call__(self, envelope: dict) -> None: ...


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
    # Monotonic time the match went terminal (finished/abandoned), or None
    # while live. The reaper evicts terminal matches from MatchManager.matches
    # after a grace window (audit 1.3); None means "don't reap".
    terminal_at: Optional[float] = None
    # Per-match monotonic counter stamped onto every *snapshot* (one per
    # state-changing write), distinct from the per-cue cue_seq. Carried on
    # both the local SocketIO emit and the cloud snapshot write so the TV's
    # source-selector (local-primary, cloud-fallback) never renders an
    # older frame over a newer one on failover. See ADR 0004.
    snapshot_seq: int = 0


def serialize_match(match: "Match") -> dict:
    """Full persistable snapshot of a Match (incl. the game's own state).
    Monotonic `last_input_at` is stored as an elapsed offset and re-based
    on deserialize, since monotonic doesn't survive a restart."""
    return {
        "id": match.id,
        "location_id": match.location_id,
        "game_slug": match.game_slug,
        "table_number": match.table_number,
        "status": match.status,
        "started_at": match.started_at.isoformat(),
        "ended_at": match.ended_at.isoformat() if match.ended_at else None,
        "cue_seq": match.cue_seq,
        "snapshot_seq": match.snapshot_seq,
        "last_input_elapsed_s": time.monotonic() - match.last_input_at,
        "match_puck_ids": {str(k): v for k, v in match.match_puck_ids.items()},
        "players": [
            {
                "puck_uuid": p.puck_uuid,
                "puck_index": p.puck_index,
                "name": p.name,
                "color": p.color,
                "is_active": p.is_active,
            }
            for p in match.players
        ],
        "game": match.game.serialize(),
    }


def deserialize_match(data: dict, registry: GameRegistry) -> "Match":
    """Rebuild a Match (and its live game) from a serialize_match() dict."""
    players = [Player(**pd) for pd in data["players"]]
    game_class = registry.get(data["game_slug"])
    game = game_class.deserialize(players, data["game"])
    ended = data["ended_at"]
    return Match(
        id=data["id"],
        location_id=data["location_id"],
        game_slug=data["game_slug"],
        table_number=data["table_number"],
        players=players,
        game=game,
        match_puck_ids={int(k): v for k, v in data["match_puck_ids"].items()},
        status=data["status"],
        started_at=datetime.fromisoformat(data["started_at"]),
        ended_at=datetime.fromisoformat(ended) if ended else None,
        last_input_at=time.monotonic() - data["last_input_elapsed_s"],
        cue_seq=data["cue_seq"],
        # Tolerate snapshots written before snapshot_seq existed: a missing
        # key recovers as 0 rather than KeyError-ing the whole match.
        snapshot_seq=data.get("snapshot_seq", 0),
    )


class MatchManager:
    """Owns active matches in memory and writes every state-changing
    event to Supabase. A serializable game's full state can also be
    persisted to a `store` so a match survives a restart and can be shared
    across workers (see runtime/CONTEXT.md)."""

    # A match with no input AND every puck stale for this long is treated
    # as abandoned (everyone left). Must comfortably exceed the heartbeat
    # stale threshold so a brief Wi-Fi blip never abandons a live table.
    ABANDON_AFTER_S = 120.0

    # Hard wall-clock ceiling on an active match. A wedged game (a stuck
    # state machine that never reaches is_over, kept alive by one live-but-
    # idle puck so the all-stale abandon gate never trips) would otherwise
    # tick at 10 Hz forever. No real match approaches an hour, so this is a
    # pure backstop (audit runtime-games-2026-06-06). Survives a restart
    # because it's measured off the persisted wall-clock started_at.
    MAX_MATCH_DURATION_S = 3600.0

    # How long a terminal (finished/abandoned) match lingers in `matches`
    # before the reaper evicts it (audit 1.3). Long enough that late
    # idempotent retries + the TV's final-frame fetch still resolve.
    REAP_GRACE_S = 300.0

    def __init__(
        self,
        registry: GameRegistry,
        writer: SupabaseWriterProtocol,
        scheduler: Optional[SchedulerProtocol] = None,
        heartbeat: Optional[HeartbeatTracker] = None,
        idempotency: Optional[IdempotencyCache] = None,
        abandon_after_s: Optional[float] = None,
        store=None,
        lock_provider=None,
        state_sink: Optional["StateSink"] = None,
        reap_grace_s: Optional[float] = None,
        on_match_reaped=None,
    ) -> None:
        self.registry = registry
        self.writer = writer
        self.scheduler = scheduler
        self.reap_grace_s = (
            reap_grace_s if reap_grace_s is not None else self.REAP_GRACE_S
        )
        # Optional callback fired when a terminal match is evicted, with the
        # match_id — the container uses it to drop that match's rate-limiter
        # buckets so they don't leak (audit 1.4).
        self.on_match_reaped = on_match_reaped
        # Optional transport-agnostic push sink. When set, the manager calls
        # state_sink(envelope) on every state-changing input/tick — OUTSIDE
        # the per-match lock — so the TV gets the frame over the LAN socket
        # without the runtime importing Flask-SocketIO. Default None = no
        # local push (tests, cloud-only fallback). See ADR 0004.
        self.state_sink = state_sink
        # Optional distributed lock provider (e.g. RedisLock) exposing
        # lock_for(match_id) -> context manager. When set, it replaces the
        # in-process per-match RLock — the seam for cross-worker mutual
        # exclusion. NOTE: a distributed lock alone is not enough for
        # multi-worker correctness (state, heartbeat, and a single ticker
        # are also required); see runtime/CONTEXT.md.
        self.lock_provider = lock_provider
        # Optional durable match store (InMemoryMatchStore / RedisMatchStore).
        # When set, serializable games are persisted on every state change
        # so a restart recovers active matches. Non-serializable games are
        # skipped silently.
        self.store = store
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
        # One reentrant lock per match, serialising every mutation of that
        # match's state. The scheduler thread (tick) and Flask request
        # threads (on_input) both touch a match's game object; without
        # this they race on game internals AND on the idempotency
        # check-then-act. Reentrant so finalize/abandon (called from
        # inside a locked on_input/tick) don't deadlock. This is the seam
        # that becomes a Redis per-match lock when state moves out of
        # process (see runtime/CONTEXT.md).
        self._match_locks: dict[str, threading.RLock] = {}
        self._match_locks_guard = threading.Lock()

    def _lock_for(self, match_id: str) -> threading.RLock:
        with self._match_locks_guard:
            lock = self._match_locks.get(match_id)
            if lock is None:
                lock = threading.RLock()
                self._match_locks[match_id] = lock
            return lock

    def _lock_cm(self, match_id: str):
        """The per-match critical-section lock as a context manager — the
        injected distributed lock if one is configured, otherwise the
        in-process reentrant lock."""
        if self.lock_provider is not None:
            return self.lock_provider.lock_for(match_id)
        return self._lock_for(match_id)

    def _drop_lock(self, match_id: str) -> None:
        """Release the per-match lock entry once a match is terminal so
        the map doesn't grow without bound. Safe: a late request for a
        finished match just makes a fresh lock and hits the status guard."""
        with self._match_locks_guard:
            self._match_locks.pop(match_id, None)

    def _persist(self, match: Match) -> None:
        """Save the match to the durable store if one is configured and the
        game supports serialization. Best-effort — a store hiccup must not
        break gameplay."""
        if self.store is None or not getattr(match.game, "serializable", False):
            return
        try:
            data = serialize_match(match)
            # Persist heartbeat state too (audit 1.8) so recovery keeps
            # exactly-once disconnect semantics across a restart.
            if self.heartbeat is not None:
                data["heartbeat"] = self.heartbeat.export(match.id)
            self.store.save(match.id, data)
        except Exception:  # noqa: BLE001
            logger.exception("failed to persist match %s", match.id)

    def recover(self) -> list[str]:
        """Rebuild active matches from the store on boot (restart recovery).
        Returns the ids recovered. Finished/abandoned rows are dropped from
        the store rather than re-loaded."""
        if self.store is None:
            return []
        recovered: list[str] = []
        for match_id in self.store.load_all_ids():
            data = self.store.load(match_id)
            if not data:
                continue
            if data.get("status") != "active":
                self.store.delete(match_id)
                continue
            try:
                match = deserialize_match(data, self.registry)
            except Exception:  # noqa: BLE001
                logger.exception("failed to recover match %s; dropping", match_id)
                self.store.delete(match_id)
                continue
            self.matches[match.id] = match
            if self.heartbeat is not None:
                self.heartbeat.register(
                    match.id, [p.puck_index for p in match.players]
                )
                # Restore the persisted heartbeat state (last_seen offsets +
                # stale_emitted) so a puck that already disconnected pre-crash
                # doesn't re-fire its PLAYER_LEFT cue on boot (audit 1.8).
                hb = data.get("heartbeat")
                if hb:
                    self.heartbeat.restore(match.id, hb)
            if self.scheduler is not None:
                self.scheduler.register(match.id)
            recovered.append(match.id)
            logger.info("recovered match %s (%s)", match.id, match.game_slug)
        return recovered

    def reap_terminal(self) -> int:
        """Evict terminal (finished/abandoned) matches whose grace window has
        elapsed, so `matches` doesn't grow without bound over a long-running
        box (audit 1.3). Fires on_match_reaped per eviction (rate-limiter
        cleanup, audit 1.4). Returns the number reaped. Cheap + called from
        the scheduler loop; safe against a concurrent insert (skips a sweep
        if the dict resizes under us)."""
        now = time.monotonic()
        try:
            items = list(self.matches.items())
        except RuntimeError:
            return 0  # dict changed size mid-iteration; reap next sweep
        reaped = 0
        for match_id, match in items:
            if (
                match.terminal_at is not None
                and (now - match.terminal_at) > self.reap_grace_s
            ):
                self.matches.pop(match_id, None)
                reaped += 1
                if self.on_match_reaped is not None:
                    try:
                        self.on_match_reaped(match_id)
                    except Exception:  # noqa: BLE001
                        logger.exception(
                            "on_match_reaped failed for %s", match_id
                        )
                logger.info("reaped terminal match %s", match_id)
        return reaped

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

        # puck_index must be unique — it keys match_puck_ids, scoring, and
        # all game state. A duplicate would silently collapse two players
        # into one. Pairing guarantees uniqueness today; this guard makes
        # it impossible for any caller to bypass before a DB write lands.
        indices = [p.puck_index for p in players]
        if len(set(indices)) != len(indices):
            raise ValueError(f"duplicate puck_index in players: {indices}")

        # Build the game first so its initial state seeds the snapshot in
        # the SAME transaction as the match + puck rows. A game constructor
        # that rejects its options raises here, before any DB write — no
        # half-created match. Wrap any constructor error as a clear
        # ValueError so a bad game_option surfaces as a 4xx, not an opaque
        # 500 (audit 2.7).
        try:
            game = game_class(players=players, **game_options)
        except ValueError:
            raise
        except Exception as e:  # noqa: BLE001
            raise ValueError(
                f"invalid options for game {game_slug!r}: {e}"
            ) from e

        pucks: list[tuple[str, str, Optional[str]]] = [
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
        self._persist(match)
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
        with self._lock_cm(match_id):
            update, payload, deferred = self._on_input_locked(
                match, match_id, event, event_id
            )
        # Push to the local TV sink AND run the durable match-end writes
        # OUTSIDE the lock — never hold the per-match lock across a socket
        # write or a synchronous Supabase round-trip (ADR 0004, audit 1.5).
        self._emit(match, payload)
        self._run_deferred(deferred, match_id)
        return update

    def _on_input_locked(
        self,
        match: Match,
        match_id: str,
        event: InputEvent,
        event_id: Optional[str],
    ) -> tuple[StateUpdate, Optional[dict], list]:
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
                # Replay the original response. We cache the JSON-able
                # state dict (not the StateUpdate object) so the same code
                # path works whether the cache is in-process or Redis-
                # backed. The side effects (scores, snapshot) already
                # happened on the first arrival; a replay re-emits no cues
                # or score events — and no local frame (payload None).
                return StateUpdate(state=cached), None, []

        if match.status != "active":
            return StateUpdate(state=self._safe_state(match)), None, []

        match.last_input_at = time.monotonic()
        reconnected = False
        if self.heartbeat is not None:
            reconnected = self.heartbeat.ping(match_id, event.puck_index)

        # A puck that was swept stale and is now talking again is a RECONNECT.
        # Un-retire it BEFORE processing its input so the input applies to the
        # restored state (audit runtime-games-2026-06-06). Contained like
        # on_input — a buggy reconnect hook must not wedge the match.
        reconnect_reaction = None
        if reconnected:
            try:
                reconnect_reaction = match.game.on_puck_reconnected(
                    event.puck_index
                )
            except Exception:  # noqa: BLE001
                logger.exception(
                    "game.on_puck_reconnected raised (match=%s puck=%s)",
                    match_id,
                    event.puck_index,
                )

        # Contain a buggy game: an exception in on_input must not 500 the
        # request thread or leave the match wedged (the scheduler already
        # guards the tick path; this is the input-path equivalent — audit
        # 0.3). We drop the offending frame and return the last good state.
        try:
            update = match.game.on_input(event)
        except Exception:  # noqa: BLE001
            logger.exception(
                "game.on_input raised (match=%s puck=%s); dropping frame",
                match_id,
                event.puck_index,
            )
            # The reconnect reaction (if any) already mutated game state, so
            # surface ITS snapshot + cues rather than a bare safe-state — else
            # the un-retire happened silently with no PLAYER_JOINED beat and no
            # snapshot until the next input (self-review).
            if reconnect_reaction is not None:
                return reconnect_reaction, None, []
            return StateUpdate(state=self._safe_state(match)), None, []

        # Fold the reconnect reaction's cues/scores ahead of the input's so
        # the PLAYER_JOINED beat precedes anything the input produced; the
        # input update already carries the post-reconnect state snapshot.
        if reconnect_reaction is not None:
            update.cues = reconnect_reaction.cues + update.cues
            update.score_events = (
                reconnect_reaction.score_events + update.score_events
            )
            if reconnect_reaction.is_final:
                update.is_final = True
        self._persist_scores(match, update.score_events)
        # Always write a snapshot on input — every input is, by
        # definition, something the player did that the TV should react
        # to. The same payload is emitted to the local sink (outside the
        # lock, by the caller) so local and cloud carry the same seq.
        payload = self._snapshot_payload(match, update)
        self.writer.update_match_snapshot(match_id, payload)
        deferred: list = []
        if update.is_final or match.game.is_over():
            deferred = self._finalize(match)
        else:
            self._persist(match)
        if key is not None and self.idempotency is not None:
            # Store the JSON-able response state for replay (see the get
            # path above). A Redis cache serialises this directly.
            self.idempotency.put(key, update.state)
        return update, payload, deferred

    def tick(
        self, match_id: str, dt: float = DEFAULT_TICK_DT
    ) -> StateUpdate:
        """Advance one tick. `dt` is the real elapsed seconds since the last
        tick — the live scheduler measures and passes it so timed games run
        at wall-clock speed even when the box can't hold 10 Hz (gap #5b).
        Defaults to the nominal step so synthetic test ticks are deterministic."""
        match = self._must_get(match_id)
        with self._lock_cm(match_id):
            update, payload, deferred = self._tick_locked(match, match_id, dt)
        # Push to the local TV sink + run match-end writes OUTSIDE the lock
        # (ADR 0004, audit 1.5). payload is None on a no-op tick (no state
        # change), so quiet ticks emit nothing — volume tracks real change.
        self._emit(match, payload)
        self._run_deferred(deferred, match_id)
        return update

    def _tick_locked(
        self, match: Match, match_id: str, dt: float = DEFAULT_TICK_DT
    ) -> tuple[StateUpdate, Optional[dict], list]:
        if match.status != "active":
            return StateUpdate(state=self._safe_state(match)), None, []

        # Floor dt at 0 — the live scheduler already clamps, but a direct
        # caller must never run a timed game's physics/clock BACKWARD
        # (audit runtime-games-2026-06-06). One clamp here protects every game.
        dt = max(0.0, dt)
        try:
            update = match.game.tick(dt)
        except Exception:  # noqa: BLE001
            # Defense in depth: the scheduler already logs+continues on a
            # tick exception, but containing it here keeps the public tick()
            # (and any direct caller) safe too.
            logger.exception("game.tick raised (match=%s); skipping", match_id)
            return StateUpdate(state=self._safe_state(match)), None, []

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

        # Only persist + emit a snapshot on tick if the tick produced score
        # events, fired cues, or finalised the match. Otherwise 10 Hz
        # ticks would spam the matches row (and the socket) with no state
        # change. payload stays None on a quiet tick so the caller emits
        # nothing.
        payload: Optional[dict] = None
        if update.score_events or update.cues or update.is_final:
            payload = self._snapshot_payload(match, update)
            self.writer.update_match_snapshot(match_id, payload)
        deferred: list = []
        if update.is_final or match.game.is_over():
            deferred = self._finalize(match)
        elif self._is_abandoned(match):
            # No natural end and the table's gone quiet — close it out as
            # abandoned so it doesn't sit 'active' forever. Checked after
            # finalisation so a game that ends itself wins the race.
            deferred = self._abandon(match)
        elif update.score_events or update.cues:
            # State changed this tick — persist the durable snapshot.
            self._persist(match)
        return update, payload, deferred

    # === Finalise ===

    def _run_deferred(self, deferred: list, match_id: str) -> None:
        """Run the durable match-end writes returned by _finalize/_abandon,
        OUTSIDE the per-match lock (audit 1.5). The match is already terminal
        in memory; a cloud failure here is logged, not raised at the puck
        (the writer's own bounded retry handles transient blips)."""
        for write in deferred:
            try:
                write()
            except Exception:  # noqa: BLE001
                logger.exception(
                    "deferred match-end write failed (match=%s)", match_id
                )

    def _finalize(self, match: Match) -> list:
        """In-memory finalise transition under the lock; RETURNS the durable
        Supabase writes (final scores + finished) for the caller to run
        outside the lock, so a slow write at match-end never holds it."""
        if match.status == "finished":
            return []
        match.status = "finished"
        match.ended_at = datetime.now(timezone.utc)

        deferred: list = []
        finals = match.game.final_scores()
        for puck_index, total in finals.items():
            mp_id = match.match_puck_ids.get(puck_index)
            if mp_id is None:
                # Puck wasn't in the lobby — final score has nowhere to land.
                logger.warning(
                    "final score for unknown puck_index %s in match %s; "
                    "dropped",
                    puck_index,
                    match.id,
                )
                continue
            deferred.append(
                functools.partial(
                    self.writer.insert_score,
                    match_id=match.id,
                    match_puck_id=mp_id,
                    round_number=0,
                    score_delta=0,
                    score_total=total,
                    event_type="final",
                )
            )
        deferred.append(
            functools.partial(
                self.writer.update_match_finished,
                match_id=match.id,
                ended_at=match.ended_at,
            )
        )
        if self.scheduler is not None:
            self.scheduler.unregister(match.id)
        if self.heartbeat is not None:
            self.heartbeat.drop_match(match.id)
        match.terminal_at = time.monotonic()
        self._drop_lock(match.id)
        if self.store is not None:
            self.store.delete(match.id)
        logger.info("match %s finished", match.id)
        return deferred

    def _is_abandoned(self, match: Match) -> bool:
        """A still-active match is abandoned when every puck has gone
        stale AND no input has landed for abandon_after_s. The input-age
        gate (on top of all-stale) keeps a match that's merely between
        turns from being reaped."""
        # Hard ceiling first: a match running absurdly long is force-closed
        # regardless of liveness, so a wedged state machine + one idle-but-
        # pinging puck can't keep it 'active' forever (audit
        # runtime-games-2026-06-06).
        age_s = (datetime.now(timezone.utc) - match.started_at).total_seconds()
        if age_s >= self.MAX_MATCH_DURATION_S:
            return True
        if self.heartbeat is None:
            return False
        if not self.heartbeat.all_stale(match.id):
            return False
        return (time.monotonic() - match.last_input_at) >= self.abandon_after_s

    def _abandon(self, match: Match) -> list:
        """In-memory abandon transition; RETURNS the durable write for the
        caller to run outside the lock (audit 1.5)."""
        if match.status != "active":
            return []
        match.status = "abandoned"
        match.ended_at = datetime.now(timezone.utc)
        deferred: list = [
            functools.partial(
                self.writer.update_match_abandoned,
                match_id=match.id,
                ended_at=match.ended_at,
            )
        ]
        if self.scheduler is not None:
            self.scheduler.unregister(match.id)
        if self.heartbeat is not None:
            self.heartbeat.drop_match(match.id)
        match.terminal_at = time.monotonic()
        self._drop_lock(match.id)
        if self.store is not None:
            self.store.delete(match.id)
        logger.info("match %s abandoned (all pucks stale, no input)", match.id)
        return deferred

    # === Internals ===

    def _safe_state(self, match: Match) -> dict:
        """get_state() that can't crash the caller — a game whose get_state
        raises returns an empty dict (logged) rather than propagating."""
        try:
            return match.game.get_state()
        except Exception:  # noqa: BLE001
            logger.exception("game.get_state raised (match=%s)", match.id)
            return {}

    def _persist_scores(self, match: Match, events: list[ScoreEvent]) -> None:
        for se in events:
            mp_id = match.match_puck_ids.get(se.puck_index)
            if mp_id is None:
                # A game emitted a score for a puck not in this match — a
                # real game bug. Surface it instead of silently dropping
                # (audit 2.10 observability).
                logger.warning(
                    "score for unknown puck_index %s in match %s; dropped",
                    se.puck_index,
                    match.id,
                )
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
        lets the TV tell a genuinely new cue from a redelivered one.

        The whole payload also carries a match-level `snapshot_seq` (one per
        write, distinct from the per-cue seq). The TV reconciles local vs
        cloud frames on it, so it MUST be stamped here — the single point
        every snapshot flows through — to guarantee local and cloud carry
        the same seq for the same frame (ADR 0004)."""
        payload = dict(update.state)
        if update.cues:
            cue_dicts = []
            for cue in update.cues:
                d = cue.to_dict()
                d["seq"] = match.cue_seq
                match.cue_seq += 1
                cue_dicts.append(d)
            payload["cues"] = cue_dicts
        payload["snapshot_seq"] = match.snapshot_seq
        match.snapshot_seq += 1
        return payload

    def _emit_envelope(self, match: Match, payload: dict) -> dict:
        """Wrap a snapshot payload in the local-push envelope the TV's
        socket handler consumes. Symmetrical with the cloud shape — cloud
        gives {status (column), snapshot (jsonb)}; this gives the same —
        so the TV normalises both to {status, snapshot, seq} trivially. The
        seq lives inside `snapshot` in both paths."""
        return {
            "match_id": match.id,
            "status": match.status,
            "snapshot": payload,
        }

    def _emit(self, match: Match, payload: Optional[dict]) -> None:
        """Push a frame to the local TV sink, OUTSIDE the per-match lock.
        Guarded: a transport failure must never break gameplay — the cloud
        snapshot write already carries the same frame for persistence and
        the fallback path."""
        if self.state_sink is None or payload is None:
            return
        try:
            self.state_sink(self._emit_envelope(match, payload))
        except Exception:  # noqa: BLE001
            logger.exception("state_sink emit failed for match %s", match.id)
