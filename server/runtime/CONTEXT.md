# Multi-game runtime — vocabulary + contract

The runtime is the "boring stuff in one place" (Caxy meeting, 2026-06-02).
Pairing, scoring, leaderboards, matchmaking, state machine, real-time
sync live here so every game inherits them.

## Module map

| File | Responsibility |
|---|---|
| `game.py` | The `Game` ABC every game implements. Plus the dataclasses (`Player`, `InputEvent`, `ScoreEvent`, `StateUpdate`) the runtime passes around. |
| `registry.py` | `GameRegistry` — slug → game class. Games call `registry.register(SpeedPyramid)` at import time. |
| `inputs.py` | Normalises raw puck JSON into `InputEvent`. The one place input aliases collapse. |
| `match.py` | `Match` dataclass + `MatchManager`. Owns active matches in memory, persists every state-changing event to Supabase. |
| `../supabase_client.py` | `SupabaseWriter` — psycopg connection to Supabase Postgres. Bypasses RLS because it connects as the `postgres` role (equivalent to PostgREST's service_role). |

## What a Game class must implement

```python
from server.runtime import Game, Player, InputEvent, StateUpdate, registry

class SpeedPyramid(Game):
    slug = "speed_pyramid"
    display_name = "Speed Pyramid"
    min_players = 1
    max_players = 8
    input_schema = ("tilt_x", "tilt_y", "button_tap", "button_hold")

    def __init__(self, players, **options):
        ...

    def on_input(self, event: InputEvent) -> StateUpdate:
        ...

    def tick(self) -> StateUpdate:
        # Default no-op. Override for time-driven games.
        return StateUpdate(state=self.get_state())

    def on_puck_disconnected(self, puck_index) -> StateUpdate | None:
        # Optional. The MatchManager calls this from the heartbeat sweep
        # when a puck goes stale. Default no-op returns None. Override to
        # keep the match moving instead of hanging on a silent puck.
        return None

    def get_state(self) -> dict:
        ...

    def is_over(self) -> bool:
        ...

    def final_scores(self) -> dict[int, int]:
        # puck_index -> final score
        ...

registry.register(SpeedPyramid)
```

## Lifecycle the MatchManager drives

```
              create()
                 │
                 ▼
       insert_match (Supabase)
       upsert_match_puck × N
       game_class(players)
                 │
                 ▼
       ┌─────────────────┐
       │     active      │◄─── on_input(event) ──── puck HTTP
       │                 │◄─── tick()         ──── 10 Hz loop
       │                 │◄─── on_puck_disconnected(i)
       │                 │        ▲ heartbeat sweep (inside tick)
       └────────┬────────┘
                │
       is_over() or is_final
                │
                ▼
            _finalize()
       insert_score(event_type='final') × N
       update_match_finished
                │
                ▼
           Supabase Realtime fans
           the row updates out to
           subscribed TVs.
```

## How games declare their inputs

`input_schema` is a tuple of `InputKind` strings the game cares about.
The puck firmware sends the union of all six channels every tick; the
runtime doesn't filter. The schema exists so:

- The bar portal can display "this game uses tilt + button" without
  inspecting source.
- The dev sandbox can show only the relevant Virtual Puck controls.
- A future input-validation layer can flag if a puck firmware version is
  too old to provide a channel a game depends on.

## Why one InputEvent shape across all games

The existing `multiplayer_engines.py` dispatcher has one signature per
game (`update(puck_id, tilt_x, tilt_y, shake_intensity)` vs
`update(puck_id, gyro_z)` vs ...). Every new game costs an `isinstance`
branch. With `InputEvent`, the dispatcher is `match.game.on_input(event)`
— the game pulls only the fields it cares about. Adding game N+1 is zero
runtime changes.

## How disconnects are handled

Detection is shared, reaction is per-game. The `HeartbeatTracker` (one
shared instance) marks a puck stale when it hasn't pinged in
`STALE_THRESHOLD_S`. Inside `MatchManager.tick`, the sweep emits a
`PLAYER_LEFT` cue and then calls `game.on_puck_disconnected(puck_index)`
exactly once per disconnect transition. The returned `StateUpdate` (cues,
score_events, fresh state, `is_final`) folds into the same tick, so one
tick both detects and resolves the disconnect.

Each game keeps the match moving its own way:

| Game | Reaction |
|---|---|
| Speed Pyramid | Force-locks the puck as TIMEOUT (0 pts) so the round resolves. Remembers the disconnect in a `disconnected` set and re-locks it at the top of every later round — the heartbeat only reports a disconnect once, so the game owns the persistence. |
| Puck Golf | Retires the puck (`disconnected` + `hole_done` for every hole) and passes the turn if it was theirs, so the round-robin never stalls. |
| Puck Racer | Marks the puck `disconnected` — integration skips it, it can't finish, and the race ends when every racer is finished-or-disconnected. |
| Smash | Eliminates the fighter so "last one standing" can be reached. |

All four finalise the match when the disconnect leaves no one able to
play. Regression coverage: `server/tests/test_disconnect.py` drives a
real match through the MatchManager with a heartbeat-driven disconnect
and asserts the game reacted, not just that a cue fired.

## ScoreEvent semantics

- `event_type="round"` — mid-match progress. Many per match per puck.
  Does not update the leaderboards table (the trigger filters for
  `final` only).
- `event_type="final"` — the puck's terminal score. Exactly one per
  match per puck, enforced by the
  `uniq_final_score_per_match_puck` partial unique index in the
  initial schema migration. The leaderboards trigger upserts day/week/
  month/all_time buckets when this row lands.

## Why MatchManager is in-process

Pilot scale is one bar, ≤4 concurrent matches. Storing match state in a
Python dict keyed by match_id is the simplest thing that works. When we
need to shard across workers (multi-bar, multi-process), the swap is:

1. Move `MatchManager.matches` to Redis with `match:{id}` keys.
2. Take a per-match Redis lock around `on_input` / `tick` so two
   workers can't double-process the same input frame.
3. Everything else (game class, Supabase writer) stays.

No premature distribution.

## How the TV sees state

Not via the MatchManager. The TV subscribes to Supabase Realtime
channels:

- `matches` UPDATE filtered by `id=eq.<match_id>` — status flips.
- `match_pucks` INSERT filtered by `match_id=eq.<match_id>` — puck
  joined the lobby.
- `scores` INSERT filtered by `match_id=eq.<match_id>` — every score
  event, mid-match and final.

The TV reconstructs the visible state from these streams. The
`get_state()` dict the game returns goes into a `matches.snapshot` JSONB
column (TBD — not yet on the schema; will add when the first game's
state-shape stabilises).

## Open items not yet wired

- `matches.snapshot` JSONB column for the full game state. Deferred
  until Speed Pyramid's state shape is stable in the runtime.
- Tick loop (10 Hz scheduler). Single asyncio task per active match.
- Game options validation — `game_options` flows through `create()`
  untyped; should become per-game pydantic models.
- Power-up framework — Track G item 16, scoped for Speed Pyramid
  rework or later.
- Ghost sweep / heartbeat — Track G item 17. Detection lands via
  `HeartbeatTracker`; per-game reaction via `on_puck_disconnected`
  (see "How disconnects are handled"). Still TODO: auto-removing a
  permanently-gone puck's `match_pucks` row vs. leaving it for the
  scoreboard.
