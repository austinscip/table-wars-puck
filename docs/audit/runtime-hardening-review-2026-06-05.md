# Runtime hardening — edge-case review (2026-06-05)

**Scope:** adversarial review of the production-hardening work landed this
session — per-game disconnect adapters (Tier 1 item 1), the pytest/jest
harness (item 2), and Tier 1 items 3–8 — plus edge cases carried forward
for future work. Written per the user mandate: *"so fucking
architecturally sound with no gaps whatsoever."*

Each entry is **state**: `Handled` (covered + tested), `Accepted` (a
deliberate, documented limitation for pilot scope), or `Open` (a real gap
to close before the relevant scale).

---

## 1. Disconnect adapters (committed `71b9527`)

| # | Edge case | State | Notes |
|---|---|---|---|
| 1.1 | Silent puck reconnects mid-match | **Accepted** | All four games **retire a disconnected puck for the match**. SpeedPyramid re-locks it every round via `_settle_disconnected`; the 10 Hz settle wins any race a reconnect could start, so reconnect is a non-feature at pilot. Consistent across games and documented in `runtime/CONTEXT.md`. Real reconnect support is a future enhancement (would require not force-settling until a per-round grace). |
| 1.2 | Every puck disconnects | **Handled** | Each game finalises (Golf/Smash/Racer → result or `None` winner; SpeedPyramid settles all rounds to a 0–0 `finished`). Tested: `test_puck_golf_all_disconnect_finalises`. |
| 1.3 | Heartbeat reports a disconnect only once; later SpeedPyramid rounds | **Handled** | The `disconnected` set re-settles each round so a permanent disconnect never makes a later round wait out the timer. Tested in `test_speed_pyramid_disconnect_force_locks_and_advances` (drives a 2nd round after the disconnect). |
| 1.4 | Disconnect of the current turn in Golf | **Handled** | Turn passes via `_advance_turn`; retired puck stays `hole_done` across holes via `_reset_hole_state`; `_skip_to_active_turn` prevents a deadlock when a retired puck would be "current" after a hole advance. |
| 1.5 | Racer disconnect lets a silent puck coast to a win on `BASE_SPEED` | **Handled** | `disconnected` racers are skipped in integration and excluded from finishers; `final_scores` ranks them by distance only. Tested: live racer outscores the one who left. |
| 1.6 | Double-finalise when a disconnect and a natural end coincide | **Handled** | `_finalize`/`_abandon` guard on `status`; `on_puck_disconnected` returns `None` once `self.finished`. |

## 2. Transactional match creation (item 3)

| # | Edge case | State | Notes |
|---|---|---|---|
| 2.1 | Crash mid-create leaves an orphan match / pucks-without-snapshot | **Handled** | `SupabaseWriter.create_match` wraps match + N puck rows + seed snapshot in one `conn.transaction()`. Tested structurally (single connection, single txn, rollback-on-failure) via a faked psycopg, plus manager-level "failure registers nothing". |
| 2.2 | Game constructor rejects its options after rows were written | **Handled** | Game is built **before** any DB write; bad options raise with zero side effects. |
| 2.3 | Duplicate `puck_index` in the player list | **Open (upstream)** | `match_puck_ids` is keyed by `puck_index`; a dup would collide. PairingManager guarantees unique indices today, so this is latent. Add a guard in `create()` if a future caller bypasses pairing. |

## 3. Idempotency (item 5)

| # | Edge case | State | Notes |
|---|---|---|---|
| 3.1 | Network retry double-counts a score / double-locks | **Handled** | `(match_id, puck_index, event_id)` LRU; retry replays the cached `StateUpdate` without re-applying. Tested: one round-score persists for a duplicated input. |
| 3.2 | Two concurrent retries of the same `event_id` both miss the cache | **Open** | `on_input` isn't locked per-match, so a true concurrent double-delivery has a TOCTOU window. Pilot pucks send serially (retry only after timeout), so this is unlikely; the real fix is the per-match lock from Tier 2 item 9 (Redis). Documented in `idempotency.py`. |
| 3.3 | Firmware reuses an `event_id` for two *different* events | **Accepted** | The second is dropped. Unique-per-event ids are the firmware's contract; documented. |
| 3.4 | Cached `StateUpdate` object mutated by a caller | **Accepted** | Routes only read `.state`. The same object is returned on replay; no caller mutates it. |

## 4. Abandoned-match writer (item 4)

| # | Edge case | State | Notes |
|---|---|---|---|
| 4.1 | Match sits `active` forever after everyone leaves | **Handled** | Tick sweep abandons when `all_stale` AND no input for `ABANDON_AFTER_S` (120 s ≫ 8 s stale). Tested with a neutered game so the backstop is what fires. |
| 4.2 | Brief Wi-Fi blip reaps a live table | **Handled** | The input-age gate on top of all-stale prevents it; tested (`recent_input_blocks_abandon`, `live_puck_blocks_abandon`). |
| 4.3 | Abandon races a finalise on another thread | **Handled (defensive)** | `update_match_abandoned` is guarded `where status = 'active'`, so a late sweep can't stomp a finished row. In-memory `status` may briefly disagree under true concurrency; the single-threaded scheduler doesn't hit this. |
| 4.4 | Self-finalising games make abandon redundant | **Accepted** | With all four games closing on disconnect (~8 s), abandon is a pure backstop for a future no-op-disconnect game. Intentional. |

