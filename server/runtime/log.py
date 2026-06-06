"""
Structured logging + optional Sentry for the runtime.

The runtime previously had no logging framework — the tick loop swallowed
game exceptions to a bare `print()`, which means a crashing game in
production is invisible until someone reads stdout. This wires standard
Python logging (one configurable root setup) and an optional Sentry hook
so unhandled tick/finalise errors are captured off-box.

Scope: the runtime package. The legacy Flask app (`app.py`) still uses
`print()` throughout; converting it is a separate sweep. New runtime code
should call `get_logger(__name__)` and never `print()`.

Configuration (env):
  LOG_LEVEL                 default INFO
  SENTRY_DSN                if set (and sentry_sdk installed), errors ship
  SENTRY_TRACES_SAMPLE_RATE default 0.0
  ENVIRONMENT               tag on Sentry events; default "dev"
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any, Optional


_LOG_CONFIGURED = False
_SENTRY_INITED = False


# Patterns that must never reach a log sink or Sentry event. Each redacts
# the secret portion while leaving enough context to debug.
_REDACTIONS = [
    # postgres://user:PASSWORD@host -> postgres://user:<redacted>@host
    (re.compile(r"(postgres(?:ql)?://[^:/@\s]+:)[^@\s]+(@)"), r"\1<redacted>\2"),
    # JWT (header.payload.SIGNATURE) -> keep header.payload, redact sig
    (re.compile(r"(eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.)[A-Za-z0-9_-]+"), r"\1<redacted>"),
    # A sensitive key followed by `=` OR `:` and its value, in a query-string
    # or a serialized dict/JSON/header dump. The key may be padded
    # (AWS_SECRET_ACCESS_KEY, db_password) — match the sensitive word anywhere
    # in a [\w-] key. Covers both `password=x` and `"password": "x"` shapes.
    # NB: no "authorization" here — the Bearer rule below owns the
    # "Authorization: Bearer <tok>" string form (this rule would eat just
    # "Bearer" and strand the token). Structured `authorization` keys are
    # caught by _SENSITIVE_KEY.
    (re.compile(
        r"([\w-]*(?:password|passwd|pwd|api[_-]?key|secret|token"
        r"|dsn|credential)[\w-]*[\"']?\s*[=:]\s*[\"']?)[^\s&;,}\"']+",
        re.I), r"\1<redacted>"),
    # Authorization: Bearer <opaque-token> -> redact. The (?!eyJ) lookahead
    # leaves JWTs for the rule above (which keeps header.payload for debugging).
    (re.compile(r"(Bearer\s+)(?!eyJ)[A-Za-z0-9._~+/=-]+", re.I), r"\1<redacted>"),
]

# Dict KEYS whose VALUE is a secret regardless of the value's own content. The
# in-string `redact()` only catches secrets embedded as `key=value` inside ONE
# string; a Sentry event stores secrets STRUCTURED (key "password", value bare
# "hunter2"), so the leaf-string scrub alone misses them (self-review of the
# observability fix). Redacting by key closes extra/tags/breadcrumb leaks.
_SENSITIVE_KEY = re.compile(
    r"(?:password|passwd|pwd|secret|token|api[_-]?key|authorization|dsn|jwt"
    r"|credential|signing[_-]?key|private[_-]?key)", re.I)


def redact(text: str) -> str:
    for pattern, repl in _REDACTIONS:
        text = pattern.sub(repl, text)
    return text


def _scrub_event(event: Any, _depth: int = 0) -> Any:
    """Recursively redact secret-looking values from a Sentry event before it
    ships off-box. Two layers: a leaf-string `redact()` for secrets embedded in
    a message/URL, AND a by-KEY redaction so a structured `{"password": "x"}`
    in extra/tags/breadcrumbs/context is scrubbed even though the bare value
    "x" matches no in-string pattern. Belt-and-suspenders on top of the init()
    hardening (frame locals + request bodies disabled). Pure + depth-bounded so
    it's unit-testable without the Sentry SDK installed."""
    if _depth > 16:
        return event
    if isinstance(event, dict):
        out = {}
        for k, v in event.items():
            if isinstance(k, str) and _SENSITIVE_KEY.search(k):
                out[k] = "<redacted>"  # value is a secret by virtue of its key
            else:
                out[k] = _scrub_event(v, _depth + 1)
        return out
    if isinstance(event, (list, tuple)):
        return [_scrub_event(v, _depth + 1) for v in event]
    if isinstance(event, str):
        return redact(event)
    return event


