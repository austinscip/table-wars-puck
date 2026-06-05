"""
Unit tests for PlayerIdentity (ADR 0005) — token generation + hashing.
Pure (no DB), so these run everywhere.
"""

from __future__ import annotations

from runtime import PlayerIdentity


def test_token_is_high_entropy_and_unique():
    ident = PlayerIdentity()
    a, b = ident.new_token(), ident.new_token()
    assert a != b
    assert len(a) >= 32  # url-safe base64 of 32 bytes


def test_hash_token_is_stable_and_distinct():
    h = PlayerIdentity.hash_token("the-token")
    assert h == PlayerIdentity.hash_token("the-token")  # stable
    assert h != PlayerIdentity.hash_token("other-token")
    assert len(h) == 64  # sha256 hex
    assert "the-token" not in h  # never the raw token


def test_phone_recovery_disabled_without_pepper():
    ident = PlayerIdentity()
    assert ident.phone_recovery_enabled is False
    assert ident.hash_phone("313-555-1212") is None


def test_phone_hash_normalises_formatting():
    ident = PlayerIdentity(phone_pepper="pepper-secret")
    assert ident.phone_recovery_enabled is True
    # Same digits, different formatting -> same key.
    assert ident.hash_phone("(313) 555-1212") == ident.hash_phone("3135551212")
    # Different number -> different key.
    assert ident.hash_phone("3135551212") != ident.hash_phone("3135551213")


def test_phone_hash_is_peppered():
    # The pepper changes the hash, so a stolen DB without the pepper can't
    # rainbow-table the (small) phone space.
    a = PlayerIdentity(phone_pepper="pepper-A").hash_phone("3135551212")
    b = PlayerIdentity(phone_pepper="pepper-B").hash_phone("3135551212")
    assert a is not None and b is not None
    assert a != b
    assert len(a) == 64


def test_phone_hash_rejects_implausible_numbers():
    ident = PlayerIdentity(phone_pepper="pepper")
    assert ident.hash_phone("") is None
    assert ident.hash_phone("123") is None  # too short
    assert ident.hash_phone("abc-def") is None  # no digits
