# Post-sweep follow-ups #5 — smaller / lower-confidence items (2026-06-06)

Working the grab-bag in POST-SWEEP-FOLLOWUPS #5. Fixed the concrete ones with
tests; reviewed and honestly graded the rest.

## Fixed (with tests)

**Web TV ErrorBoundary reload loop (speed-pyramid web).** The boundary
auto-reloaded the page 8 s after any render crash with no cap — a *persistent*
bad frame (one that recurs immediately on every boot) became an endless
white-flash reload every 8 s. Now counts reloads in `sessionStorage` (survives
the reload), backs off exponentially (8→16→32→60 s), and after `maxReloads`
(5) **gives up** and shows a static "needs attention" card instead of looping.
A 60 s healthy run clears the counter so isolated blips don't accumulate.
Backoff logic extracted to a pure `computeReloadPlan` + vitest tests.

**TableWarsTV ErrorBoundary flap (react-native-tvos).** This one re-renders in
place (no page reload) so it never white-flashed, but a persistently-bad frame
still flapped card↔crash every 6 s forever. Added the same backoff + give-up
guard (`computeRecoverPlan` + jest test); after the cap it holds a terminal card.

**Narration cache staleness on overlayfs.** `_narrated_qids()` invalidated on
the questions-directory mtime — verified on macOS APFS, but some container
filesystems (overlayfs) don't reliably bump a directory's mtime when a file is
added/removed inside it, which would pin a stale narrated-set until restart.
Added a 60 s TTL backstop so the set re-scans at most once per minute regardless
of mtime behavior, without making the hot path (every load-question) re-glob the
directory each call. (Existing `test_narration_cache.py` still green.)

## Reviewed — solid / deferred with rationale

**`database.py` connection + transaction robustness.** Reviewed:
- **No connection leak** — `get_db_connection()` is a contextmanager with
  `try/finally: conn.close()` on both the sqlite and psycopg paths, so every
  `execute_query` closes its connection. There is no pool (a fresh connection
  per call), which is connection *churn* but not *exhaustion* — and it's
  appropriate for the single-worker, single-venue, low-QPS deployment (the
  high-throughput runtime path uses `psycopg_pool` via `SupabaseWriter`, which
  was audited separately).
- **`?`→`%s` rewrite** (`query.replace('?', '%s')` on the Postgres path) is a
  latent footgun — it would corrupt a literal `?` in SQL (a string literal, or
  a Postgres `jsonb ?` operator). **But** every live query (pair_routes,
  trivia_database) builds placeholders via `get_placeholder()` (which is already
  `%s` on Postgres), so no query carries a stray `?` to mis-replace today
  (grep-verified). Left as-is; flagged so a future `jsonb ?` query knows to use
  the parameter path, not a literal.

**`mdns_advertise.py`.** Reviewed: best-effort by design and fully
error-contained — `register_service` wrapped in try/except, `atexit` shutdown
that `unregister_all_services()` + `close()`s the zeroconf instance, graceful
`ImportError` when zeroconf is absent. A failed advertise prints to stderr and
the server still serves (pucks can dial by IP). No bug. Solid.

**Trivia content pipeline / answer correctness.** The *code* hazard — a content
row with a dirty `correct_answer` (lowercase / whitespace / non-A-D) silently
scoring everyone wrong — was fixed in `runtime-games-2026-06-06` (RG-5:
normalize + drop unscoreable rows + fall back to defaults). Auditing the actual
**1,296 seeded questions** for factual answer correctness is a content-QA task,
not a code change — deferred to the owner.

**End-to-end live-system smoke.** The `tests/sp_harness.py` built for the live
Speed Pyramid audit is already a partial e2e: it drives the *real* Flask
pair/sp blueprints (request → start → load-question → pick/minigame → answer →
reveal → final-results) against a throwaway DB, which is most of the
"simulated puck through a full match" value without a browser. A *full* e2e
(Flask + the web TV in a headless browser + a scripted puck) is a sizeable
harness; deferred as the next infra investment, with the sp_harness noted as the
foundation to build it on.
