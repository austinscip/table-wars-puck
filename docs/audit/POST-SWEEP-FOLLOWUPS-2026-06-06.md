# Post-Sweep Follow-ups (2026-06-06)

The first full pass of the audit program (`AUDIT-PROGRAM.md`) is complete — every
area is ✅. This file captures the gaps and improvements found in an honest
self-review AFTER that sweep, in priority order. Work these with the same
playbook (fan out adversarial review → triage hard, re-grade severities → fix in
priority order with a real-flow regression test → keep CI green → commit per
area on the `sandbox` branch → write/append an audit doc). CI = pytest + mypy
(server), tsc + eslint + jest (TableWarsTV), tsc + eslint + vitest
(speed-pyramid web), firmware host tests. Confirm CI green after each push
(`gh run watch`).

## 1. ✅ DONE (2026-06-06) — Audit the LIVE Speed Pyramid engine — it never got a dedicated pass

> Completed: `live-speed-pyramid-2026-06-06.md`. Fixed crash-recovery time
> rebase, double-reveal gevent race, ghost-sweep reconnect reconcile, rehydrate
> int-key/backfill drift, negative response-time. Built the first endpoint test
> harness (`server/tests/sp_harness.py`). Impersonation re-graded **by-design**
> (closed puck protocol on isolated LAN, per `legacy-flask`); a per-puck
> capability token is the one deferred high-leverage hardening — carried below.

### Carried forward from #1: per-puck capability token — ✅ DONE (2026-06-06)
`puck_id` was an assertion, not a credential. Now closed: the server issues an
opaque token on `/api/pair/request|confirm`, stored in the lobby (persisted,
never leaked in a snapshot) and required (constant-time) on every state-mutating
`sp_*`/`pair_*` write; firmware sends it. See the appendix in
`live-speed-pyramid-2026-06-06.md`. (TV control-plane endpoints remain a separate
operator-token concern, still deferred.)

### Also done (2026-06-06): the two internal robustness items
- **Writer-transaction atomicity for finalize** — `SupabaseWriter.finalize_match`
  does all final scores + the status flip in ONE idempotent transaction (no more
  stranded `active` row on a mid-batch failure). `runtime-games`/F3.
- **Idempotency persistence across restart** — recent idempotency keys are
  snapshotted with the match and re-seeded on recover, so a retry after a
  crash+restart is deduped instead of re-applied. `runtime`/F6.

### Original scope (for reference)

The deployed product runs on `server/pair_routes.py` (~2,550 lines),
`server/trivia_game_engines.py` (~484, the live scoring), and
`server/trivia_session_manager.py` (~232). The "F1–F4 games" audit
(`games-2026-06-06.md`) covered `server/games/*.py` — the **next-gen runtime**
games that feed the (non-live) TableWarsTV — NOT this live path. `pair_routes`
was only read incidentally (~5 functions: narration, match-state, /answer,
heartbeat) during the firmware/polish audits. This is the real product's core
and deserves the full per-game adversarial treatment:
- Scoring (`SpeedPyramidGame.calculate_points`/`tier_for`): negative/overflow,
  double-score, response-time edge cases, final vs round consistency.
- The round / category-pick / minigame / power-up / reveal state machine in
  `pair_routes` (`_SP_STATE`): stuck states, race between force-reveal and
  all-answered, round counters, the pending_category_pick / pending_minigame
  transitions, power-up arming/targeting.
- Untrusted `puck_id` (pucks self-report it, no token on these endpoints):
  impersonation, answer-as-another-puck, out-of-range index.
- Idempotency/double-submit, the ghost-sweep + `expected_pucks` reconciliation.
- JSON-safety of the match-state payload; serialization/crash-recovery of
  `_SP_STATE` (`state_persistence.py`).
Cross-check against the firmware (`docs/audit/firmware-2026-06-06.md`) and web TV
(`tv-speed-pyramid-web-2026-06-06.md`) since both talk to these endpoints.

