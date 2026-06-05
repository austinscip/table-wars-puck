"""
Player identity tokens + hashing (ADR 0005).

A Player is identified by an opaque, high-entropy token delivered via QR and
held on the patron's phone. The server stores only a HASH of it, so a DB leak
can't impersonate a player. The token's 256 bits of entropy make a plain
SHA-256 safe (not brute-forceable).

Phone numbers — optional, for cross-device recovery — are the opposite: a
phone number is low-entropy and trivially enumerable, so a bare hash is
plaintext-equivalent. They are keyed with an HMAC under a server-held pepper
instead, and phone recovery is simply DISABLED when no pepper is configured
(we won't store weakly-protected PII).

This module is pure (no DB, no Flask) so it's trivially unit-testable; the
SupabaseWriter does the persistence.
"""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from typing import Optional


class PlayerIdentity:
    def __init__(self, phone_pepper: Optional[str] = None) -> None:
        # When unset, phone recovery is disabled (hash_phone returns None).
        self.phone_pepper = phone_pepper or None

    @staticmethod
    def new_token() -> str:
        """A fresh opaque player token (URL-safe, ~256 bits)."""
        return secrets.token_urlsafe(32)

    @staticmethod
    def hash_token(token: str) -> str:
        """Stable lookup key for a token. SHA-256 is safe here because the
        token is high-entropy."""
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @property
    def phone_recovery_enabled(self) -> bool:
        return bool(self.phone_pepper)

    def hash_phone(self, phone: str) -> Optional[str]:
        """Peppered HMAC of a normalised phone number, or None when phone
        recovery isn't configured or the input isn't a plausible number.
        Normalisation strips everything but digits so formatting differences
        ('(313) 555-1212' vs '3135551212') resolve to the same key."""
        if not self.phone_pepper:
            return None
        digits = re.sub(r"\D", "", phone or "")
        if len(digits) < 7:  # not a plausible phone number
            return None
        return hmac.new(
            self.phone_pepper.encode("utf-8"),
            digits.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
