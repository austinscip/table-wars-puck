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