> **Status (2026-06-06): items #1–#5 all DONE.** #1 `live-speed-pyramid`, #2
> `deps`, #3 self-review (folded into the fix commits), #4 firmware ANSWERING
> heartbeat (appended to `firmware-2026-06-06.md`), #5 `followups-smaller`.
> Remaining below = the OWNER manual items + the deferred-with-rationale tail
> documented in each area doc.

## 2. ✅ DONE — Dependency CVE bump (`deps-2026-06-06.md`)

The first sweep claimed "deps pinned" but never ran a CVE check. Known-vuln
versions in `server/requirements.txt`:
- `gunicorn==21.2.0` → CVE-2024-1135 (HTTP request smuggling). Bump to >=22.0.
- `flask-cors==4.0.0` → origin-bypass / log-injection CVEs. Bump to >=4.0.1 (or 5.x).
- `Flask==3.0.0` with **Werkzeug unpinned** (transitive) → can resolve to a
  Werkzeug with multipart-DoS CVEs. Bump Flask + explicitly pin Werkzeug to a
  patched version.
Also run `pip-audit` (server) and `npm audit` (portal, TableWarsTV,
speed-pyramid) and triage real hits. Bump, then run the full suite + a `pio run`
firmware compile (deps don't affect firmware, but verify server boots) before
committing — these are behaviour-affecting, not blind bumps.

## 3. Adversarially review the auditor's own work

The program is built on independent review, but all ~21 commits from the sweep
were only self-reviewed. Run a code review over the cumulative `main..sandbox`
diff (e.g. `/code-review` at high effort, or a fresh review agent) and fix
anything it surfaces. Treat the auditor's fixes with the same skepticism as the
original code.

## 4. Firmware: residual heartbeat gap + verification debt

- `firmware-2026-06-06.md` fixed ghost-sweep by sending `?puck_id=` on the
  match-state poll — but the puck only polls match-state in IDLE / LOCKED /
  CATEGORY_PICKING / MINIGAME, **not during ANSWERING**. Sum the worst-case
  answering+narration+reveal window; if it can approach `GHOST_TIMEOUT_S` (30s,
  `pair_routes`), add a heartbeat during ANSWERING too (or a dedicated
  `/api/sp/heartbeat` ping on a timer).
- The firmware fixes are review-only (compiled, never run on hardware; only the
  JSON parsers are host-tested). Consider a deeper host-test harness for the
  state machine, and/or a hardware smoke test before the next field flash.

## 5. Smaller / lower-confidence items

- **`database.py`** connection-pool + transaction robustness under load wasn't a
  dedicated pass (Track G adjacent). Pool exhaustion, leaked connections,
  the `?`→`%s` placeholder rewrite, retries.
- **Narration dir-mtime cache invalidation** (`pair_routes._narrated_qids`,
  `polish-2026-06-06.md`) was tested on macOS APFS; verify directory-mtime
  bumps on file add/remove behave the same on the Docker/overlayfs prod FS
  (if not, switch to a TTL or an explicit admin reload).
- **Web TV `ErrorBoundary`** (`server/static/games/speed-pyramid/src/components/`)
  auto-reloads every 8s with no backoff — a persistent bad frame becomes a
  reload loop. Add a retry cap / backoff (and the same applies to the
  TableWarsTV boundary's 6s recover).
- **`mdns_advertise.py`** (how pucks discover the server) and the **trivia
  content pipeline** (`trivia_database.py`, seeds, answer correctness) were never
  looked at.
- **End-to-end verification**: nothing was run as a live system (Flask + web TV +
  a simulated puck through a full match). A scripted e2e smoke would catch what
  static review + unit tests can't.

## Standing manual items for the OWNER (not code — carried from the sweep)

- Rotate the bar WiFi password (it's still in git history).
- Set prod env: `SECRET_KEY`, `ADMIN_API_TOKEN`, `DB_PASSWORD`,
  `CORS_ALLOWED_ORIGINS`; keep `DEBUG` unset/false.
- Supabase dashboard: disable public sign-ups + enable email-enumeration
  protection.
</content>
