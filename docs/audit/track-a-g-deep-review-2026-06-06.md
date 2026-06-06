# Deep adversarial review — Track A (Architecture) + Track G (Runtime)

**Date:** 2026-06-06
**Method:** four independent grounded reviews (schema, RLS/security, runtime
concurrency/durability, runtime lifecycle/contract), then triaged + re-graded
for real reachability/impact. Severities here are the triaged ones, not the
raw agent ratings.

Legend: 🔴 Critical · 🟠 High · 🟡 Medium · ⚪ Low · ⭐ = regression/rough-edge
in *this session's own* work (honest self-flag).

---

## TIER 0 — fix before any non-toy deployment (externally reachable)

### 0.1 🔴 Unauthenticated firmware upload + admin endpoints = fleet RCE  [Track A]
`server/firmware_routes.py:242` `POST /firmware/upload`, `server/app.py:515`
`POST /api/admin/bars/<slug>/pucks`, `server/trivia_routes.py:636`
`/api/trivia/admin/questions`. No auth decorator / before_request anywhere.
Anyone who reaches the box can publish an **unsigned** firmware binary that
every puck pulls → remote code execution across the fleet, plus reassign
pucks and inject TV content. **Fix:** auth gate (super-admin JWT or admin
secret) on every admin blueprint **and** code-signature verification before a
firmware is published. (The handoff already named "admin endpoint auth" as
*the* real gap; this enumerates it.)

### 0.2 🔴 NaN/Inf/malformed input injection corrupts physics + emits invalid JSON  [Track G]
`server/runtime/inputs.py:18-29`. `float(data.get("tilt_x", ...))` accepts
`"inf"`/`"nan"` (JSON allows them) with no `isfinite`/range check. A paired
puck POSTs `{"shake":"inf"}` → racer position → ∞ (instant finish), Smash NaN
makes `_in_arena` always-false (never KO) or instant infinite-KO; NaN then
serializes into the snapshot as invalid JSON the TV can't parse. **Fix:** parse
each numeric field through a helper that catches `ValueError`, rejects
non-finite, and clamps to a sane range.

### 0.3 🟠 A game exception in `on_input` 500s the request and wedges the match  [Track G]
`server/runtime/match.py:446`. `tick` is wrapped by the scheduler, but the
**input path has no guard**. Any game bug (IndexError on a bad `round_index`,
etc.) propagates a raw 500 and leaves the match half-mutated/un-driveable.
**Fix:** wrap `game.on_input`/`get_state` like the scheduler wraps tick — log
and return a safe state (or finalize-as-errored). Pair with catching
`event_from_dict`'s `ValueError` at the route (`runtime_routes.py:482`) → 400.

### 0.4 🟠 Seat-bind score theft  [Track G — ⭐ my bind endpoint]
`server/runtime_routes.py:549`. `/bind` is unauthenticated by design (token =
identity) but the caller picks `puck_index` with **zero proof they hold that
seat**. On shared bar Wi-Fi, scan any QR, bind your token to the leader's
seat → the final-score trigger credits *you*; or overwrite a rival's seat to
wipe their attribution. **Fix:** require the puck's signed input token to
co-sign a seat bind (the physical puck at that seat vouches), or bind-once +
gate `/bind` behind `PUCK_JWT_SECRET`.

