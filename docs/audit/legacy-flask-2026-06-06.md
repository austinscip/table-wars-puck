# Legacy Flask Stack Audit (2026-06-06)

Area **Legacy Flask stack** from `AUDIT-PROGRAM.md`. Ran the playbook: 4
parallel adversarial agents (SQLi/DB, authz/open-endpoints, input-validation/
DoS, secrets/config/XSS), then re-graded hard against the real code **and the
actual deployment + trust model**.

## Scope & threat model

`server/app.py` (885 lines, ~40 direct `@app.route` handlers) + the legacy
game blueprints `trivia_routes.py` (744), `tv_game_routes.py` (310),
`multiplayer_routes.py` (188), plus the engines/DB they call. Wired via
`init_*_routes(app, socketio)` at the bottom of `app.py`.

**Deployment**: can be internet-facing (Railway via `Dockerfile`; `nginx/`
terminates TLS on :443) OR bar-LAN (`http://192.168.1.x:5001`, mDNS). So the
audit assumes **internet-reachable is possible**.

**Trust model (critical for calibration)**: pucks have **no identity or auth
token** — they POST `puck_id` in plaintext (see the firmware audit). This is
true for the LIVE Speed Pyramid endpoints (`/api/sp/*`, `pair_routes.py`) too,
not just the legacy stack. So "any client can POST a score / start a game"
is an *architectural property of the puck protocol*, not a legacy-specific bug,
and it cannot be fixed by bolting `@require_admin` onto game endpoints without
breaking every puck. The legacy `multiplayer`/`tv_game` blueprints (the old
"games 52-73") are also largely **superseded** by Speed Pyramid yet still
mounted.

This audit therefore fixes the **deploy/config hardening + injection/validation
defects that are real and safe to fix**, and **documents** the open-endpoint
posture with the honest framing above (the strategic fix is network isolation +
retiring superseded blueprints + the existing `pair_routes` token path — a
redesign, not a hardening pass).

---

## Findings by tier (re-graded)

### HIGH

**H1 — `DEBUG` defaulted to `'True'`.** `app.py` (run block):
`debug = os.environ.get('DEBUG', 'True').lower() == 'true'`. A deploy that
doesn't explicitly set `DEBUG=false` (a fresh Railway deploy, a local box used
as prod) runs the **Werkzeug interactive debugger = remote code execution** if
reachable. Prod compose sets `DEBUG=False`, but the *default* must be safe.
**Fixed:** default `'False'`; opt into the debugger with `DEBUG=true` for local
dev.

**H2 — Reflected XSS on the bar-not-found pages.** Four handlers did
`return f"Bar '{bar_slug}' not found", 404`, and a bare-string Flask return is
served as `text/html`, so `bar_slug = "<img src=x onerror=alert(1)>"` reflects
as live HTML. **Fixed:** `escape(bar_slug)` (markupsafe) on all four sites.
Regression-tested.

### MEDIUM

**M1 — SocketIO CORS hardcoded `*`.** `socketio = SocketIO(app,
cors_allowed_origins="*", …)` ignored the configurable HTTP `CORS_ALLOWED_ORIGINS`
— so the websocket accepted connections from **any** origin even when the HTTP
API was locked down (a real cross-origin-websocket lever onto the unauthenticated
socket event handlers). **Fixed:** the socket now derives its allowed origins
from the same `CORS_ALLOWED_ORIGINS` env (`*` only in dev).

