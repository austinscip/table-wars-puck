# Runtime games — crash-recovery / race / reconnect pass (2026-06-06)

The same dedicated treatment the live Speed Pyramid engine got
(`live-speed-pyramid-2026-06-06.md`), now extended to the **next-gen runtime**
that drives TableWarsTV: `server/runtime/` (MatchManager, scheduler, heartbeat,
persistence, match_store) + the four games in `server/games/` (speed_pyramid,
puck_golf, puck_racer, smash). Four parallel adversarial agents
(lifecycle/races, crash-recovery/serialization, disconnect/reconnect, per-game
edges), grounded in real `file:line`, then triaged and re-graded hard.

## Headline verdict

The runtime is **markedly more robust than the legacy path** — but it had the
**same reconnect-strand gap**, and a cluster of upgrade-day / wedge robustness
holes. Re-grading facts:

- **Time rebase is CONFIRMED CORRECT** (the legacy bug is absent). `match.py`
  serializes `last_input_at` as an elapsed offset and re-bases on restore
  (`:147`,`:180`); `heartbeat.py` does the same for `last_seen` + `stale_emitted`
  (`:143-166`); SpeedPyramid rebases the round timer (`:501-543`); Racer/Smash
  use accumulated-dt (no clock) and the scheduler's `prev` is fresh on boot so
  the first post-restore tick's dt is one interval, clamped — no teleport.
- **`--workers 1` + the gevent worker** (enforced) means the tick loop is a
  *greenlet*, not a preemptive OS thread (deploy README is explicit). So the
  lifecycle agent's "preemptive thread pool" race framing (F1/F2: `matches`-dict
  mutation, lock-identity) is **NOT reachable** — greenlets don't switch
  mid-iteration of a non-I/O loop. Re-graded to defensive/documented.

## Fixed (each with a real-flow regression test)

### HIGH — reconnect (the legacy gap's runtime twin)

**RG-1 — No reconnect path: a dropped puck was permanently stranded.** The
heartbeat layer supported recovery (`ping` clears `stale_emitted`) but the
game-state half was never wired — a swept puck stayed retired, and the
turn-based games kept force-scoring it zero every remaining round even after its
Wi-Fi recovered. **Fixed:** added `Game.on_puck_reconnected` (mirror of
`on_puck_disconnected`); `heartbeat.ping` now reports the reconnect transition;
`match._on_input_locked` calls the hook **before** `on_input` so the input
applies to the restored state. **SpeedPyramid + PuckGolf resume** (SP drops the
puck from `disconnected` and clears the pre-emptive forced-TIMEOUT lock on the
still-open round so it can answer; Golf clears the retired flag so the next hole
re-deals it). **PuckRacer + Smash are explicitly NON-resumable** (real-time /
elimination) — documented overrides, not accidental no-ops. Tests in
`test_reconnect.py`.

### MEDIUM — crash-recovery robustness

**RG-2 — `deserialize` KeyError dropped the WHOLE match on schema skew.** All
four games used strict `data["k"]` access, so a snapshot written before a newly
added field → `KeyError` → `deserialize_match` drops the match silently. An
"add a field + deploy + a box reboots mid-match" sequence destroyed every
in-progress table at that instant. **Fixed:** every `deserialize` now falls back
to the freshly-constructed default (`data.get(k, <ctor default>)`) for mutable
progress fields; structural collections (questions/course) stay strict (a
snapshot without those is genuinely corrupt). Test: drop a field from a real
snapshot → restore still succeeds.

**RG-3 — `PuckRacer._finalize` unguarded `max()` on empty finals.** A recovery
that dropped every racer → `ValueError` swallowed by the tick guard → match
wedged. **Fixed:** `... if finals else None`, matching the golf empty-roster
fix. Test: empty roster finalizes without raising.

**RG-4 — `RedisMatchStore.save` wrote NaN/Inf and wasn't atomic.**
`json.dumps` default emits `NaN`/`Infinity` (non-standard JSON) which poisons
the durable copy / hangs reload comparisons; and `SET` + `SADD` weren't atomic
(a `kill -9` between them leaves data written but the id missing from the active
set → silently not recovered). **Fixed:** `allow_nan=False` (surfaces a bad
float loudly at persist) + a pipeline so key-write and index-add are atomic.
Test: NaN rejected, no half-written index entry.

