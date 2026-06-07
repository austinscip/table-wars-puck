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

from .game import (
    Game,
    Player,
    InputEvent,
    ScoreEvent,
    StateUpdate,
    InputKind,
    DEFAULT_TICK_DT,
)
from .registry import GameRegistry, registry
from .match import (
    Match,
    MatchManager,
    StateSink,
    serialize_match,
    deserialize_match,
)
from .match_store import InMemoryMatchStore, RedisMatchStore
from .persistence import PersistenceQueue
from .identity import PlayerIdentity
from .trivia_content import TriviaContentCache
from .inputs import event_from_dict
from .pairing import PairingManager, PairingError, color_for
from .scheduler import TickScheduler
from .heartbeat import HeartbeatTracker, STALE_THRESHOLD_S
from .idempotency import IdempotencyCache
from .auth import MatchTokenAuthority, TvMatchTokenAuthority, AuthError
from .ratelimit import RateLimiter
from .redis_backends import RedisIdempotencyCache, RedisLock
from .log import (
    configure_logging,
    get_logger,
    init_sentry,
    harden_secrets,
    redact,
)
from .analytics import init_analytics, capture as capture_event
from .cues import (
    Cue,
    CueChannel,
    CueEvent,
    cue_player_correct,
    cue_player_wrong,
    cue_match_start,
    cue_match_end,
    cue_round_start,
    cue_timer_warning,
)

__all__ = [
    "Game",
    "Player",
    "InputEvent",
    "InputKind",
    "ScoreEvent",
    "StateUpdate",
    "DEFAULT_TICK_DT",
    "GameRegistry",
    "registry",
    "Match",
    "MatchManager",
    "StateSink",
    "serialize_match",
    "deserialize_match",
    "InMemoryMatchStore",
    "RedisMatchStore",
    "PersistenceQueue",
    "PlayerIdentity",
    "TriviaContentCache",
    "event_from_dict",
    "PairingManager",
    "PairingError",
    "color_for",
    "TickScheduler",
    "HeartbeatTracker",
    "STALE_THRESHOLD_S",
    "IdempotencyCache",
    "MatchTokenAuthority",
    "TvMatchTokenAuthority",
    "AuthError",
    "RateLimiter",
    "RedisIdempotencyCache",
    "RedisLock",
    "configure_logging",
    "get_logger",
    "init_sentry",
    "harden_secrets",
    "redact",
    "init_analytics",
    "capture_event",
    "Cue",
    "CueChannel",
    "CueEvent",
    "cue_player_correct",
    "cue_player_wrong",
    "cue_match_start",
    "cue_match_end",
    "cue_round_start",
    "cue_timer_warning",
]
