"""
Puck authentication — short-lived signed capability tokens.

Threat model: pucks talk to Flask over plain HTTP on shared bar Wi-Fi.
Without auth, anyone on the network can POST input for any puck_index and
stuff the scoreboard or grief a game. The pairing handshake (dialing the
6-digit code shown on the TV) already proves a puck is physically present
at the table; this module turns that proof into a token the puck then
presents on every input.

A `MatchTokenAuthority` mints an HS256 JWT scoped to
(location_id, puck_index) when a puck enters a lobby, and verifies it on
each input. The token is short-lived (default 2h — longer than any match,
short enough that a leaked token expires by close) and bound to the puck
index, so a captured token can't be replayed as a *different* puck.

This is not a substitute for TLS — a token sniffed off plain HTTP can be
replayed as the same puck within its lifetime. It raises the floor from
"anyone can be any puck" to "you must have completed pairing at this
table, and you can only act as the puck you paired as." TLS termination at
the venue edge is the complementary deployment-side control (see the
security review).

Enforcement is gated on PUCK_JWT_SECRET being set: configure a secret in
prod to require tokens; leave it unset in dev for the open flow.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Optional

import jwt


DEFAULT_TTL_SECONDS = 2 * 60 * 60  # 2 hours — outlasts any single match.
_ALGORITHM = "HS256"
_SCOPE = "puck-input"
# RFC 7518 §3.2: an HS256 key should be at least as long as the hash
# output (32 bytes). We enforce it so a weak secret can't slip into prod.
MIN_SECRET_BYTES = 32


class AuthError(Exception):
    """Raised when a token is missing, malformed, expired, or scoped to a
    different puck/location than the request it accompanies."""


@dataclass
class PuckToken:
    location_id: str
    puck_index: int
    table_number: int
    issued_at: int
    expires_at: int


class MatchTokenAuthority:
    def __init__(
        self, secret: str, ttl_seconds: int = DEFAULT_TTL_SECONDS
    ) -> None:
        if not secret:
            raise ValueError("MatchTokenAuthority requires a non-empty secret")
        if len(secret.encode("utf-8")) < MIN_SECRET_BYTES:
            raise ValueError(
                f"PUCK_JWT_SECRET must be at least {MIN_SECRET_BYTES} bytes "
                f"(got {len(secret.encode('utf-8'))}). Generate one with "
                f"`python -c \"import secrets; print(secrets.token_urlsafe(48))\"`."
            )
        self._secret = secret
        self._ttl = ttl_seconds

    def issue(
        self,
        location_id: str,
        puck_index: int,
        table_number: int,
        now: Optional[int] = None,
    ) -> str:
        """Mint a token for a puck that has completed pairing. `now` is
        injectable for deterministic tests."""
        iat = int(now if now is not None else time.time())
        exp = iat + self._ttl
        claims: dict[str, Any] = {
            "scope": _SCOPE,
            "loc": location_id,
            "idx": int(puck_index),
            "tbl": int(table_number),
            "iat": iat,
            "exp": exp,
        }
        return jwt.encode(claims, self._secret, algorithm=_ALGORITHM)

    def verify(
        self,
        token: str,
        location_id: str,
        puck_index: int,
        now: Optional[int] = None,
    ) -> PuckToken:
        """Verify a token and assert it was issued for exactly this
        (location_id, puck_index). Raises AuthError on any mismatch."""
        if not token:
            raise AuthError("missing token")
        options = {"require": ["exp", "iat"]}
        try:
            kwargs: dict[str, Any] = {
                "algorithms": [_ALGORITHM],
                "options": options,
            }
            if now is not None:
                # PyJWT validates exp against its own clock; for a
                # deterministic test we widen leeway and check exp by hand
                # below instead of fighting the library clock.
                kwargs["options"] = {**options, "verify_exp": False}
            claims = jwt.decode(token, self._secret, **kwargs)
        except jwt.ExpiredSignatureError as e:
            raise AuthError("token expired") from e
        except jwt.InvalidTokenError as e:
            raise AuthError(f"invalid token: {e}") from e

        if claims.get("scope") != _SCOPE:
            raise AuthError("wrong token scope")
        if claims.get("loc") != location_id:
            raise AuthError("token location mismatch")
        if claims.get("idx") != int(puck_index):
            raise AuthError("token puck mismatch")

        exp = int(claims["exp"])
        if now is not None and int(now) >= exp:
            raise AuthError("token expired")

        return PuckToken(
            location_id=claims["loc"],
            puck_index=claims["idx"],
            table_number=int(claims.get("tbl", 0)),
            issued_at=int(claims["iat"]),
            expires_at=exp,
        )
