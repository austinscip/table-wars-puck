"""
HeartbeatTracker — per-puck last-seen tracking so the runtime notices
when a puck stops talking (battery dies, Wi-Fi flakes, app crashes).

Why this lives in the runtime instead of per-game: the failure mode
("puck N hasn't said anything in 8s") is universal. Each game can
choose how to react via on_puck_disconnected (force-lock a round,
mark eliminated, give up the turn) but the detection is shared.

Threshold model:
- ping(match_id, puck_index)  -- called every time the runtime sees
  input from this puck. Refreshes last_seen.
- sweep(match_id, now=None) -> set[int]
  Returns the set of puck_indices that crossed STALE_THRESHOLD_S since
  the last sweep. The tracker marks each as "stale_emitted" so it
  won't be returned again — exactly-once semantics per disconnect.
- recover() if a stale puck pings again, it clears the emitted flag
  so a subsequent disconnect would re-fire.

Single in-process for now; multi-worker deployments would share state
in Redis with the same API.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass


# Pucks must ping at least this often to stay alive. Picked at 8s
# because the runtime ticks at 10 Hz and most games will see input
# from active pucks every 100-500 ms; 8s of silence is "the puck
# probably crashed", not "the player is thinking".
STALE_THRESHOLD_S = 8.0


@dataclass
class _PuckHeartbeat:
    last_seen: float
    stale_emitted: bool = False


class HeartbeatTracker:
    def __init__(self, stale_threshold_s: float = STALE_THRESHOLD_S) -> None:
        self.stale_threshold_s = stale_threshold_s
        self._beats: dict[str, dict[int, _PuckHeartbeat]] = {}
        self._lock = threading.RLock()

    # === Pings ===

    def ping(
        self, match_id: str, puck_index: int, now: float | None = None
    ) -> bool:
        """Refresh last_seen for a puck. Returns True iff this ping is a
        RECONNECT transition — the puck had previously been swept stale and
        is now talking again. The manager uses that to call the game's
        on_puck_reconnected so a recovered puck is un-retired (audit
        runtime-games-2026-06-06)."""
        ts = now if now is not None else time.monotonic()
        with self._lock:
            beats = self._beats.setdefault(match_id, {})
            existing = beats.get(puck_index)
            if existing is None:
                beats[puck_index] = _PuckHeartbeat(last_seen=ts)
                return False
            # Re-pinging clears any prior stale flag — disconnect
            # transitions can fire again if the puck dies a second time.
            was_stale = existing.stale_emitted
            existing.last_seen = ts
            existing.stale_emitted = False
            return was_stale

    def register(self, match_id: str, puck_indices: list[int]) -> None:
        """Seed last_seen for every puck in a freshly-created match
        so the first sweep doesn't fire spuriously for pucks that
        haven't yet sent input."""
        now = time.monotonic()
        with self._lock:
            beats = self._beats.setdefault(match_id, {})
            for idx in puck_indices:
                beats.setdefault(idx, _PuckHeartbeat(last_seen=now))

    # === Sweep ===

    def sweep(
        self, match_id: str, now: float | None = None
    ) -> set[int]:
        """Return puck_indices that crossed the stale threshold since
        the last sweep. Each puck is reported exactly once per
        disconnect transition."""
        ts = now if now is not None else time.monotonic()
        with self._lock:
            beats = self._beats.get(match_id)
            if not beats:
                return set()
            newly_stale: set[int] = set()
            for puck_index, beat in beats.items():
                if beat.stale_emitted:
                    continue
                if ts - beat.last_seen >= self.stale_threshold_s:
                    beat.stale_emitted = True
                    newly_stale.add(puck_index)
            return newly_stale

    def all_stale(self, match_id: str, now: float | None = None) -> bool:
        """True when every puck in the match has been silent for at least
        the stale threshold. Used by the abandoned-match sweep: a match
        where no puck is talking AND no input has landed for a while is a
        table everyone walked away from. Returns False for an unknown or
        empty match (nothing to abandon)."""
        ts = now if now is not None else time.monotonic()
        with self._lock:
            beats = self._beats.get(match_id)
            if not beats:
                return False
            return all(
                ts - beat.last_seen >= self.stale_threshold_s
                for beat in beats.values()
            )

    # === Cleanup ===

    def drop_match(self, match_id: str) -> None:
        with self._lock:
            self._beats.pop(match_id, None)

    def snapshot(self, match_id: str) -> dict[int, dict]:
        """Read-only view of one match's heartbeats. Used by debug
        endpoints and tests."""
        with self._lock:
            beats = self._beats.get(match_id, {})
            return {
                puck_index: {
                    "last_seen": beat.last_seen,
                    "stale_emitted": beat.stale_emitted,
                }
                for puck_index, beat in beats.items()
            }

    # === Durability (audit 1.8) ===

    def export(self, match_id: str) -> dict[int, dict]:
        """Serializable heartbeat state for one match: last_seen as an
        ELAPSED offset (monotonic doesn't survive a restart) plus the
        stale_emitted flag. Persisted alongside the match so recovery
        preserves the exactly-once disconnect semantics — a puck that already
        disconnected pre-crash won't re-fire its PLAYER_LEFT cue on boot."""
        now = time.monotonic()
        with self._lock:
            beats = self._beats.get(match_id, {})
            return {
                puck_index: {
                    "last_seen_elapsed_s": now - beat.last_seen,
                    "stale_emitted": beat.stale_emitted,
                }
                for puck_index, beat in beats.items()
            }

    def restore(self, match_id: str, data: dict) -> None:
        """Re-seed heartbeats from export() output, re-basing the elapsed
        offset onto the current monotonic clock. Tolerates JSON string keys
        (Redis/JSON store round-trips int dict keys to strings)."""
        now = time.monotonic()
        with self._lock:
            beats = self._beats.setdefault(match_id, {})
            for raw_idx, entry in data.items():
                idx = int(raw_idx)
                beats[idx] = _PuckHeartbeat(
                    last_seen=now - float(entry.get("last_seen_elapsed_s", 0.0)),
                    stale_emitted=bool(entry.get("stale_emitted", False)),
                )
