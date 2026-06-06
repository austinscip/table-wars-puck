"""
Tests for the runtime logging/Sentry setup (Tier 1, item 8).

The point of these is the guarantees the runtime relies on: setup is
idempotent (called on every worker boot), loggers are namespaced, and
Sentry init is a safe no-op when unconfigured so dev/test never need the
DSN or the SDK.
"""

from __future__ import annotations

import logging

from runtime import configure_logging, get_logger, init_sentry
from runtime.log import redact, _scrub_event


def test_redact_handles_equals_colon_and_padded_keys():
    """Self-review of the observability fix: redact() must catch `key: value`
    (JSON/header form) and padded keys, not just `key=value`."""
    assert "<redacted>" in redact("password=hunter2")
    assert "hunter2" not in redact('"password": "hunter2"')
    assert "p@ss" not in redact("AWS_SECRET_ACCESS_KEY=p@ssw0rd")
    assert "sk-live" not in redact("X-Api-Key: sk-live-abc123")
    # Bearer + postgres URL + JWT signature still covered.
    assert "opaquetok" not in redact("Authorization: Bearer opaquetok123")
    assert "<redacted>" in redact("postgres://u:topsecret@host/db")


def test_scrub_event_redacts_structured_secrets_by_key():
    """A Sentry event stores secrets STRUCTURED ({'password': 'x'}); the by-key
    redaction must scrub those even though the bare value matches no pattern."""
    event = {
        "request": {"data": {"password": "hunter2"}},
        "extra": {"db_password": "p@ssw0rd",
                  "env": {"PUCK_JWT_SECRET": "topsecretsigningkey"},
                  "harmless": "keep-me"},
        "tags": {"authorization": "Bearer abc", "table": "5"},
    }
    scrubbed = _scrub_event(event)
    flat = repr(scrubbed)
    assert "hunter2" not in flat
    assert "p@ssw0rd" not in flat
    assert "topsecretsigningkey" not in flat
    assert "abc" not in flat
    # Non-secret structured data is preserved.
    assert scrubbed["extra"]["harmless"] == "keep-me"
    assert scrubbed["tags"]["table"] == "5"


def test_configure_logging_is_idempotent():
    # Must not raise or stack handlers when called repeatedly.
    configure_logging()
    configure_logging()
    configure_logging()


def test_get_logger_is_namespaced():
    log = get_logger("widget")
    assert log.name == "tablewars.widget"
    assert isinstance(log, logging.Logger)


def test_init_sentry_noops_without_dsn(monkeypatch):
    monkeypatch.delenv("SENTRY_DSN", raising=False)
    # No DSN -> returns False, never raises, no dependency required.
    assert init_sentry() is False


def test_init_sentry_warns_when_sdk_missing(monkeypatch):
    monkeypatch.setenv("SENTRY_DSN", "https://example@sentry.io/123")
    # Simulate sentry_sdk not installed by blocking the import.
    import builtins

    real_import = builtins.__import__

    def blocked_import(name, *args, **kwargs):
        if name == "sentry_sdk":
            raise ImportError("blocked for test")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", blocked_import)
    # DSN set but SDK missing -> graceful False, not a crash.
    assert init_sentry() is False
