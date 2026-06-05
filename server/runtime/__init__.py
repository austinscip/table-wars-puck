"""
Multi-game runtime — the "boring stuff" (Mike's Caxy meeting, 2026-06-02)
in one place so each game inherits pairing, scoring, leaderboards,
matchmaking, state machine, and real-time sync for free.

Public surface:

    from server.runtime import (
        Game,            # base class every game implements
        Player,          # generic per-puck state
        InputEvent,      # normalised puck input
        ScoreEvent,      # one score change emitted by a game tick
        StateUpdate,     # bundle of state + score events returned per input
        registry,        # global GameRegistry singleton
        MatchManager,    # match lifecycle + Supabase persistence
    )

See server/runtime/CONTEXT.md for the contract a game class must satisfy
and the lifecycle MatchManager drives.
"""

from .game import Game, Player, InputEvent, ScoreEvent, StateUpdate, InputKind
from .registry import GameRegistry, registry
from .match import Match, MatchManager
from .inputs import event_from_dict

__all__ = [
    "Game",
    "Player",
    "InputEvent",
    "InputKind",
    "ScoreEvent",
    "StateUpdate",
    "GameRegistry",
    "registry",
    "Match",
    "MatchManager",
    "event_from_dict",
]
