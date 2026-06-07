"""
Admin authentication gate (audit finding 0.1).

The admin + firmware-management endpoints were completely unauthenticated —
anyone who could reach the Flask box could publish an unsigned firmware that
every puck installs (fleet RCE), reassign pucks, or inject trivia content.

This module provides a `require_admin` decorator gating those endpoints on a
shared `ADMIN_API_TOKEN` (sent as `Authorization: Bearer <token>` or
`X-Admin-Token`), compared in constant time.

Two postures:
- `strict=True` (firmware publish): FAIL CLOSED — if no token is configured,
  the endpoint is refused (503). You cannot push firmware to the fleet
  without deliberately configuring the operator token.
- `strict=False` (other admin/info): gate when a token is configured; when
  it isn't, allow but log loudly (so the existing dev workflow keeps working
  and prod is locked down by setting the env). Mirrors the puck-auth posture.

Firmware integrity (code-signing signature verification before publish) is a
deeper follow-up tracked in the audit; this gate closes the open-to-anyone
hole.
"""

from __future__ import annotations

import hmac
import os
from functools import wraps

from flask import jsonify, request

from runtime import get_logger

_log = get_logger("admin_auth")


def _provided_token() -> str | None:
    header = request.headers.get("Authorization", "")
    if header.startswith("Bearer "):
        return header[len("Bearer ") :].strip()
    return request.headers.get("X-Admin-Token")


def _provided_operator_token() -> str | None:
    """Operator/TV token from a header or query param. The browser TV sends
    it as an X-Operator-Token header on control-plane fetches; the query form
    is a fallback for path-only POSTs."""
    return (
        request.headers.get("X-Operator-Token")
        or request.args.get("operator_token")
    )


def _authorized(expected: str) -> bool:
    token = _provided_token()
    return bool(token) and hmac.compare_digest(token, expected)


def require_admin(strict: bool = False):
    """Decorator gating an endpoint on ADMIN_API_TOKEN. See module docstring
    for the strict vs non-strict postures."""

    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            expected = os.environ.get("ADMIN_API_TOKEN")
            if not expected:
                if strict:
                    return (
                        jsonify(
                            {
                                "error": "admin auth not configured "
                                "(set ADMIN_API_TOKEN to manage firmware)"
                            }
                        ),
                        503,
                    )
                _log.warning(
                    "ADMIN_API_TOKEN unset — %s %s is UNAUTHENTICATED "
                    "(dev mode; set ADMIN_API_TOKEN in production)",
                    request.method,
                    request.path,
                )
                return view(*args, **kwargs)
            if not _authorized(expected):
                return jsonify({"error": "unauthorized"}), 401
            return view(*args, **kwargs)

        return wrapper

    return decorator


def require_operator(view):
    """Gate a TV/operator CONTROL-PLANE endpoint (force-reveal, start-timer,
    minigame-finish, reset) on SP_OPERATOR_TOKEN. These are meant to be driven
    only by the TV/Hub, not by a puck or a random LAN device — without this,
    any client could force a reveal to cut every round short, spam start-timer,
    or end a minigame early (security audit M2).

    Opt-in, mirroring require_admin's non-strict posture: enforced only when
    SP_OPERATOR_TOKEN is configured, otherwise open + a loud log so dev/test
    flows keep working and prod is locked down by setting the env. The token is
    handed to the TV by injecting it into the served SPA HTML (see app.py)."""

    @wraps(view)
    def wrapper(*args, **kwargs):
        expected = os.environ.get("SP_OPERATOR_TOKEN")
        if not expected:
            _log.warning(
                "SP_OPERATOR_TOKEN unset — %s %s is UNAUTHENTICATED "
                "(dev mode; set SP_OPERATOR_TOKEN in production)",
                request.method,
                request.path,
            )
            return view(*args, **kwargs)
        token = _provided_operator_token()
        if not (token and hmac.compare_digest(token, expected)):
            return jsonify({"error": "operator auth required"}), 401
        return view(*args, **kwargs)

    return wrapper
