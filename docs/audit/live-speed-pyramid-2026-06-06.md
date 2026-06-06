# LIVE Speed Pyramid engine — dedicated adversarial pass (2026-06-06)

Closes **POST-SWEEP-FOLLOWUPS #1** — the biggest gap from the first sweep. The
deployed product runs on `server/pair_routes.py` (~2,550 lines, the lobby +
Speed Pyramid state machine), `server/trivia_game_engines.py` (live scoring),
`server/trivia_session_manager.py`, and `server/state_persistence.py`
(crash-recovery). The earlier `games-2026-06-06.md` pass covered the *next-gen
runtime* (`server/games/*.py`) that feeds TableWarsTV — **not** this live path,
which had **zero endpoint tests** before this audit.

Four parallel adversarial agents (scoring integrity / state machine / untrusted
input / crash-recovery), each grounded in real `file:line`, then triaged and
re-graded hard against the actual deployment.

## Load-bearing deployment facts (these re-grade half the findings)

- **`--workers 1` is REQUIRED and enforced** (Dockerfile + `tablewars-runtime.service`),
  with the `GeventWebSocketWorker`. The whole `_LOBBY` / `_SP_STATE` design is
  by-design single-process. ⇒ The "multi-worker score divergence" and "preemptive
  thread pool" framings from two agents are **wrong**. BUT gevent still **yields
  at DB I/O** (prod Postgres sockets are monkey-patched), so check-then-write
  races across a DB query **are real** — that is the one concurrency class worth
  fixing (SP-S1).
- **Closed puck protocol on an isolated bar LAN** is the established posture
  (`legacy-flask-2026-06-06.md`): puck endpoints are unauthenticated **by design**,
  mitigated via network isolation, **not** per-route auth. ⇒ The entire
  impersonation family is re-graded to "consistent with the documented posture"
  (see Deferred), not new bugs.
- `app.py` has a global `errorhandler(Exception)` → clean `503`, no traceback.
  ⇒ The "unhandled `int()` → 500" class is neutralized to a self-inflicted 503.

## Fixed (each with a real-flow regression test)

All fixes land with the **first endpoint tests this path has ever had**:
`tests/sp_harness.py` (a throwaway-SQLite Flask client that drives the real
`pair`/`sp` blueprints) + `tests/test_sp_engine.py` + `tests/test_sp_recovery.py`.

### HIGH

**SP-CR1 — Crash recovery rebases nothing; a restart amplifies the crash.**
`state_persistence` stores every timestamp as an absolute `time.time()` float
(`last_seen`, `joined_at`, `expires_at`, `current_round_started_at`, pick/minigame
`started_at`/`deadline_at`), and `init_pair_routes` restored them verbatim
(`pair_routes.py` rehydrate block). After a restart even seconds later, every
deadline/last_seen is in the past, so the **first** `match-state` poll instantly
ghost-sweeps *every* puck, auto-resolves the pending pick/minigame with no input,
and measures post-restart answers as a ~minutes-long response time. The
persistence feature — whose entire purpose is bar crash-recovery — made a crash
*worse* than a plain restart-to-IDLE. **Fixed:** `_rebase_times_after_rehydrate`
shifts every absolute timestamp forward by `drift = now − saved_at`, preserving
each remaining-time / time-since gap. Tests: rebase shifts all fields; an 8s pick
still has ~8s left after a 2-minute restart.

### MEDIUM

**SP-S1 — Double-reveal double-scores the round (gevent race).**
`_maybe_emit_reveal` checked the `revealed_for_question_id` guard, then did a DB
read (a gevent yield point), then ran the cumulative-score loop, then *finally*
set the guard. The last puck's `/answer` and the TV's `/force-reveal` can both
pass the guard while one is blocked on that read, then both score the round —
corrupting the authoritative `cumulative_scores` that final-results trusts (wrong
totals, possibly wrong winner). **Fixed:** claim the round (`revealed_for_question_id
= qid`) immediately after the wait-gate, before any I/O, with no yield in between.
Test deterministically simulates the interleave (re-entry during the reveal's DB
lookup) and asserts the round scores exactly once.

**SP-S2 — Ghost sweep can strand reconnecting pucks.** A transient outage that
silences every puck >`GHOST_TIMEOUT_S` empties `expected_pucks`; the reveal gate
(`expected and not all(...)`) then short-circuits and the match auto-advances
"with nobody," and `_bump_last_seen` never re-adds a recovered puck — they're
stranded for the rest of the match. **Fixed:** `_reconcile_reconnect` re-adds a
puck to `expected_pucks` when it resumes polling, guarded so it only resurrects a
genuine reconnect (still a lobby player, match not complete) and **never** a
deliberate `/leave-match` leaver (new `left_match_pucks` set). Tests: swept puck
re-added on reconnect; explicit leaver stays out.

**SP-CR2 — `pending_minigame.fires` int keys lost on rehydrate.**
`fix_int_keys_after_rehydrate` coerced the other int-keyed dicts but missed
`pending_minigame['fires']`, so after a restart its keys are strings and the
all-fired gate (`pid in fires for pid in expected`) silently fails — a finished
minigame never recognizes it's done and real fires get overwritten by zero-point
fills. **Fixed:** added `fires` (and the new `left_match_pucks`) to the
coercion walk. Test: full JSON round-trip restores int keys and the gate passes.

