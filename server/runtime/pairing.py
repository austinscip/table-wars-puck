"""
PairingManager — the game-agnostic lobby state machine.

Pucks send pair requests, dial digits, confirm codes, and finally the
host taps to start. PairingManager owns the in-memory state for the
6-digit code lifecycle. When the host starts, it resolves puck_index ->
puck_uuid via SupabaseWriter, builds a Player list, and hands off to
MatchManager.create(). The Match is then live and the TV's Realtime
subscription starts seeing rows.

One active lobby per location at a time. For pilot scale that's fine;
multi-bar deployments will key lobbies by (location_id, table_number).

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


class PairingManager:
    LOBBY_TTL_SECONDS = 600  # 10 min idle before reclaimed

    def __init__(
        self,
        match_manager: MatchManager,
        puck_resolver: PuckResolverProtocol,
    ) -> None:
        self.match_manager = match_manager
        self.resolver = puck_resolver
        self._lobby: Optional[Lobby] = None
        self._lock = threading.RLock()

    # === Lifecycle ===

    def request_code(
        self,
        puck_index: int,
        game_slug: str,
        location_id: str,
        table_number: int,
    ) -> dict:
        """Puck wants to pair. If no lobby exists, this puck becomes
        host. If a lobby exists, this puck is a joiner — they still get
        the code so their firmware can compare what they dial.

        Returns: {code, role: 'host'|'joiner', color, color_name,
                  players, game_slug}
        """
        with self._lock:
            self._purge_if_expired()
            if self._lobby is None:
                self._lobby = self._fresh_lobby(
                    puck_index=puck_index,
                    game_slug=game_slug,
                    location_id=location_id,
                    table_number=table_number,
                )
            elif self._lobby.game_slug != game_slug:
                raise PairingError(
                    f"Active lobby is for {self._lobby.game_slug!r}, "
                    f"not {game_slug!r}"
                )

            existing = self._lobby.pucks.get(puck_index)
            if existing is not None:
                role = "host" if existing.is_host else "joiner"
                return self._role_response(role, existing)

            # First time we've seen this puck on the current lobby.
            # Host is the puck whose request created the lobby. Anyone
            # else is a joiner — they don't enter the lobby until they
            # confirm the code.
            is_host = puck_index == self._lobby.host_index
            if is_host:
                puck = self._add_puck(puck_index, is_host=True)
                return self._role_response("host", puck)

            color, color_name = color_for(puck_index)
            return {
                "code": self._lobby.code,
                "role": "joiner",
                "color": color,
                "color_name": color_name,
                "game_slug": self._lobby.game_slug,
                "players": self._lobby.snapshot()["players"],
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
            lobby = self._require_lobby()
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
        the lobby code they're added to the lobby."""
        with self._lock:
            lobby = self._require_lobby()
            if code != lobby.code:
                raise PairingError("Code does not match the current lobby")
            existing = lobby.pucks.get(puck_index)
            if existing is not None:
                role = "host" if existing.is_host else "joiner"
                return self._role_response(role, existing)
            puck = self._add_puck(puck_index, is_host=False)
            return self._role_response("joiner", puck)

    def start_match(self, puck_index: int, **game_options) -> Match:
        """Host taps to start. Resolves puck UUIDs, builds Player list,
        hands off to MatchManager.create(). Returns the live Match."""
        with self._lock:
            lobby = self._require_lobby()
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
            lobby = self._require_lobby()
            if puck_index != lobby.host_index:
                raise PairingError(
                    f"Only the host (puck {lobby.host_index}) can cancel"
                )
            self._lobby = None

    def clear(self) -> None:
        """Force-clear the lobby. Used by tests and the bar portal."""
        with self._lock:
            self._lobby = None

    # === Inspection ===

    def lobby_snapshot(self) -> dict:
        with self._lock:
            self._purge_if_expired()
            if self._lobby is None:
                return {"active": False}
            return self._lobby.snapshot()

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

    def _add_puck(self, puck_index: int, *, is_host: bool) -> LobbyPuck:
        assert self._lobby is not None
        color, color_name = color_for(puck_index)
        lp = LobbyPuck(
            puck_index=puck_index,
            color=color,
            color_name=color_name,
            is_host=is_host,
            joined_at=time.time(),
        )
        self._lobby.pucks[puck_index] = lp
        return lp

    def _role_response(self, role: str, puck: LobbyPuck) -> dict:
        assert self._lobby is not None
        return {
            "code": self._lobby.code,
            "role": role,
            "color": puck.color,
            "color_name": puck.color_name,
            "game_slug": self._lobby.game_slug,
            "players": self._lobby.snapshot()["players"],
        }

    def _require_lobby(self) -> Lobby:
        self._purge_if_expired()
        if self._lobby is None:
            raise PairingError("No active lobby")
        return self._lobby

    def _purge_if_expired(self) -> None:
        if self._lobby is None:
            return
        if not self._lobby.started and self._lobby.expires_at < time.time():
            self._lobby = None

    @staticmethod
    def _new_code() -> str:
        return "".join(random.choices(string.digits, k=6))
