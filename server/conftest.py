"""
Pytest configuration + shared fixtures for the Table Wars server.

Lives at the server root so pytest adds this directory to sys.path,
letting tests `import runtime` and `import games` exactly the way the
Flask app does (the games import `from runtime import ...`, so the
server dir must be importable as a top-level path).

The fixtures here deliberately avoid any network or Supabase dependency:
a FakeWriter records every persistence call so a test can assert on the
real MatchManager lifecycle (create -> input/tick -> finalise) without a
database. Per the no-unguarded-fixes policy, regression tests drive the
actual runtime, not a re-implementation of it.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime

import pytest

# Make `import runtime` / `import games` resolve the same way app.py does.
_SERVER_DIR = os.path.dirname(os.path.abspath(__file__))
if _SERVER_DIR not in sys.path:
    sys.path.insert(0, _SERVER_DIR)

from runtime import (  # noqa: E402
    HeartbeatTracker,
    MatchManager,
    Player,
    registry as game_registry,
)


class FakeWriter:
    """Records every SupabaseWriter call the MatchManager makes so tests
    can assert on the persistence side-effects without a real database.
    Satisfies the SupabaseWriterProtocol the manager depends on."""

    def __init__(self) -> None:
        self.matches: list[dict] = []
        self.match_pucks: dict[tuple[str, str], str] = {}
        self.scores: list[dict] = []
        self.snapshots: list[tuple[str, dict]] = []
        self.finished: list[tuple[str, datetime]] = []
        self.abandoned: list[tuple[str, datetime]] = []
        self._match_seq = 0
        self._puck_seq = 0
        # Player identity (ADR 0005).
        self.players_by_token: dict[str, str] = {}
        self.player_names: dict[str, str | None] = {}
        self.bindings: list[tuple[str, str, str | None]] = []
        self.phone_hashes: dict[str, str] = {}
        self._player_seq = 0

    def create_match(
        self,
        location_id: str,
        game_slug: str,
        table_number: int,
        pucks: list[tuple[str, str, str | None]],
        snapshot: dict,
    ) -> tuple[str, list[str]]:
        # Mirrors the real writer's atomic create: one match row, N puck
        # rows, one seed snapshot. The fake doesn't model rollback — tests
        # that need to exercise a mid-create failure raise from a wrapper
        # around this method.
        self._match_seq += 1
        match_id = f"match-{self._match_seq}"
        self.matches.append(
            {
                "id": match_id,
                "location_id": location_id,
                "game_slug": game_slug,
                "table_number": table_number,
            }
        )
        mp_ids: list[str] = []
        for puck_uuid, _role, _name in pucks:
            self._puck_seq += 1
            mp_id = f"mp-{self._puck_seq}"
            self.match_pucks[(match_id, puck_uuid)] = mp_id
            mp_ids.append(mp_id)
        self.snapshots.append((match_id, snapshot))
        return match_id, mp_ids

    def insert_score(
        self,
        match_id: str,
        match_puck_id: str,
        round_number: int,
        score_delta: int,
        score_total: int,
        event_type: str,
    ) -> None:
        self.scores.append(
            {
                "match_id": match_id,
                "match_puck_id": match_puck_id,
                "round_number": round_number,
                "score_delta": score_delta,
                "score_total": score_total,
                "event_type": event_type,
            }
        )

    def update_match_finished(self, match_id: str, ended_at: datetime) -> None:
        self.finished.append((match_id, ended_at))

    def update_match_abandoned(self, match_id: str, ended_at: datetime) -> None:
        self.abandoned.append((match_id, ended_at))

    def update_match_snapshot(self, match_id: str, snapshot: dict) -> None:
        self.snapshots.append((match_id, snapshot))

    # === Players (ADR 0005) ===

    def resolve_or_create_player(self, token_hash, display_name=None):
        pid = self.players_by_token.get(token_hash)
        if pid is not None:
            if display_name and self.player_names.get(pid) is None:
                self.player_names[pid] = display_name
            return pid, False
        self._player_seq += 1
        pid = f"player-{self._player_seq}"
        self.players_by_token[token_hash] = pid
        self.player_names[pid] = display_name
        return pid, True

    def bind_player_to_match_puck(self, match_puck_id, player_id, display_name=None):
        self.bindings.append((match_puck_id, player_id, display_name))

    def find_player_id_by_phone_hash(self, phone_hash):
        for pid, ph in self.phone_hashes.items():
            if ph == phone_hash:
                return pid
        return None

    def attach_phone_hash(self, player_id, phone_hash):
        self.phone_hashes[player_id] = phone_hash

    # === Test conveniences ===

    def final_scores(self, match_id: str) -> dict[str, int]:
        """match_puck_id -> score_total for every 'final' score row."""
        return {
            s["match_puck_id"]: s["score_total"]
            for s in self.scores
            if s["match_id"] == match_id and s["event_type"] == "final"
        }

    def cue_names(self, match_id: str) -> list[str]:
        """Flat list of every cue name written to any snapshot for this
        match, in write order. Lets a test assert a beat actually reached
        the persistence layer the TV reads from."""
        out: list[str] = []
        for mid, snap in self.snapshots:
            if mid != match_id:
                continue
            for cue in snap.get("cues", []) or []:
                out.append(cue.get("cue"))
        return out

    def cue_seqs(self, match_id: str) -> list[int]:
        """Every cue `seq` written to any snapshot for this match, in
        write order. The TV dedupes on this, so it must be strictly
        increasing across the whole match."""
        out: list[int] = []
        for mid, snap in self.snapshots:
            if mid != match_id:
                continue
            for cue in snap.get("cues", []) or []:
                if "seq" in cue:
                    out.append(cue["seq"])
        return out


@pytest.fixture(autouse=True)
def _games_registered():
    """Importing the games package self-registers all four games. The
    registry is a module singleton, so the guard makes the import
    idempotent across the whole test session."""
    import games  # noqa: F401
    return game_registry


@pytest.fixture
def writer() -> FakeWriter:
    return FakeWriter()


@pytest.fixture
def heartbeat() -> HeartbeatTracker:
    return HeartbeatTracker()


@pytest.fixture
def manager(writer: FakeWriter, heartbeat: HeartbeatTracker) -> MatchManager:
    """A MatchManager wired to the FakeWriter + a real HeartbeatTracker
    but no scheduler — tests drive tick() manually so they control time."""
    return MatchManager(
        registry=game_registry, writer=writer, heartbeat=heartbeat
    )


def make_players(n: int) -> list[Player]:
    """n pucks, indices 1..n, with stable uuids/names/colors."""
    palette = ["#e11", "#1a1", "#11e", "#ee1", "#e1e", "#1ee", "#888", "#000"]
    return [
        Player(
            puck_uuid=f"uuid-{i}",
            puck_index=i,
            name=f"P{i}",
            color=palette[(i - 1) % len(palette)],
        )
        for i in range(1, n + 1)
    ]


def force_disconnect(
    manager: MatchManager, match_id: str, puck_index: int
) -> None:
    """Age a puck's heartbeat past the stale threshold so the next
    manager.tick() sweep reports it disconnected. Pokes tracker internals
    deliberately: the alternative is a real-time sleep, which would make
    the regression slow and flaky. This drives the genuine sweep ->
    on_puck_disconnected path, not a shortcut around it."""
    beats = manager.heartbeat._beats[match_id]
    beats[puck_index].last_seen -= manager.heartbeat.stale_threshold_s + 100.0


def force_all_stale(manager: MatchManager, match_id: str) -> None:
    """Age every puck's heartbeat past the stale threshold so
    HeartbeatTracker.all_stale(match_id) is True on the next sweep. Used
    by the abandoned-match test."""
    beats = manager.heartbeat._beats[match_id]
    for beat in beats.values():
        beat.last_seen -= manager.heartbeat.stale_threshold_s + 100.0