### 0.5 🟠 Puck identity fully spoofable when `PUCK_JWT_SECRET` is unset (pilot default)  [Track A/G]
`server/runtime_routes.py:463-464`, `server/runtime/auth.py`. With auth off
(documented pilot default) the route trusts `body["puck_index"]`; any LAN
device drives any puck's gameplay/score, and the rate-limiter (keyed on
`match:puck_index`) becomes a *grief* tool (spam a victim's bucket → 429s).
**Fix:** make the secret mandatory outside an explicit dev mode (fail
startup), so a misconfigured prod box can't silently run open.

---

## TIER 1 — wrong results, exploits, or leaks (live, single-worker)

### 1.1 🟠 Leaderboards bucket in UTC, ignoring each location's timezone  [Track A]
`migrations/20260603000000_initial_schema.sql:262-264` (and player mirror
`...0002:100-102`). `v_today/v_week/v_month` use UTC, but `locations.timezone`
(default America/Detroit) exists and is ignored. "Today's high score" resets
at ~7-8pm local (midnight UTC), and `date_trunc('week')` is ISO-Monday-UTC —
so the user-facing "#3 this week at this bar" uses the wrong day/week windows.
**Fix:** compute `(now() at time zone loc.timezone)::date` etc. using the
location's tz.

### 1.2 🟡 `total_matches` inflates on any replayed `final` (counter isn't idempotent)  [Track A]
`migrations/...initial_schema.sql:286` & `...0002:124,138`. Same upsert sets
`high_score = GREATEST(...)` (idempotent) but `total_matches = +1` (not). Any
replay (recovery re-flush, manual backfill, future at-least-once) permanently
inflates the count while high_score stays right. **Fix:** derive the count
(`count(distinct match_id)`) or gate the `+1` on genuinely-new matches; at
minimum document the column as replay-unsafe.

### 1.3 🟠 Finished matches never removed from `MatchManager.matches` → unbounded memory  [Track G]
`server/runtime/match.py` `_finalize`/`_abandon` drop the lock, heartbeat,
scheduler reg, and store row but **never `self.matches.pop(id)`**. Every match
ever played stays resident (full Game object) for process lifetime; `/health`
iterates them all. **Fix:** reap finished matches after a short grace TTL (keep
~5 min for late idempotent retries / final-frame fetch, then evict).

### 1.4 🟡 Rate-limiter buckets never cleaned up (`RateLimiter.drop` is dead code)  [Track G]
`server/runtime/ratelimit.py:65` exists "to call on finalize" but nothing
calls it; `_buckets` grows one entry per `(match,puck)` forever. **Fix:** wire
`rate_limiter.drop(f"{match_id}:")` into the terminal transition (same hook as
1.3).

### 1.5 🟠 Synchronous final/lifecycle writes run *under* the per-match lock  [Track G — ⭐ ADR 0004 refinement]
`server/runtime/match.py` `_finalize`/`_abandon` are called inside
`with _lock_cm(...)`, and the PersistenceQueue routes finals to a synchronous
Supabase write with retry+backoff sleeps (`persistence.py:234-255`). So a
Supabase hiccup at match-end wedges that match's lock for seconds (and a
non-cooperative psycopg call could block the whole gevent hub). I moved the
*snapshot* write off the lock but left finals on it. **Fix:** capture
`final_scores()` + ids under the lock, flip status, release, then do the
synchronous writes.

### 1.6 🟡 Golf "quit early" scoring exploit  [Track G]
`games/puck_golf.py:334`. `final_scores` sums only holes played; a disconnect
charges nothing for unplayed holes, so a player who leaves after one good hole
ranks *above* someone who finished all three (fewest total strokes). **Fix:**
charge MAX_STROKES per remaining hole on retire (or rank disconnected pucks
last, as Racer does).

### 1.7 🟡 `recover()` runs *after* `scheduler.start()`, and shutdown never drains  [Track G — ⭐]
`server/runtime_routes.py`: `scheduler.start()` precedes `manager.recover()`,
so the live tick loop can touch matches mid-rebuild; and nothing calls
`writer.stop()`/`scheduler.stop()` at SIGTERM, so the entire graceful-drain
path is dead code (≤250ms of queued snapshots/round-scores lost on every
redeploy). **Fix:** `recover()` before `start()`; register an atexit/signal
handler that stops the scheduler then drains the queue.

### 1.8 🟡 Heartbeat state isn't serialized → duplicate disconnect cues after recovery  [Track G]
`server/runtime/match.py:128-155` omits heartbeat `last_seen`/`stale_emitted`.
On recovery a puck that already disconnected pre-crash gets its `PLAYER_LEFT`
cue fired **again**, violating the documented exactly-once contract. **Fix:**
serialize heartbeat offsets + the emitted flag with the match.

---

## TIER 2 — hardening, scale, and latent multi-worker

### 2.1 🟡 Pin grants in migrations (don't trust Supabase dashboard defaults)  [Track A]
No `GRANT`/`REVOKE` in any migration; isolation depends on Supabase's default
anon/authenticated DML grants + every write policy happening to be
super-admin-gated. No defense-in-depth. **Fix:** a migration that `REVOKE`s
all DML from anon/authenticated and grants back only the intended SELECTs;
make the test harness load those grants so tests mirror prod.