**SP-CR3 — Play-Again / rehydrate dropped Slice-E fields → KeyError.**
`sp_reset` overwrote state with a literal that omitted every Slice E1/E2/E3 field,
and the rehydrate path `_SP_STATE.update`'d raw dicts bypassing the `_sp_state_for`
backfill — so the first power-up grant/activate after a Play-Again (or on an
older snapshot) hit a `KeyError`. **Fixed:** one `_fresh_sp_state` factory +
`_ensure_sp_fields` backfill shared by `_sp_state_for`, `sp_reset`, and the
rehydrate loop, so the field set can't drift. Test: every E-field survives a reset.

### LOW

**SP-S3 — Negative `response_time_ms` corrupts the tie-break.** A negative
puck-reported time survives the ±2s reconciliation when the round just started,
then is written to `trivia_answers`; final-results' `SUM/AVG(response_time_ms)`
tie-break then makes that puck look impossibly fast and win ties it shouldn't.
**Fixed:** `max(0, …)` clamp on the reported time. Test: negative input never
reaches the persisted aggregates.

## Re-graded DOWN / deferred (documented, not fixed)

- **Impersonation family (answer/fire/activate/pick/leave/host as another puck,
  control-plane `force-reveal`/`start-timer`/`minigame-finish`/`pair/clear`
  callable by anyone)** — re-graded to **by-design**, consistent with
  `legacy-flask-2026-06-06.md`: `puck_id` is an assertion, not a credential; the
  mitigation is network isolation, not per-route auth. A real fix is a per-puck
  capability token issued at `/confirm` — a sizeable architectural change the
  prior audit deliberately deferred. **Carried to the standing follow-ups** as the
  single highest-leverage hardening if the threat model ever expands to "any phone
  on the bar WiFi / one tampered puck."
- **Score divergence on state eviction (scoring-agent "Critical")** — not reachable
  under the enforced single worker; `cumulative_scores` survives match-end and is
  snapshotted, so final-results' authoritative source is intact. The only loss
  paths are admin `/clear` (intentional) or multi-worker (forbidden by deploy).
- **Writer reads live dict mid-serialize (crash-agent "High")** — not reachable
  under gevent: `_coerce_for_json` is pure (no I/O ⇒ no greenlet yield), so the
  snapshot walk runs atomically before the writer yields at file I/O. No torn read.
- **response-time tier inflation / minigame `t_ms` trust / negative tier** —
  client-trusted timings crossing the hard 3s/6s/10s cliffs. Per the LAN posture
  (pucks aren't adversarial in the deployed model) this is balance-only; the
  window guards (`t_ms<0`/`>duration → 0`) already reject the gross cheats.
- **STEAL credits a wrong-but-not-timed-out firer; minigame tie broken by
  puck_id; `derive_tier` divides by 7 while cumulative includes bonuses** —
  game-design / cosmetic-tier questions, deterministic, not correctness bugs.
  Left as-is pending a design decision (matches the games-audit tie-break stance).
- **`sp_force_reveal` lazily creates state without `_session_is_backed`;
  `sp_start_timer` unbounded** — bounded (needs a real session row) / TV-only;
  low value, deferred.
- **C2 round double-increment (state-agent "Critical")** — re-graded LOW: the live
  flow has a single TV driver that debounces `load-question`; pucks are read-only
  against round transitions (ADR-0002). The existing idempotency guard covers the
  realistic case; the residual is the same gevent-yield class as SP-S1 but only
  reachable with two concurrent question-loaders, which the deployed topology
  doesn't produce.

## Verified genuinely solid (keep — don't re-check)

- `_session_is_backed` / `sp_reset` phantom-state guards (R037/R043) — correct;
  never-paired codes can't leak orphan state.
- All SQL parameterized via `get_placeholder()` despite attacker-controlled
  `session_code`/`category_id`/`question_id` — no injection.
- STEAL settlement (`points_snapshot` taken once → order-independent mutual
  steals; exact `//2` remainder distribution; timed-out firers excluded; self/
  phantom targets rejected without consuming the item). One-shot arms cleared
  every round.
- Idempotency on the honest path: `/answer` already-answered 409, `/minigame/fire`
  already-fired, power-up one-shot `inv.remove`, repeated `/start`, reveal guard.
- `/leave-match` prunes the leaver from every per-puck structure + re-checks
  reveal/minigame so it can't wedge the all-answered gate.
- Match-end timing (R026): completes only once the FINAL question is *revealed*,
  not when round hits 7; Q7 re-issue returns the active question, not match-end.
- final-results crowns all co-leaders on an exact tie; response-time→puck_id
  ordering is deterministic. The atomic write (tmp + `os.replace`), set
  round-trip sentinel, debounced writer, and `v:1` schema gate are well-built.

## Resolution summary

**Fixed (verified: full pytest `264 passed`, +10 new; CI-scoped mypy clean):**
SP-CR1 (time rebase), SP-S1 (atomic reveal claim), SP-S2 (reconnect reconcile +
`left_match_pucks`), SP-CR2 (`fires`/`left_match_pucks` int-key restore), SP-CR3
(`_fresh_sp_state`/`_ensure_sp_fields` consolidation across reset + rehydrate),
SP-S3 (negative response-time clamp). First endpoint test harness for the live
engine (`tests/sp_harness.py`).

**Deferred (with rationale above):** per-puck capability token (by-design LAN
posture; carried to follow-ups), client-timing tier inflation, the design/
cosmetic nits. The single highest-leverage future hardening remains the puck
token — the only thing standing between "isolated LAN" and "any device on the
bar WiFi can grief a match."
