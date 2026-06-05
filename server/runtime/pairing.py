"""
PairingManager — the game-agnostic lobby state machine.

Pucks send pair requests, dial digits, confirm codes, and finally the
host taps to start. PairingManager owns the in-memory state for the
6-digit code lifecycle. When the host starts, it resolves puck_index ->
puck_uuid via SupabaseWriter, builds a Player list, and hands off to
MatchManager.create(). The Match is then live and the TV's Realtime
subscription starts seeing rows.

Lobbies are keyed by (location_id, table_number), so one server hosts
many simultaneous tables. A puck's later calls (dial/confirm/start/cancel)
carry only its puck_index; the manager resolves the puck's lobby through a
`puck_index -> lobby key` locator populated when the puck first requests a
code. Constraint: puck_index must be unique per location (the pilot fleet
is <=8 pucks assigned across the location). When a location grows past a
single index space, the puck calls must carry table_number explicitly.

Threading: Flask is multi-threaded by default. Every mutation grabs the
manager's lock so two pucks dialing simultaneously can't corrupt the
shared dials map.
"""

from __future__ import annotations

import random
import string
import threading
import time
from dataclasses import dataclass, field
from typing import Optional, Protocol

from .game import Player
from .match import Match, MatchManager


# Same palette as the existing pair_routes.py PUCK_COLORS, transposed
# into structured tuples for the manager. Matches the locked design
# tokens in server/static/games/speed-pyramid/tokens.json.
PUCK_PALETTE: dict[int, tuple[str, str]] = {
    1: ("#3B82F6", "blue"),
    2: ("#EC4899", "pink"),
    3: ("#FBBF24", "gold"),
    4: ("#10B981", "green"),
    5: ("#A855F7", "purple"),
    6: ("#F97316", "orange"),
    7: ("#06B6D4", "cyan"),
    8: ("#EF4444", "red"),
}


def color_for(puck_index: int) -> tuple[str, str]:
    return PUCK_PALETTE.get(puck_index, ("#F8FAFC", "white"))


class PuckResolverProtocol(Protocol):
    """SupabaseWriter exposes ensure_puck; we depend on the slice that
    maps puck_index -> uuid so PairingManager stays test-isolated."""

    def ensure_puck(self, puck_index: int, location_id: str) -> str: ...


@dataclass
class LobbyPuck:
    puck_index: int
    color: str
    color_name: str
    is_host: bool
    joined_at: float


@dataclass
class Lobby:
    code: str
    game_slug: str
    location_id: str
    table_number: int
    host_index: int
    pucks: dict[int, LobbyPuck] = field(default_factory=dict)
    # Per-puck in-progress dial state, used by the host TV display only.
    dials_in_progress: dict[int, list[Optional[int]]] = field(default_factory=dict)
    started: bool = False
    match_id: Optional[str] = None
    expires_at: float = 0.0

    def snapshot(self) -> dict:
        return {
            "active": True,
            "code": self.code,
            "game_slug": self.game_slug,
            "location_id": self.location_id,
            "table_number": self.table_number,
            "host_puck_index": self.host_index,
            "started": self.started,
            "match_id": self.match_id,
            "players": [
                {
                    "puck_index": p.puck_index,
                    "color": p.color,
                    "color_name": p.color_name,
                    "is_host": p.is_host,
                    "joined_at": p.joined_at,
                }
                for p in sorted(self.pucks.values(), key=lambda x: x.joined_at)
            ],
        }


class PairingError(Exception):
    """Raised when pairing state rejects an action (no lobby, wrong
    code, non-host trying to start, etc)."""


LobbyKey = tuple  # (location_id: str, table_number: int)


