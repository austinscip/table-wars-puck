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

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Protocol

from .game import Game, Player, InputEvent, ScoreEvent, StateUpdate
from .registry import GameRegistry


class SupabaseWriterProtocol(Protocol):
    """The slice of SupabaseWriter the manager needs. Keeping it as a
    Protocol means tests can swap in a fake without touching network."""

    def insert_match(
        self, location_id: str, game_slug: str, table_number: int
    ) -> str: ...

    def upsert_match_puck(
        self,
        match_id: str,
        puck_uuid: str,
        role: str,
        player_name: str | None,
    ) -> str: ...

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


class MatchManager:
    """Owns active matches in memory and writes every state-changing
    event to Supabase. Single-process for now; if we shard across
    workers, store match state in Redis and lock per match_id."""

    def __init__(
        self,
        registry: GameRegistry,
        writer: SupabaseWriterProtocol,
    ) -> None:
        self.registry = registry
        self.writer = writer
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

        match_id = self.writer.insert_match(
            location_id=location_id,
            game_slug=game_slug,
            table_number=table_number,
        )

        match_puck_ids: dict[int, str] = {}
        for i, p in enumerate(players):
            role = "host" if i == 0 else "sibling"
            mp_id = self.writer.upsert_match_puck(
                match_id=match_id,
                puck_uuid=p.puck_uuid,
                role=role,
                player_name=p.name,
            )
            match_puck_ids[p.puck_index] = mp_id

        game = game_class(players=players, **game_options)
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
        return match

    # === Drive ===

    def on_input(self, match_id: str, event: InputEvent) -> StateUpdate:
        match = self._must_get(match_id)
        if match.status != "active":
            return StateUpdate(state=match.game.get_state())

        update = match.game.on_input(event)
        self._persist_scores(match, update.score_events)
        if update.is_final or match.game.is_over():
            self._finalize(match)
        return update

    def tick(self, match_id: str) -> StateUpdate:
        match = self._must_get(match_id)
        if match.status != "active":
            return StateUpdate(state=match.game.get_state())

        update = match.game.tick()
        self._persist_scores(match, update.score_events)
        if update.is_final or match.game.is_over():
            self._finalize(match)
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
