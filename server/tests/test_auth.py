"""
Tests for puck authentication (Tier 3, item 13).

The token is the security boundary that stops anyone on bar Wi-Fi from
POSTing input as any puck, so these are deliberately adversarial: wrong
puck, wrong venue, expired, tampered, missing.
"""

from __future__ import annotations

import jwt
import pytest

from runtime import AuthError, MatchTokenAuthority, MatchManager, PairingManager, registry

from conftest import FakeWriter


# >= 32 bytes so the authority's minimum-length check passes.
SECRET = "test-secret-please-rotate-0123456789-abcdef"


def test_issue_then_verify_roundtrip():
    auth = MatchTokenAuthority(SECRET)
    token = auth.issue("loc-1", 3, table_number=1, now=1000)
    claims = auth.verify(token, "loc-1", 3, now=1100)
    assert claims.puck_index == 3
    assert claims.location_id == "loc-1"
    assert claims.table_number == 1


def test_token_for_one_puck_rejected_for_another():
    auth = MatchTokenAuthority(SECRET)
    token = auth.issue("loc-1", 3, table_number=1, now=1000)
    with pytest.raises(AuthError, match="puck mismatch"):
        auth.verify(token, "loc-1", 5, now=1100)


def test_token_for_one_venue_rejected_for_another():
    auth = MatchTokenAuthority(SECRET)
    token = auth.issue("loc-A", 3, table_number=1, now=1000)
    with pytest.raises(AuthError, match="location mismatch"):
        auth.verify(token, "loc-B", 3, now=1100)


def test_expired_token_rejected():
    auth = MatchTokenAuthority(SECRET, ttl_seconds=60)
    token = auth.issue("loc-1", 3, table_number=1, now=1000)
    # 1000 + 60 = 1060 expiry; verify at 2000 is past it.
    with pytest.raises(AuthError, match="expired"):
        auth.verify(token, "loc-1", 3, now=2000)


def test_tampered_token_rejected():
    auth = MatchTokenAuthority(SECRET)
    token = auth.issue("loc-1", 3, table_number=1, now=1000)
    tampered = token[:-3] + ("abc" if not token.endswith("abc") else "xyz")
    with pytest.raises(AuthError):
        auth.verify(tampered, "loc-1", 3, now=1100)


def test_token_signed_with_other_secret_rejected():
    issuer = MatchTokenAuthority("attacker-secret-also-32-bytes-long-xxxxx")
    forged = issuer.issue("loc-1", 3, table_number=1, now=1000)
    verifier = MatchTokenAuthority(SECRET)
    with pytest.raises(AuthError):
        verifier.verify(forged, "loc-1", 3, now=1100)


def test_short_secret_rejected():
    with pytest.raises(ValueError, match="at least 32 bytes"):
        MatchTokenAuthority("too-short")


def test_missing_token_rejected():
    auth = MatchTokenAuthority(SECRET)
    with pytest.raises(AuthError, match="missing token"):
        auth.verify("", "loc-1", 3, now=1100)


def test_wrong_scope_rejected():
    # A token with a different scope (e.g. minted for some other purpose)
    # must not pass as a puck-input token.
    bad = jwt.encode(
        {"scope": "admin", "loc": "loc-1", "idx": 3, "tbl": 1,
         "iat": 1000, "exp": 9_999_999_999},
        SECRET,
        algorithm="HS256",
    )
    auth = MatchTokenAuthority(SECRET)
    with pytest.raises(AuthError, match="scope"):
        auth.verify(bad, "loc-1", 3, now=1100)


def test_empty_secret_rejected():
    with pytest.raises(ValueError):
        MatchTokenAuthority("")


# --- Pairing integration ---


def _pairing(token_authority=None):
    writer = FakeWriter()
    mm = MatchManager(registry=registry, writer=writer)

    class _Resolver:
        def ensure_puck(self, puck_index, location_id):
            return f"uuid-{puck_index}"

    return PairingManager(
        match_manager=mm,
        puck_resolver=_Resolver(),
        token_authority=token_authority,
    )


def test_pairing_includes_token_when_authority_set():
    auth = MatchTokenAuthority(SECRET)
    pm = _pairing(token_authority=auth)
    resp = pm.request_code(1, "speed_pyramid", "loc-1", 1)  # host
    assert resp["token"], "host should receive a token"
    # The issued token verifies for this puck + location.
    claims = auth.verify(resp["token"], "loc-1", 1)
    assert claims.puck_index == 1


def test_pairing_token_is_none_without_authority():
    pm = _pairing(token_authority=None)
    resp = pm.request_code(1, "speed_pyramid", "loc-1", 1)
    assert resp["token"] is None