**M2 — `/api/score` input not validated; leaked exception detail.** Took
`request.get_json()` (a missing/wrong Content-Type → `None` → AttributeError →
503 storm under the puck's tight poll), passed `score` unbounded into the DB,
and returned `str(e)` to the caller on error. **Fixed:** `get_json(silent=True)`,
coerce `puck_id`/`score` to int, bound `score` to `[0, 1e6]`, validate
`game_type`/`session_id`, and return a generic error (traceback stays
server-side). Regression-tested.

**M3 — `SECRET_KEY` hardcoded dev fallback** (`'tablewars_secret_2024_dev'`).
A known signing key lets anyone forge Flask-signed cookies. Impact is LOWER than
the agents claimed because **nothing uses the Flask session for auth** (every
`session[...]` in the codebase is a local DB-row dict named `session`, not
`flask.session`; the admin gate is a bearer token). **Fixed (defense-in-depth):**
when `SECRET_KEY` is unset, generate a random per-process key (never the public
constant) and log a warning to set it for multi-worker stability; added
`SESSION_COOKIE_HTTPONLY` + `SameSite=Lax` (left `Secure` off so LAN http works).

### Documented / architectural (NOT bolt-on fixable — see threat model)

**A1 — Unauthenticated game/score/registration endpoints** (`/api/score`,
`/api/register`, `/api/game-start`, `/api/bars` POST, `/tv-games/*`,
`/multiplayer/*`, `/api/trivia/start|answer|skill-break/*`) and **unauthenticated
SocketIO event handlers** (`puck_input`, `multiplayer_input`, `trivia_*`). These
are open **by design** (puck protocol has no identity), and the `multiplayer`/
`tv_game` blueprints are **superseded** by Speed Pyramid. Mitigations that are
real (vs. breaking pucks):
- **Network isolation** — keep this box on the bar LAN / behind nginx with an
  IP allowlist; don't expose the raw game API to the internet.
- **Lock the socket CORS** (done, M1) so a browser on a random site can't drive
  the socket.
- **Retire/flag the superseded blueprints** — gate `multiplayer_routes` /
  `tv_game_routes` behind an env flag (default off in prod) so dead surface
  isn't mounted. (Deferred — needs confirmation nothing still calls them; the
  live firmware does still use some `trivia_routes` endpoints, so that blueprint
  can't be blanket-disabled.)
- The LIVE path (`pair_routes` `/match/<id>/input`) already supports a
  `token_authority` + rate limiter (Track G) — the model to extend if these
  endpoints ever need real auth.

**A2 — Firmware download is unauthenticated** (`/firmware/download/<version>`).
Pucks (no auth) must fetch it, so gating it would break OTA. The real fix is
**firmware code-signing** (pucks verify a signature before flashing) — already
tracked as a follow-up in `admin_auth.py`'s docstring. Deferred.

**A3 — `require_admin(strict=False)` is open when `ADMIN_API_TOKEN` is unset.**
Deliberate dev posture (documented in `admin_auth.py`). In prod, `ADMIN_API_TOKEN`
MUST be set or the non-strict admin/info endpoints are open. Firmware *publish*
is correctly `strict=True` (fails closed). Recommend a startup assertion that
`ADMIN_API_TOKEN` is set when a prod indicator is present (deferred — owner
config). Flagged below.

**A4 — Unbounded in-memory registries** (`active_sessions`, `active_games`,
`active_multiplayer_games`) with no eviction — a long-running server leaks them.
These are the **legacy** engines; the LIVE Speed Pyramid state (`_SP_STATE`) was
already hardened with ghost-sweep/reaping in Track G. Tied to retiring the
superseded blueprints (A1). Noted.

### LOW

- **`LIKE '%{region}%'`** in the regional leaderboard is **not** SQLi (the value
  is bound) — just wildcard *pattern enumeration*. Optional `ESCAPE` hardening;
  not done.
- **`allow_unsafe_werkzeug=True`** is required for the threading-mode dev server;
  kept. Prod should run under gunicorn.

---

## Re-graded DOWN / rejected

- **"SQL injection (Critical)"** — **none found.** The SQLi agent confirmed every
  `execute_query` is parameterized via `get_placeholder()`; route params, JSON
  fields, and `LIMIT` (`type=int`) are all bound, never interpolated. Genuinely
  solid.
- **"SECRET_KEY → session forgery → privilege escalation (Critical)"** —
  overstated; no Flask-session auth exists (see M3). Downgraded to
  defense-in-depth.
- **"9 CRITICAL open endpoints, add `@require_admin` to each"** — re-framed as
  A1: open *by design* (puck protocol), can't bolt admin auth without breaking
  pucks; mitigation is network isolation + retiring superseded routes, not
  per-route decorators.
- **"SPA path traversal via `send_from_directory`"** — Flask's
  `send_from_directory` blocks `../`; the candidate `isfile` check is
  belt-and-suspenders, not a traversal. Not a vuln.

## Verified solid (keep)

- **No SQL injection anywhere** — disciplined parameterization across all routes.
- Global `@app.errorhandler(Exception)` returns a generic 503 (no stack-trace
  leak) with a puck back-off hint.
- Firmware *publish/set-latest* are `@require_admin(strict=True)` (fail closed).
- Pair-room code validated (`len==6 and isdigit()`); `<int:…>` route converters
  reject non-numeric ids before handlers.
- Jinja autoescape on templates; constant-time admin token compare
  (`hmac.compare_digest`).
- Non-root Docker user; nginx security headers + TLS; deps pinned in
  `requirements.txt`.

## Deliberately deferred (with rationale)

- Per-endpoint / per-socket-event auth + session tokens for the legacy game
  stack — a redesign that would break the unauthenticated puck protocol;
  superseded by Speed Pyramid. Mitigate by network isolation + retiring the dead
  blueprints.
- Firmware code-signing (A2) — the correct fix for the open download; bigger
  workstream.
- Gating `multiplayer_routes`/`tv_game_routes` behind an env flag (A1) — needs a
  usage sweep first (live firmware still hits some `trivia_routes`).
- Startup assertion for `ADMIN_API_TOKEN` in prod (A3) — owner config decision.

## Manual follow-ups (owner)

1. In production: set `SECRET_KEY`, `ADMIN_API_TOKEN`, `CORS_ALLOWED_ORIGINS`
   (to the portal/TV origins), and keep `DEBUG` unset/false. Do **not** expose
   the raw game API to the public internet — front it with the LAN / an nginx
   IP allowlist.

---

## Resolution summary

**Fixed (verified: `mypy` clean, full pytest **248 passed**, app imports):**

- **H1** — `DEBUG` default `'True'` → `'False'` (no accidental debugger RCE).
- **H2** — reflected-XSS escape on the four `/bar/<slug>` not-found returns.
- **M1** — SocketIO CORS now driven from `CORS_ALLOWED_ORIGINS` (was hardcoded `*`).
- **M2** — `/api/score`: silent JSON parse, int coercion + range bound, generic
  error (no `str(e)` leak).
- **M3** — `SECRET_KEY` random fallback instead of the public constant + cookie
  flags.
- New regression test `tests/test_legacy_app_hardening.py` (6 cases) — first
  test to drive the `app.py` monolith via its test client.

**Documented / deferred** — A1–A4 + LOW items, with the threat-model rationale
above.
</content>