## 5. Monotonic cue watermark (item 6)

| # | Edge case | State | Notes |
|---|---|---|---|
| 5.1 | NTP step / restart runs `ts` backwards, sticking the TV watermark | **Handled** | Server stamps a per-match monotonic `seq`; TV dedupes on `seq`, not `ts`. Tested both sides — the Python test asserts gapless monotonic seq; the jest test asserts a cue with a *smaller ts but larger seq* still dispatches. |
| 5.2 | Server restart mid-match resets `cue_seq` to 0 while the TV's `lastSeq` is high → new cues swallowed | **Accepted** | A server restart already loses all in-memory match state (the match is dead until Tier 2 Redis-backed state). The TV freezes regardless; the seq reset is a symptom, not the cause. Revisit with persistent runtime state. |
| 5.3 | Pre-`seq` snapshot during cutover | **Accepted** | TV falls back to array-index ordering so legacy cues still fire (forward progress); cross-batch dedup is impossible without a stable id, but the server always stamps `seq` now. Tested. |

## 6. TV Realtime resubscribe (item 7)

| # | Edge case | State | Notes |
|---|---|---|---|
| 6.1 | Channel errors/times out and never reconnects (TV freezes on last frame) | **Handled** | `useMatchState` re-subscribes with exponential backoff + jitter and re-fetches the row on every successful (re)subscribe to reconcile UPDATEs missed while down. Typechecks; **no automated test** — needs a manual/integration verification (induce a network drop) because mocking the channel would test the mock, not the behaviour. |
| 6.2 | `CLOSED` fired by a deliberate teardown triggers a phantom reconnect | **Handled** | Teardown sets `disposed` before `removeChannel`; the status callback early-returns on `disposed`. |
| 6.3 | `realtime.ts::subscribeToMatch` lacks the same resilience | **Accepted (dead code)** | Unused — only `useMatchState` is wired into the screens. Left as-is; harden or delete when it's adopted. |

## 7. Structured logging (item 8)

| # | Edge case | State | Notes |
|---|---|---|---|
| 7.1 | Tick-loop exception lost to stdout | **Handled** | Scheduler now `logger.exception(...)`; ships to Sentry when configured. |
| 7.2 | Sentry SDK absent / DSN unset in dev | **Handled** | `init_sentry()` no-ops gracefully (returns False, warns if DSN set but SDK missing). Tested. |
| 7.3 | Legacy `app.py` still uses `print()` everywhere | **Open** | Out of scope for this pass — runtime-only. A follow-up sweep should convert the legacy Flask app + add Sentry to the Flask error handler and the RN app (master-plan week 19, pulled earlier). |

---

## 8. Carried forward — Tier 4 smells not yet addressed

These are from the handoff's "things the user told me to also think of" and
remain **Open**; none block the disconnect/persistence work above but each
is a real product gap:

- **Smash KO credit heuristic** — credits the KO to the surviving opponent
  with the most `kos_landed`, which is wrong in 3+ FFA. Needs a real
  last-hitter tracker (`smash.py:_handle_ko`).
- **Score-direction incoherence across games** — SpeedPyramid sums
  positive, Golf negates strokes, Racer uses position+bonus. Coherent
  *within* a game (per-game leaderboards) but `score_total` is not
  cross-game normalised. Decide whether cross-game ranking is ever a
  product feature before normalising.
- **Magic constants** — Racer `GRACE_SECONDS_AFTER_FIRST_FINISH = 8`,
  SpeedPyramid timer warning at 10 s, Golf `MAX_STROKES = 6`. All
  invented; none playtested. Flag for a tuning pass.
- **Question dedup across matches** — SpeedPyramid pulls random questions
  with no `exclude_ids`, so a player can see the same 5 twice. Needs a
  recent-answers exclusion from `trivia_answers`.
- **Puck auto-provisioning** — `ensure_puck` creates a row for any new
  index. Fine for dev; production needs explicit fleet management (Tier 3).

## 9. Test coverage status

- **Python:** 25 tests (`server/tests/`), all green. Cover disconnect per
  game, happy-path play, transactional create (manager + writer),
  idempotency, abandonment, cue seq, logging.
- **TV (jest):** 6 tests for the cue dispatcher seq watermark, green.
  (`App.test.tsx` fails on a pre-existing `@react-navigation` jest
  transform issue, unrelated to this work.)
- **Untested by automation:** item 7 reconnect (needs live-socket
  integration), and the real Supabase transaction semantics (verified
  structurally via a faked driver + by code review).