### LOW/MEDIUM — game-logic edges + backstops

**RG-5 — SpeedPyramid loaded unscoreable content.** `correct_answer` from the DB
was used unnormalized — a `"a"` / `" A "` row was impossible to score (every
player WRONG, reveal highlights a letter no tilt maps to). **Fixed:** normalize
to a clean uppercase A-D at the DB-load boundary and **drop** a row whose letter
isn't valid. Test: `' a '` → `A`; `'X'` row dropped.

**RG-6 — No hard match-duration ceiling.** A wedged state machine kept alive by
one idle-but-pinging puck never trips the all-stale abandon gate and would tick
forever. **Fixed:** `MAX_MATCH_DURATION_S = 3600` backstop in `_is_abandoned`,
measured off the persisted wall-clock `started_at` (survives restart). Test: an
aged match force-abandons.

**RG-7 — `tick(dt)` could run a game backward.** The scheduler clamps dt≥0, but
a direct caller didn't. **Fixed (defense-in-depth):** `dt = max(0.0, dt)` once in
`MatchManager.tick` so every game inherits the floor. Test: negative dt doesn't
rewind the race clock.

## Re-graded DOWN / not fixed (documented)

- **`matches`-dict mutation race / lock-identity-on-`_drop_lock` (lifecycle F1/F2,
  agent "High")** — not reachable under the enforced single-worker gevent model
  (the tick loop is a greenlet, not a preemptive thread; non-I/O iteration
  doesn't yield). The reap path already snapshots `list(...)` + catches
  `RuntimeError`. Documented; the health-endpoint `.values()` sum is the only
  unguarded iterator and is greenlet-safe today.
- **Banked-power free shot (per-game GOLF-1, agent "Medium")** — **NOT reachable:**
  `on_input` ignores non-current-turn pucks (`puck_golf.py:159`) and `_take_shot`
  zeros power on commit (`:395`), and a turn only passes on a shot or disconnect.
  Power cannot persist to a later turn. The agent missed both guards. Verified solid.
- **Deferred-write / idempotency-vs-durable-commit atomicity (lifecycle F3/F5)** —
  real but narrow (needs a Supabase write to fail mid-batch); the fix is a writer
  transaction, a larger change. Deferred.
- **IdempotencyCache not snapshotted (crash F6)** — a retried input within the
  few-second crash window could re-apply post-restart. Low; the Redis-backed
  cache seam exists. Deferred.
- **Racer finish-bonus scales with field size (per-game RACER-2)** — within a
  match the ordering/winner is always correct; only cross-match leaderboard
  comparability is affected. Design decision, deferred.

## Verified genuinely solid (keep)

- Time rebase across match / heartbeat / pyramid / golf / physics (the legacy
  ghost-sweep bug is absent — confirmed with file:line).
- The per-match RLock correctly serialises tick-thread vs request greenlet for
  the game-state read-modify-write; side-effecting I/O (emit, match-end writes)
  is pushed OUTSIDE the lock.
- Double-finalize is prevented by the status guards under the lock; the tick loop
  contains a single game's exception without stranding the others.
- Every game already unblocks a silent-puck round/turn/finish (the no-wedge
  property — tested in `test_disconnect.py`); abandoned matches are fully cleaned
  up (no leak).
- Atomic snapshot write (tmp+rename), set/elapsed-offset round-trips, `v:1` schema
  gate, debounced writer.

## Resolution summary

**Fixed (full suite 277 passed, +13 new; CI-scoped mypy clean):** RG-1 reconnect
(protocol + heartbeat + manager + all 4 games), RG-2 deserialize tolerance (4
games), RG-3 racer empty-finalize guard, RG-4 match_store NaN-reject + atomic
save, RG-5 SP answer normalization, RG-6 match-duration backstop, RG-7 dt clamp.
New tests: `test_reconnect.py`, `test_runtime_crash_recovery.py`,
`test_runtime_edges.py`. Deferred items above carry rationale.
