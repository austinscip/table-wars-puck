# Observability Audit (2026-06-06)

Area **Observability** from `AUDIT-PROGRAM.md` (Sentry / PostHog / structured
logging — "barely wired; audit + complete"). Focused single-area pass on the
part that IS wired (server-side logging + Sentry in `runtime/log.py`, covered by
`test_logging.py` + `test_secrets.py`), then a re-grade.

## What exists

- **Structured logging** (`runtime/log.py`): one idempotent root setup, a
  `tablewars.` namespace, and a `RedactingFilter` that scrubs secrets
  (postgres DSN password, JWT signature, `password=`/`api_key=`/`token=` blobs)
  from every log record before it hits a handler. Solid, tested.
- **Sentry** (`init_sentry`): no-ops cleanly when `SENTRY_DSN` is unset or the
  SDK isn't installed (so dev/CI don't need the dep); ships errors when
  configured. `sentry-sdk>=2.0.0` is in `requirements.txt` (prod only).
- **Secret env scrubbing** (`scrub_env` / `harden_secrets`): opt-in post-boot
  removal of `DATABASE_URL`/`PUCK_JWT_SECRET`/`SENTRY_DSN` from `os.environ`.
- **PostHog**: not wired anywhere. Client apps (web TV, portal, TableWarsTV)
  have ErrorBoundaries that only `console.error` — no remote capture.

## Findings by tier

### MEDIUM (fixed)

**O1 — Sentry shipped secrets/PII despite the log redactor.** The
`RedactingFilter` only scrubs *log records*. But Sentry, by default, also
attaches **exception stack-frame local variables** (which routinely hold a DB
password, JWT, or bearer token at the point of the throw) and **request bodies**
(puck answers, tokens) to events — none of which pass through the log filter. So
a `logger.exception(...)` or any unhandled error could exfiltrate secrets to the
Sentry project. **Fixed** in `init_sentry`:
- `include_local_variables=False` — don't ship frame locals (the biggest
  vector).
- `max_request_body_size="never"` — don't ship request bodies.
- `send_default_pii=False` — explicit (also the SDK default).
- `before_send=lambda event, _h: _scrub_event(event)` — a final net that
  recursively runs the existing `redact()` over every string in the event
  (message, breadcrumbs, tags, any leftover frame var), so a DSN/JWT/token that
  slipped into a message is still scrubbed before send. `_scrub_event` is pure +
  depth-bounded and **unit-tested without the SDK installed**.

**O2 — Authorization bearer tokens weren't redacted.** The redactor caught
`token=<v>` but not `Authorization: Bearer <opaque-token>` (the admin-gate /
puck-auth shape). **Fixed:** added a `Bearer <token>` redaction, with a `(?!eyJ)`
lookahead so JWTs are still handled by the JWT rule (which keeps
`header.payload` for debuggability). Tested.

### Documented / deferred (with rationale)

**O3 — No client-side error reporting.** The web TV, portal, and TableWarsTV
ErrorBoundaries (added in their respective audits) only `console.error`; a crash
auto-recovers but isn't reported off-box. Wiring remote capture (Sentry browser
/ react-native SDK) into three client apps is a **feature** needing a client
Sentry project + per-app DSN/config + PII review — out of scope for a hardening
pass. The boundaries already expose the hook point ("future Sentry/PostHog
hook"). **Deferred to a product/ops decision.**

**O4 — PostHog product analytics not wired.** Separate workstream (product
analytics, not error observability); server `analytics_routes` already provides
bar-level metrics from the DB. **Deferred.**

**O5 — Legacy `app.py` still uses `print()`** for many paths (noted in
`log.py`'s own docstring). Converting it to `get_logger()` is a separate sweep;
the global error handler already routes unhandled exceptions through
`_flask_log.exception` (→ Sentry, now scrubbed). **Deferred.**

## Verified solid (keep)

- `redact()` + `RedactingFilter` coverage (postgres DSN, JWT signature, keyed
  secrets, record args) — tested in `test_secrets.py`.
- `init_sentry` idempotency + clean no-op without DSN/SDK — tested in
  `test_logging.py`.
- `harden_secrets` opt-in env scrub — tested.
- The Flask global error handler returns a generic body (no stack leak to the
  client) and routes the traceback to the logger/Sentry path.

---

## Resolution summary

**Fixed (verified: `mypy` clean, full pytest **251 passed** incl. 2 new):**

- **O1** — `init_sentry` privacy hardening (`include_local_variables=False`,
  `max_request_body_size="never"`, `send_default_pii=False`, `before_send`
  event scrub via the new pure `_scrub_event`).
- **O2** — Bearer-token redaction added to `_REDACTIONS` (JWT-aware lookahead).
- New tests in `test_secrets.py`: Bearer redaction + `_scrub_event` over a
  realistic Sentry-event shape.

**Deferred** — client-side remote error capture (O3), PostHog (O4), legacy
`app.py` logging sweep (O5), with rationale above.
</content>

---

## Self-review follow-up (2026-06-06, followups #3)

A skeptical re-review of this fix found the secret-scrub was **weaker than its
comments claimed**:
- `_scrub_event` only redacted secrets embedded *within a string* (`key=value`).
  A Sentry event stores secrets **structured** (`extra={'db_password': 'x'}`,
  `tags={'authorization': '…'}`), so a bare value matched no in-string pattern
  and shipped verbatim. The init flags (`include_local_variables=False`,
  `max_request_body_size="never"`) covered frame-vars + request body, but
  `extra`/`tags`/breadcrumbs/`set_context` were exposed.
- the `key=value` regex missed the `key: value` (JSON/header) form and padded
  keys (`AWS_SECRET_ACCESS_KEY`, `db_password`).

**Fixed:** `_scrub_event` now also redacts **by dict key** (`_SENSITIVE_KEY`) —
any value under a password/secret/token/api_key/authorization/dsn/jwt/credential
key becomes `<redacted>` regardless of content — and the in-string regex now
matches `=` **or** `:` and a sensitive word anywhere in a `[\w-]` key. (The
`Bearer` rule keeps ownership of `Authorization: Bearer <tok>`.) New
`test_logging.py` cases cover the colon/padded-key forms and a structured Sentry
event with secrets in `request.data`/`extra`/`tags`; non-secret structured data
is verified preserved.