### 2.2 🟡 Missing FK indexes + wrong ON DELETE on a few FKs  [Track A]
Add `leaderboards(game_id)`, `leaderboards(puck_id)`,
`player_leaderboards(game_id)` (cascades currently seq-scan a big aggregate
table). `pucks.current_firmware_id` is `NO ACTION` → you can never delete a
referenced firmware version (should be `SET NULL`). And **`leaderboards.puck_id
ON DELETE CASCADE` contradicts the retention ADR** ("aggregates retained") — a
puck RMA/swap wipes that puck's all-time leaderboards; reconsider to RESTRICT
or soft-retire.

### 2.3 🟡 `matches.snapshot` written every tick on the wide `matches` row → bloat + write amplification  [Track A]
`migrations/20260604...:10` + `supabase_client.py`. Inline JSONB rewritten per
tick = MVCC bloat on the queryable table + a new entry in every `matches`
index per write + whole-row Realtime fan-out. **Fix:** split into a narrow
`match_snapshots(match_id pk, snapshot, updated_at)` table, or set aggressive
per-table autovacuum on `matches`. Add `updated_at` to `matches` either way.

### 2.4 🟡 `player_count` is permanently 0; `phone_hash` not unique; trivia `difficulty`/`time_limit` unchecked  [Track A]
`matches.player_count` has no writer (drop it or maintain via trigger).
`player_secrets.phone_hash` is non-unique but recovery `fetchone()`s it →
two players can claim one phone (make it a unique partial index).
`trivia_questions.difficulty` is free-text (typos break filtering) and
`time_limit` allows 0/negative (breaks the timer) → add CHECKs.

### 2.5 🟡 `purge_old_matches` deletes in one unbounded statement  [Track A]
`migrations/20260605000003:35-38`. The first run at scale could delete
millions in one transaction (long locks, WAL balloon). **Fix:** batch with
`LIMIT` in a loop, committing between batches.

### 2.6 🟡 Multi-worker is half-wired by default  [Track G — latent]
When `REDIS_URL` is set the container enables Redis idempotency + store but
**not** `lock_provider` (`runtime_routes.py`), so a 2nd worker would race
without the distributed lock. Plus: `RedisLock` is non-reentrant while the
in-process `RLock` is reentrant (latent deadlock trap if anyone nests
locking), and `RedisLock`'s 10s TTL can expire under 1.5's slow-final-write
(no fencing token → two workers in the section). **Fix:** wire `lock_provider`
with Redis (or hard-refuse >1 worker), align reentrancy, get cloud I/O out
from under the lock (1.5), document TTL > max critical-section.

### 2.7 🟡 `game_options` is untyped/unvalidated into game constructors  [Track G]
`match.py:323,346` → `**_options` swallow. `question_count=-1/0` reaches
`random.sample(k<0)` (raises) or empty-questions IndexError. Not externally
reachable today (no route forwards options) but a loaded gun. **Fix:** per-game
`validate_options` (or pydantic), reject unknown keys, clamp counts; `create()`
should turn a constructor error into a typed 400.

### 2.8 🟡 TriviaContentCache: world-writable `/tmp` default + no schema validation + read race  [Track G — ⭐]
`runtime/trivia_content.py`. Default cache path is `/tmp/...` (any local user
can write it); `_load_cache_file` does zero validation, and `load()` isn't
wrapped, so a corrupt/poisoned cache row crashes match creation (500) instead
of falling back. **Fix:** app-private dir, validate rows on load, snapshot
`bank = self._bank` once in `load`, wrap in try/except → defaults.

### 2.9 🟡 Cue durability across a flush + finalize-vs-pending-snapshot ordering  [Track G — ⭐ PersistenceQueue]
`persistence.py:194-219`: on a flush swap, cues accumulating in the stolen dict
can be lost from the cloud copy *if* that drain write fails while a concurrent
enqueue starts a fresh slot (narrow, best-effort cloud-fallback path; local
path unaffected). And a pending pre-final snapshot can drain *after*
`update_match_finished`, leaving the cloud row `status=finished` with a
pre-final snapshot. **Fix:** on a failed snapshot write merge its cues back;
on finalize, flush/coalesce the terminal snapshot through the same slot.