class PairingManager:
    LOBBY_TTL_SECONDS = 600  # 10 min idle before reclaimed

    def __init__(
        self,
        match_manager: MatchManager,
        puck_resolver: PuckResolverProtocol,
    ) -> None:
        self.match_manager = match_manager
        self.resolver = puck_resolver
        # (location_id, table_number) -> Lobby. Many simultaneous tables.
        self._lobbies: dict[LobbyKey, Lobby] = {}
        # puck_index -> the lobby key it belongs to, so dial/confirm/
        # start/cancel resolve a puck's lobby from puck_index alone.
        self._puck_locator: dict[int, LobbyKey] = {}
        self._lock = threading.RLock()

    # === Lifecycle ===

    def request_code(
        self,
        puck_index: int,
        game_slug: str,
        location_id: str,
        table_number: int,
    ) -> dict:
        """Puck wants to pair at its table. If no lobby exists for
        (location, table) this puck becomes host; otherwise it's a joiner
        and still gets the code so its firmware can compare what it dials.

        Returns: {code, role: 'host'|'joiner', color, color_name,
                  players, game_slug, table_number}
        """
        with self._lock:
            self._purge_expired()
            key: LobbyKey = (location_id, table_number)
            lobby = self._lobbies.get(key)
            if lobby is None:
                lobby = self._fresh_lobby(
                    puck_index=puck_index,
                    game_slug=game_slug,
                    location_id=location_id,
                    table_number=table_number,
                )
                self._lobbies[key] = lobby
            elif lobby.game_slug != game_slug:
                raise PairingError(
                    f"Table {table_number} lobby is for "
                    f"{lobby.game_slug!r}, not {game_slug!r}"
                )
            self._puck_locator[puck_index] = key

            existing = lobby.pucks.get(puck_index)
            if existing is not None:
                role = "host" if existing.is_host else "joiner"
                return self._role_response(lobby, role, existing)

            # Host is the puck whose request created the lobby. Anyone
            # else is a joiner — they don't enter the lobby until they
            # confirm the code.
            is_host = puck_index == lobby.host_index
            if is_host:
                puck = self._add_puck(lobby, puck_index, is_host=True)
                return self._role_response(lobby, "host", puck)

            color, color_name = color_for(puck_index)
            return {
                "code": lobby.code,
                "role": "joiner",
                "color": color,
                "color_name": color_name,
                "game_slug": lobby.game_slug,
                "table_number": lobby.table_number,
                "players": lobby.snapshot()["players"],
            }

    def dial_progress(
        self,
        puck_index: int,
        digit_index: int,
        digit: int,
    ) -> dict:
        """Live mirror of a puck's in-flight dial. The host TV uses this
        to render each digit lighting up as the puck tilts."""
        with self._lock:
            lobby = self._resolve_lobby(puck_index)
            slots = lobby.dials_in_progress.setdefault(
                puck_index, [None] * 6
            )
            if not (0 <= digit_index < 6):
                raise PairingError(f"digit_index out of range: {digit_index}")
            if not (0 <= digit <= 9):
                raise PairingError(f"digit out of range: {digit}")
            slots[digit_index] = digit
            return {
                "puck_index": puck_index,
                "progress": list(slots),
            }

    def confirm_code(self, puck_index: int, code: str) -> dict:
        """Joiner submits the full code they've dialed. If it matches
        their table's lobby code they're added to the lobby."""
        with self._lock:
            lobby = self._resolve_lobby(puck_index)
            if code != lobby.code:
                raise PairingError("Code does not match the table's lobby")
            existing = lobby.pucks.get(puck_index)
            if existing is not None:
                role = "host" if existing.is_host else "joiner"
                return self._role_response(lobby, role, existing)
            puck = self._add_puck(lobby, puck_index, is_host=False)
            return self._role_response(lobby, "joiner", puck)

    def start_match(self, puck_index: int, **game_options) -> Match:
        """Host taps to start. Resolves puck UUIDs, builds Player list,
        hands off to MatchManager.create(). Returns the live Match."""
        with self._lock:
            lobby = self._resolve_lobby(puck_index)
            if puck_index != lobby.host_index:
                raise PairingError(
                    f"Only the host (puck {lobby.host_index}) can start"
                )
            if lobby.started:
                # Idempotent — host double-taps shouldn't blow up.
                if lobby.match_id and lobby.match_id in self.match_manager.matches:
                    return self.match_manager.matches[lobby.match_id]
                raise PairingError("Lobby already started but match missing")

            players: list[Player] = []
            host_first = sorted(
                lobby.pucks.values(),
                key=lambda p: (not p.is_host, p.joined_at),
            )
            for lp in host_first:
                puck_uuid = self.resolver.ensure_puck(
                    puck_index=lp.puck_index,
                    location_id=lobby.location_id,
                )
                players.append(
                    Player(
                        puck_uuid=puck_uuid,
                        puck_index=lp.puck_index,
                        name=f"Puck {lp.puck_index}",
                        color=lp.color,
                    )
                )

            match = self.match_manager.create(
                location_id=lobby.location_id,
                game_slug=lobby.game_slug,
                table_number=lobby.table_number,
                players=players,
                **game_options,
            )
            lobby.started = True
            lobby.match_id = match.id
            return match

    def cancel(self, puck_index: int) -> None:
        with self._lock:
            lobby = self._resolve_lobby(puck_index)
            if puck_index != lobby.host_index:
                raise PairingError(
                    f"Only the host (puck {lobby.host_index}) can cancel"
                )
            self._remove_lobby((lobby.location_id, lobby.table_number))

    def clear(self) -> None:
        """Force-clear EVERY lobby. Used by tests and the bar portal's
        global reset."""
        with self._lock:
            self._lobbies.clear()
            self._puck_locator.clear()

    def clear_table(self, location_id: str, table_number: int) -> None:
        """Clear a single table's lobby — e.g. the portal resetting one
        table without disturbing the others."""
        with self._lock:
            self._remove_lobby((location_id, table_number))

    # === Inspection ===

    def lobby_snapshot(
        self,
        location_id: Optional[str] = None,
        table_number: Optional[int] = None,
    ) -> dict:
        """Snapshot of one table's lobby. With an explicit
        (location_id, table_number) returns that table's lobby. With
        neither, returns the sole lobby if exactly one is active (the
        single-table pilot case); if several are active it reports them
        so the caller can pick a table."""
        with self._lock:
            self._purge_expired()
            if location_id is not None and table_number is not None:
                lobby = self._lobbies.get((location_id, table_number))
                return lobby.snapshot() if lobby else {"active": False}
            if not self._lobbies:
                return {"active": False}
            if len(self._lobbies) == 1:
                return next(iter(self._lobbies.values())).snapshot()
            return {
                "active": False,
                "reason": "multiple_tables",
                "tables": [
                    {
                        "location_id": loc,
                        "table_number": tbl,
                        "code": lob.code,
                        "started": lob.started,
                    }
                    for (loc, tbl), lob in self._lobbies.items()
                ],
            }

    # === Internals ===

    def _fresh_lobby(
        self,
        puck_index: int,
        game_slug: str,
        location_id: str,
        table_number: int,
    ) -> Lobby:
        lobby = Lobby(
            code=self._new_code(),
            game_slug=game_slug,
            location_id=location_id,
            table_number=table_number,
            host_index=puck_index,
            expires_at=time.time() + self.LOBBY_TTL_SECONDS,
        )
        return lobby

    def _add_puck(
        self, lobby: Lobby, puck_index: int, *, is_host: bool
    ) -> LobbyPuck:
        color, color_name = color_for(puck_index)
        lp = LobbyPuck(
            puck_index=puck_index,
            color=color,
            color_name=color_name,
            is_host=is_host,
            joined_at=time.time(),
        )
        lobby.pucks[puck_index] = lp
        return lp

    def _role_response(
        self, lobby: Lobby, role: str, puck: LobbyPuck
    ) -> dict:
        return {
            "code": lobby.code,
            "role": role,
            "color": puck.color,
            "color_name": puck.color_name,
            "game_slug": lobby.game_slug,
            "table_number": lobby.table_number,
            "players": lobby.snapshot()["players"],
        }

    def _resolve_lobby(self, puck_index: int) -> Lobby:
        """Find the lobby a puck belongs to via the locator. Raises if the
        puck never requested a code or its lobby expired."""
        self._purge_expired()
        key = self._puck_locator.get(puck_index)
        if key is None:
            raise PairingError("No active lobby for this puck")
        lobby = self._lobbies.get(key)
        if lobby is None:
            self._puck_locator.pop(puck_index, None)
            raise PairingError("No active lobby")
        return lobby

    def _remove_lobby(self, key: LobbyKey) -> None:
        if self._lobbies.pop(key, None) is None:
            return
        # Drop every locator entry that pointed at this lobby.
        for idx in [
            idx for idx, k in self._puck_locator.items() if k == key
        ]:
            del self._puck_locator[idx]

    def _purge_expired(self) -> None:
        now = time.time()
        for key, lobby in list(self._lobbies.items()):
            if not lobby.started and lobby.expires_at < now:
                self._remove_lobby(key)

    @staticmethod
    def _new_code() -> str:
        return "".join(random.choices(string.digits, k=6))
