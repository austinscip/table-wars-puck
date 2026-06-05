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
| `match.py` | `Match` dataclass + `MatchManager`. Owns active matches in memory, persists every state-changing event to Supabase. Also drives the abandoned-match sweep and per-match cue `seq` stamping. |
| `idempotency.py` | `IdempotencyCache` — bounded LRU so a retried puck request isn't processed twice. Keyed by `(match_id, puck_index, event_id)`. |
| `heartbeat.py` | `HeartbeatTracker` — per-puck last-seen + `all_stale` for the abandoned sweep. |
| `log.py` | `configure_logging` / `get_logger` / `init_sentry`. Standard Python logging + optional Sentry for the runtime. New runtime code uses `get_logger`, never `print`. |
| `../supabase_client.py` | `SupabaseWriter` — psycopg connection to Supabase Postgres. Bypasses RLS because it connects as the `postgres` role (equivalent to PostgREST's service_role). `create_match` is the **atomic** create (match + pucks + seed snapshot in one transaction). |

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

## Why MatchManager is in-process (and the lock seam)

Pilot scale is one bar, ≤4 concurrent matches. Storing match state in a
Python dict keyed by match_id is the simplest thing that works.

**The per-match lock is already in place.** `MatchManager` holds one
reentrant lock per match (`_lock_for`) and wraps `on_input` and `tick`
(and the finalise/abandon they call) in it. This already serialises the
scheduler thread against Flask request threads *within* a process, and it
closes the idempotency check-then-act window. It is also the exact seam
the multi-worker migration needs: swap `threading.RLock` for a Redis lock
keyed by `match:{id}` and the call sites don't change.

When we shard across workers (multi-bar, multi-process), the swap is:

1. Move `MatchManager.matches` to Redis with `match:{id}` keys.
2. Replace the in-process `_lock_for` RLock with a Redis lock (e.g.
   `redis-py` `Lock`) of the same per-match granularity. The
   `IdempotencyCache` likewise moves to Redis `SETNX` + TTL on the same
   key. Both are already isolated behind small interfaces.
3. Everything else (game class, Supabase writer, the connection pool)
   stays. `SupabaseWriter.with_pool` already shares one pool per process.

No premature distribution — only the seams are in place.

## Multi-lobby (one server, many tables)

`PairingManager` keys lobbies by `(location_id, table_number)`, so a
single server runs many tables at once. A puck's later calls
(dial/confirm/start/cancel) carry only `puck_index`; the manager resolves
the puck's lobby via a `puck_index -> lobby key` locator populated at
`request_code`. Constraint: `puck_index` is unique per location for the
pilot fleet. When a location outgrows a single index space, the puck
calls must carry `table_number` explicitly (the route already threads it
through `lobby-state`).

**Deferred — lobby state via Realtime (Tier 2 item 12).** The TV still
polls `/api/runtime/pair/lobby-state` at 1 Hz. The planned move is to
mirror each lobby mutation into a Supabase table the TV subscribes to via
Realtime (same channel mechanism as `matches`), which removes the poll
and makes lobby state shared across workers for free. Not yet done — it
needs a `lobbies` table + RLS + the PairingManager writing on every
mutation; tracked here so it isn't lost.

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

## Production-hardening status (2026-06-05 pass)

**Tier 1 (all):** per-game disconnect adapters; pytest + jest harness with
CI; transactional match creation; input idempotency; abandoned-match
sweep; monotonic cue `seq` (server + TV dedupe); TV Realtime resubscribe;
structured logging + optional Sentry.

**Tier 2 (in progress):** per-match lock (the Redis-lock seam, done
in-process); `SupabaseWriter.with_pool` connection pool; multi-lobby per
`(location_id, table_number)`. Deferred: Redis-backed match state (lock +
idempotency seams in place), lobby-via-Realtime (item 12).

**Review Open items closed this pass:** duplicate-`puck_index` guard;
idempotency check-then-act now atomic under the per-match lock; Flask boot
logging + Sentry-capturing error handler.

Full edge-case review:
`docs/audit/runtime-hardening-review-2026-06-05.md`.

Known-accepted limitations (see the review): a disconnected puck is
retired for the match (no mid-match reconnect); a server restart mid-match
loses in-memory state (and resets cue `seq`) until runtime state is
Redis-backed; RN-side Sentry not yet wired (Flask + runtime are).

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
