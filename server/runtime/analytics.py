"""
Product analytics (PostHog) — per-game pilot metrics (master-plan step 63).

Dormant by default, mirroring the Sentry posture in log.py: a no-op unless
`POSTHOG_API_KEY` is set AND the `posthog` SDK is installed, so dev/test and
minimal deploys need neither the key nor the dependency. Enabling it is an
opt-in operator decision (`pip install posthog` + set the key) — the plumbing
is ready so that decision doesn't require a code change.

Privacy: events carry only non-PII operational properties (game slug, table
number, player COUNT, duration, status). The `distinct_id` is the venue
`location_id` (a tenant UUID, not a person). No puck answers, names, phone
hashes, or secrets are ever captured.
"""
from __future__ import annotations

import os
from typing import Any, Optional

from .log import get_logger

_log = get_logger("analytics")

_CLIENT: Any = None
_INITED = False


def init_analytics() -> bool:
    """Initialise PostHog if POSTHOG_API_KEY is set and the SDK is installed.
    Returns True when analytics is active. No-ops (returns False) otherwise.
    Idempotent — safe to call on every worker boot."""
    global _CLIENT, _INITED
    if _INITED:
        return _CLIENT is not None
    _INITED = True
    key = os.environ.get("POSTHOG_API_KEY")
    if not key:
        return False
    try:
        from posthog import Posthog
    except ImportError:
        _log.warning(
            "POSTHOG_API_KEY is set but the posthog SDK is not installed; "
            "product analytics is OFF. `pip install posthog` to enable."
        )
        return False
    host = os.environ.get("POSTHOG_HOST", "https://us.i.posthog.com")
    try:
        _CLIENT = Posthog(project_api_key=key, host=host)
    except Exception:  # noqa: BLE001 — never let telemetry init break boot
        _log.exception("PostHog init failed; analytics OFF")
        _CLIENT = None
        return False
    _log.info("PostHog analytics enabled (host=%s)", host)
    return True


def capture(distinct_id: str, event: str,
            properties: Optional[dict] = None) -> None:
    """Fire-and-forget product event. No-op when analytics is off. NEVER
    raises into the caller — a telemetry hiccup must not break gameplay."""
    if _CLIENT is None:
        return
    try:
        _CLIENT.capture(
            distinct_id=str(distinct_id),
            event=event,
            properties=properties or {},
        )
    except Exception:  # noqa: BLE001
        _log.exception("PostHog capture failed for event=%s", event)


def reset_for_test() -> None:
    """Test hook: clear the module singleton so a test can re-init."""
    global _CLIENT, _INITED
    _CLIENT = None
    _INITED = False
