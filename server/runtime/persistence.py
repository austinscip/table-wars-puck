"""
PersistenceQueue — decouples the tick loop from cloud I/O (ADR 0004).

The MatchManager used to write every snapshot and score to Supabase
*synchronously, inside the per-match lock*. For a real-time game at 10 Hz
that put a cloud round-trip on the tick's critical path (and serialised
input behind the lock). The fix routes Supabase writes by traffic class:

- Snapshots — high-frequency, reconstructable, latest-wins. Coalesced into
  one slot per match and drained on a background thread. Best-effort:
  intermediate frames may be dropped; only freshness matters (the cloud
  copy is a fallback the TV reads when the LAN socket is down).
- Round scores — analytics only (the leaderboards trigger ignores
  'round'), so loss-tolerant. Best-effort FIFO, drained on the same thread.
- Finals, lifecycle (finished/abandoned), and create_match — leaderboard
  truth + transactional create. SYNCHRONOUS with bounded retry. They fire
  once per match (or at create), off the 10 Hz hot path, so a synchronous
  write costs no gameplay latency while keeping the strong
  "persisted-before-return" guarantee. Nothing durable ever sits unacked in
  the async queue.

This class implements SupabaseWriterProtocol so the MatchManager calls it
transparently (manager code is unchanged) — wrap the real writer at the
container: writer = PersistenceQueue(SupabaseWriter.with_pool()).

Threading/gevent: the drain thread is a plain threading.Thread. Under the
prod GeventWebSocketWorker it becomes a cooperative greenlet (monkey-patched
before import); its Event.wait yields the hub. Single-process — no shared
queue needed. Coalescing is the dominant win: the hub pays at most one
snapshot write per match per drain interval instead of one per state change.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from datetime import datetime
from typing import Optional

from .log import get_logger

logger = get_logger("persistence")


class PersistenceQueue:
    # How often the background thread flushes the async lanes.
    DRAIN_INTERVAL_S = 0.25
    # Bound the best-effort round-score backlog so a prolonged cloud outage
    # can't grow it without limit; oldest are dropped (and logged) first.
    MAX_ROUND_BACKLOG = 5_000
    # Cap accumulated cues on a coalesced snapshot. State coalesces
    # latest-wins, but cues ACCUMULATE across dropped frames so the cloud
    # fallback (and cloud-only TVs during the transition) never miss a cue.
    # Bounded so a long cloud outage can't grow one snapshot without limit.
    MAX_COALESCED_CUES = 200
    # Synchronous (truth) writes retry a few times before giving up, so a
    # transient blip at finalize doesn't lose a final score.
    SYNC_RETRIES = 3
    SYNC_RETRY_BASE_S = 0.1

    def __init__(self, writer, drain_interval_s: Optional[float] = None) -> None:
        self._writer = writer
        self._drain_interval_s = (
            drain_interval_s
            if drain_interval_s is not None
            else self.DRAIN_INTERVAL_S
        )
        # Coalesce slot per match: match_id -> latest snapshot. A new
        # snapshot overwrites an undrained one (latest-wins).
        self._snapshots: dict[str, dict] = {}
        # Best-effort round-score FIFO.
        self._round_scores: deque[dict] = deque()
        self._lock = threading.Lock()
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        # Observability: dropped frames/rows under back-pressure or outage.
        self.dropped_round_scores = 0

    # === Lifecycle ===

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run, daemon=True, name="runtime-persistence"
        )
        self._thread.start()

    def stop(self, drain: bool = True) -> None:
        """Stop the drainer. By default flush whatever is queued first so a
        graceful shutdown doesn't drop a pending snapshot/score."""
        self._stop.set()
        self._wake.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        if drain:
            self.flush()

    # === SupabaseWriterProtocol — synchronous (truth) lane ===

    def create_match(
        self,
        location_id: str,
        game_slug: str,
        table_number: int,
        pucks: list[tuple[str, str, str | None]],
        snapshot: dict,
    ) -> tuple[str, list[str]]:
        # Transactional create must succeed before the match exists in
        # memory — never async.
        return self._writer.create_match(
            location_id=location_id,
            game_slug=game_slug,
            table_number=table_number,
            pucks=pucks,
            snapshot=snapshot,
        )

    def insert_score(
        self,
        match_id: str,
        match_puck_id: str,
        round_number: int,
        score_delta: int,
        score_total: int,
        event_type: str,
    ) -> None:
        row = {
            "match_id": match_id,
            "match_puck_id": match_puck_id,
            "round_number": round_number,
            "score_delta": score_delta,
            "score_total": score_total,
            "event_type": event_type,
        }
        if event_type == "final":
            # Leaderboard truth — synchronous with retry.
            self._sync_write(lambda: self._writer.insert_score(**row))
        else:
            # Analytics — best-effort async FIFO.
            with self._lock:
                self._round_scores.append(row)
                if len(self._round_scores) > self.MAX_ROUND_BACKLOG:
                    self._round_scores.popleft()
                    self.dropped_round_scores += 1
                    logger.warning(
                        "round-score backlog over %d; dropping oldest",
                        self.MAX_ROUND_BACKLOG,
                    )
            self._wake.set()

    def update_match_finished(self, match_id: str, ended_at: datetime) -> None:
        self._sync_write(
            lambda: self._writer.update_match_finished(
                match_id=match_id, ended_at=ended_at
            )
        )

    def finalize_match(
        self,
        match_id: str,
        ended_at: datetime,
        finals: list,
    ) -> None:
        # Leaderboard truth — synchronous, with the bounded retry. The
        # underlying writer makes it ATOMIC (scores + status in one txn) and
        # idempotent (on conflict do nothing), so a retry after a transient
        # blip is safe and can't leave a half-finalized match (audit runtime F3).
        self._sync_write(
            lambda: self._writer.finalize_match(
                match_id=match_id, ended_at=ended_at, finals=finals
            )
        )

    def update_match_abandoned(self, match_id: str, ended_at: datetime) -> None:
        self._sync_write(
            lambda: self._writer.update_match_abandoned(
                match_id=match_id, ended_at=ended_at
            )
        )

    # === SupabaseWriterProtocol — async (best-effort) lane ===

    def update_match_snapshot(self, match_id: str, snapshot: dict) -> None:
        # Coalesce STATE latest-wins, but ACCUMULATE cues across any
        # undrained frame so a coalesced-away frame never loses its cues
        # (cues drive TV polish; the cloud copy is the fallback path). The
        # TV dedupes cues on their own seq, so re-delivering accumulated
        # cues is idempotent.
        with self._lock:
            prev = self._snapshots.get(match_id)
            prev_cues = prev.get("cues") if prev else None
            if prev_cues:
                merged = list(prev_cues)
                merged.extend(snapshot.get("cues") or [])
                if len(merged) > self.MAX_COALESCED_CUES:
                    merged = merged[-self.MAX_COALESCED_CUES :]
                # Don't mutate the caller's dict — the manager may still
                # hold a reference to it.
                snapshot = {**snapshot, "cues": merged}
            self._snapshots[match_id] = snapshot
        self._wake.set()

    # === Drain ===

    def flush(self) -> None:
        """Drain both async lanes once, synchronously. Used on shutdown and
        by tests for determinism."""
        with self._lock:
            snapshots = self._snapshots
            self._snapshots = {}
            rounds = list(self._round_scores)
            self._round_scores.clear()

        for match_id, snapshot in snapshots.items():
            try:
                self._writer.update_match_snapshot(match_id, snapshot)
            except Exception:  # noqa: BLE001
                # The STATE is best-effort (a superseding snapshot will
                # follow), but the CUES are not — re-merge the failed
                # snapshot's cues back into the slot so they get another
                # attempt rather than being lost from the cloud copy
                # (audit 2.9). The TV dedupes cues on seq, so re-delivery is
                # safe; non-delivery is what we must avoid.
                logger.exception(
                    "snapshot flush failed for match %s; re-queueing cues",
                    match_id,
                )
                self._requeue_cues(match_id, snapshot)
        for row in rounds:
            try:
                self._writer.insert_score(**row)
            except Exception:  # noqa: BLE001
                logger.exception(
                    "round-score flush failed for match %s; dropping",
                    row.get("match_id"),
                )

    def _requeue_cues(self, match_id: str, failed: dict) -> None:
        """Merge a failed snapshot's cues back into the pending slot so a
        transient cloud failure doesn't drop them (audit 2.9)."""
        cues = failed.get("cues")
        if not cues:
            return
        with self._lock:
            current = self._snapshots.get(match_id)
            if current is None:
                # No newer snapshot pending — re-queue the failed one whole so
                # its cues (and state) get another attempt.
                self._snapshots[match_id] = failed
            else:
                merged = list(cues)
                merged.extend(current.get("cues") or [])
                if len(merged) > self.MAX_COALESCED_CUES:
                    merged = merged[-self.MAX_COALESCED_CUES :]
                self._snapshots[match_id] = {**current, "cues": merged}
        self._wake.set()

    def _run(self) -> None:
        while not self._stop.is_set():
            # Wake on new work or after the interval (whichever first), so
            # a freshness target of ~DRAIN_INTERVAL_S holds even when the
            # wake signal is missed.
            self._wake.wait(self._drain_interval_s)
            self._wake.clear()
            if self._stop.is_set():
                break
            self.flush()

    # === Internals ===

    def _sync_write(self, fn) -> None:
        """Run a truth write with bounded retry. Re-raises on exhaustion so
        the caller (finalize/abandon) surfaces a genuine persistent failure
        rather than silently losing a final score — matching the pre-queue
        synchronous behaviour, only more resilient to transient blips."""
        last: Optional[Exception] = None
        for attempt in range(self.SYNC_RETRIES):
            try:
                fn()
                return
            except Exception as e:  # noqa: BLE001
                # A unique violation (Postgres SQLSTATE 23505) means the row
                # already landed — e.g. a retried final after an ambiguous
                # commit. That's idempotent success, not a failure, and it's
                # why total_matches can't inflate on replay (audit 1.2): the
                # second insert is rejected so the trigger never re-fires.
                if getattr(e, "sqlstate", None) == "23505":
                    return
                last = e
                logger.warning(
                    "truth write attempt %d/%d failed: %s",
                    attempt + 1,
                    self.SYNC_RETRIES,
                    e,
                )
                if attempt + 1 < self.SYNC_RETRIES:
                    time.sleep(self.SYNC_RETRY_BASE_S * (2 ** attempt))
        assert last is not None
        raise last