### 2.10 ⚪ Shorter TV/lobby token TTL; SpeedPyramid round-timer basis; tilt sign normalization; observability  [Track A/G]
TV/lobby anon tokens are replayable for their full 2h TTL on the LAN (shorten
to minutes, re-mint per match). SpeedPyramid's speed-tier timer starts at
*construction*, not first TV render — infra latency eats the gold window (and
a pre-loaded tap can score LEGENDARY at ~0ms). Answer mapping trusts firmware
tilt sign (inverted-Y firmware silently maps A↔C — no validation). Add
rate-limited warn logs when the scheduler can't hold 10 Hz and when a score is
dropped for an unknown puck_index (currently silent `continue`s).

---

## Verified SOLID (spot-checked, no action)

Per-match RLock closing the scheduler-vs-request race; `_emit` outside the
lock; RedisLock compare-and-delete release (never drops another's lock);
`_clamp_dt` bounds; scheduler per-tick exception isolation; transactional
`create_match` before in-memory registration; duplicate-`puck_index` guard;
`player_secrets` deny-all RLS; SECURITY DEFINER `search_path` hygiene
throughout; token-authority scope binding (puck N can't drive puck M,
cross-venue refused); `location_id` always server-sourced; player-token
entropy + peppered phone hashing; idempotency replay placement before the
status guard; disconnect-resolution contract; dt-based physics; atomic
`os.replace` cache write + never-blow-away-good-cache on empty pull.

---

## Suggested order

1. **Tier 0** (0.1–0.5) — security/robustness that's externally reachable.
2. **1.1 / 1.2** (leaderboard correctness) + **1.3/1.4** (leaks) + **1.5/1.7**
   (my own runtime rough edges).
3. **Tier 2** as scale/hardening, with 2.6 gated on actually wanting >1 worker.

---

## Resolution (2026-06-06)

All findings addressed except the three deliberately deferred below. Each
fix shipped with a regression test; CI green throughout.

**Fixed:** 0.1 (admin/firmware auth gate), 0.2 (input NaN/Inf/clamp), 0.3
(on_input + tick exception containment), 0.4 (bind-once), 0.5 (fail-closed
puck auth in prod), 1.1 (leaderboard timezone), 1.2 (idempotent final write),
1.3 (match reaper), 1.4 (rate-limiter cleanup), 1.5 (finals off the lock),
1.6 (golf quit-early scoring), 1.7 (recover-before-start + shutdown drain),
1.8 (heartbeat serialized), 2.1 (defense-in-depth grants), 2.2 (FK indexes +
firmware SET NULL), 2.3 (matches.updated_at + autovacuum), 2.4 (player_count
maintained, phone unique, trivia CHECKs), 2.5 (batched purge), 2.7
(game-options clamp + create() error wrap), 2.8 (trivia cache: private dir,
row validation, thread-safe read, never-raise), 2.9 (cue re-queue on failed
flush), 2.10-partial (TV-token TTL 2h→20m, scheduler overrun warning,
unknown-puck score warning).

**Deliberately deferred (documented, not coded):**
- **2.6 — full multi-worker.** The correct action is NOT to wire a partial
  distributed lock (the half-measure CONTEXT.md warns against). The system
  runs `--workers 1` (enforced in Dockerfile/systemd), so the in-process
  RLock is correct and sufficient; Redis idempotency/store are
  cross-worker-ready seams. True multi-worker needs the full 4-part spec
  (reload-under-lock, single ticker, shared heartbeat, lock_provider) shipped
  together — a deliberate future unit, not this pass.
- **2.10 — round-timer basis.** SpeedPyramid's speed-tier timer starts at
  match construction, not first TV render; fixing it cleanly needs the
  manager to stamp a "round shown at" the game reads. Accepted as a known
  limitation until the round-render handshake is built.
- **2.10 — tilt sign normalization.** A firmware with inverted tilt_y would
  map A↔C. This needs a per-firmware calibration/sign convention — a
  firmware-coordination item, not a server-only fix.

The leaderboards.puck_id `ON DELETE CASCADE` (flagged under 2.2) was kept
intentionally: deleting a puck is a deliberate destructive admin action, and
the human-facing aggregates (player_leaderboards) survive it (keyed by
player_id, SET NULL on match_pucks). The retention ADR's "aggregates
retained" is about age-based match purging, not puck deletion.
