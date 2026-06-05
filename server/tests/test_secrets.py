"""
Tests for secret handling (Tier 3, item 16): log redaction (always on)
and the opt-in post-boot env scrub.
"""

from __future__ import annotations

import logging
import os

from runtime import harden_secrets, redact
from runtime.log import RedactingFilter, scrub_env


def test_redacts_postgres_dsn():
    out = redact("connecting to postgresql://user:s3cr3t@db.host:5432/app")
    assert "s3cr3t" not in out
    assert "postgresql://user:<redacted>@db.host:5432/app" in out


def test_redacts_bare_jwt_signature_keeps_header():
    jwtish = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.SUPERSECRETSIGNATURE123"
    # Bare (not behind token=) so the JWT-specific rule applies and keeps
    # header.payload for debuggability while dropping the signature.
    out = redact(f"verifying bearer {jwtish} now")
    assert "SUPERSECRETSIGNATURE123" not in out
    assert "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0." in out


def test_token_eq_value_fully_redacted():
    # When a secret is presented as token=<value>, redact the whole value.
    jwtish = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.SUPERSECRETSIGNATURE123"
    assert "SUPERSECRETSIGNATURE123" not in redact(f"token={jwtish}")


def test_redacts_keyed_secrets():
    assert "hunter2" not in redact("password=hunter2&user=bob")
    assert "abc123" not in redact("api_key=abc123")


def test_redacting_filter_scrubs_record_args():
    flt = RedactingFilter()
    record = logging.LogRecord(
        name="t",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="dsn is %s",
        args=("postgres://u:p4ss@h/db",),
        exc_info=None,
    )
    assert flt.filter(record) is True
    assert "p4ss" not in (record.msg % record.args)


def test_scrub_env_removes_named_vars(monkeypatch):
    monkeypatch.setenv("FAKE_SECRET_XYZ", "value")
    assert os.environ.get("FAKE_SECRET_XYZ") == "value"
    scrub_env("FAKE_SECRET_XYZ")
    assert "FAKE_SECRET_XYZ" not in os.environ


def test_harden_secrets_is_opt_in(monkeypatch):
    monkeypatch.delenv("SCRUB_SECRETS_AFTER_BOOT", raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgres://u:p@h/db")
    assert harden_secrets() is False
    # Still present because the flag is off.
    assert os.environ.get("DATABASE_URL") == "postgres://u:p@h/db"


def test_harden_secrets_scrubs_when_enabled(monkeypatch):
    monkeypatch.setenv("SCRUB_SECRETS_AFTER_BOOT", "1")
    monkeypatch.setenv("DATABASE_URL", "postgres://u:p@h/db")
    monkeypatch.setenv("PUCK_JWT_SECRET", "x" * 40)
    assert harden_secrets() is True
    assert "DATABASE_URL" not in os.environ
    assert "PUCK_JWT_SECRET" not in os.environ