class RedactingFilter(logging.Filter):
    """Scrubs secrets from log records before they hit any handler (and,
    via the Sentry logging integration, before they ship off-box)."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = redact(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {
                    k: (redact(v) if isinstance(v, str) else v)
                    for k, v in record.args.items()
                }
            else:
                record.args = tuple(
                    redact(a) if isinstance(a, str) else a
                    for a in record.args
                )
        return True


def scrub_env(*names: str) -> None:
    """Remove secret env vars from os.environ after they've been read into
    long-lived objects at boot (the runtime pool, database.py's module
    constant). A later in-process compromise then can't recover them from
    the environment. Caller must be sure nothing re-reads these per
    request — see harden_secrets()."""
    for name in names:
        os.environ.pop(name, None)


def harden_secrets() -> bool:
    """Opt-in (SCRUB_SECRETS_AFTER_BOOT=1): scrub DB/secret env vars after
    boot. Off by default because it's only safe once every consumer has
    captured its secret at import/boot (true for this codebase: the
    runtime pool and database.py both do). Returns True if it scrubbed."""
    if os.environ.get("SCRUB_SECRETS_AFTER_BOOT") not in ("1", "true", "True"):
        return False
    scrub_env("DATABASE_URL", "PUCK_JWT_SECRET", "SENTRY_DSN")
    get_logger("secrets").info("scrubbed secret env vars after boot")
    return True


def configure_logging(level: Optional[str] = None) -> None:
    """Idempotent root logging setup. Safe to call from every worker /
    container boot — only the first call installs handlers."""
    global _LOG_CONFIGURED
    if _LOG_CONFIGURED:
        return
    level_name = (level or os.environ.get("LOG_LEVEL") or "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, level_name, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    # Scrub secrets from every record on the way to any handler.
    redactor = RedactingFilter()
    for handler in logging.getLogger().handlers:
        handler.addFilter(redactor)
    _LOG_CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Namespaced logger so all runtime logs share a `tablewars.` prefix
    and can be filtered/levelled as a group."""
    return logging.getLogger(f"tablewars.{name}")


def init_sentry() -> bool:
    """Initialise Sentry if SENTRY_DSN is set and the SDK is installed.
    Returns True when Sentry is active. No-ops (and returns False) when
    the DSN is unset or the SDK isn't installed, so dev/test and minimal
    deploys don't need the dependency. Idempotent."""
    global _SENTRY_INITED
    if _SENTRY_INITED:
        return True
    dsn = os.environ.get("SENTRY_DSN")
    if not dsn:
        return False
    try:
        import sentry_sdk
    except ImportError:
        get_logger("sentry").warning(
            "SENTRY_DSN is set but sentry_sdk is not installed; "
            "error reporting is OFF. `pip install sentry-sdk` to enable."
        )
        return False
    sentry_sdk.init(
        dsn=dsn,
        traces_sample_rate=float(
            os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "0.0")
        ),
        environment=os.environ.get("ENVIRONMENT", "dev"),
        # Privacy hardening (audit observability-2026-06-06): don't ship PII,
        # exception stack-frame LOCAL VARIABLES (which routinely hold a DB
        # password / JWT / token), or request BODIES (puck answers, tokens).
        # before_send is the final net — it redacts any secret that still
        # slipped into a message/breadcrumb/tag.
        send_default_pii=False,
        include_local_variables=False,
        max_request_body_size="never",
        before_send=lambda event, _hint: _scrub_event(event),
    )
    _SENTRY_INITED = True
    return True
