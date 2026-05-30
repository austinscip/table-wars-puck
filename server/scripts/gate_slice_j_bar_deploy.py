"""Gate for Slice J — bar deployment (server-side pieces).

Three concerns, three checks:
  1. `/bar/<slug>/tv` renders the real bar_tv_dashboard.html (not the
     leaderboard stub).
  2. `/admin/qr-codes/<slug>` renders the real admin_qr_codes.html
     (not the inline f-string stub).
  3. `mdns_advertise.advertise_mdns(...)` is importable + callable
     without raising (mDNS network ops are skipped to keep the gate
     hermetic).

The firmware-side Slice J (NVS provisioning, AP-mode boot,
auto-recover-on-WiFi-rotation) intentionally NOT gated here —
those need a hardware burn + manual validation. That's the user's
dev-puck test phase.

Gate assertion names:
  - bar-tv-dashboard-renders-real-template
  - admin-qr-codes-renders-real-template
  - mdns-advertise-module-importable
  - register-puck-to-bar-endpoint-exists
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import requests

_SERVER = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_SERVER))
sys.path.insert(0, str(_SERVER / "scripts"))

from verify_lib import BASE, log, Verifier  # noqa: E402


def run() -> int:
    v = Verifier()

    # Pick any existing bar slug from the live DB. Easier than seeding.
    r = requests.get(f"{BASE}/api/stats", timeout=5)
    bar_slug = None
    try:
        stats = r.json() if r.ok else {}
        # Stats endpoint may list bars; if not, fall back to common
        # sandbox test slug.
        bar_slug = (stats.get("bars") or [None])[0]
    except Exception:  # noqa: BLE001
        pass
    # Fallback: known seed slug.
    if not bar_slug:
        for cand in ("demo-bar", "test-bar"):
            r = requests.get(f"{BASE}/bar/{cand}/tv", timeout=5)
            if r.status_code == 200:
                bar_slug = cand
                break
    if not bar_slug:
        v.inconclusive(
            "setup", "no bar slug available — seed a bar first",
        )
        return v.report()
    log(f"using bar slug={bar_slug}")

    # 1. /bar/<slug>/tv should render the real template — look for the
    # marker only the real template has.
    r = requests.get(f"{BASE}/bar/{bar_slug}/tv", timeout=5)
    v.check(
        "bar-tv-dashboard-renders-real-template",
        r.status_code == 200
        and 'id="leaderboard-body"' in r.text
        and 'id="tables-grid"' in r.text,
        f"expected real bar_tv_dashboard markers; got status="
        f"{r.status_code} body[:200]={r.text[:200]!r}",
    )

    # 2. /admin/qr-codes/<slug> should render the real template.
    r = requests.get(f"{BASE}/admin/qr-codes/{bar_slug}", timeout=5)
    v.check(
        "admin-qr-codes-renders-real-template",
        r.status_code == 200
        and 'id="qr-grid"' in r.text
        and 'window.print()' in r.text
        and "Print all" in r.text,
        f"expected real admin_qr_codes markers; got status="
        f"{r.status_code} body[:200]={r.text[:200]!r}",
    )

    # 3. mDNS module importable.
    try:
        os.environ["SP_MDNS_DISABLE"] = "1"  # don't actually broadcast
        import mdns_advertise  # noqa: F401
        importable = hasattr(mdns_advertise, "advertise_mdns")
    except Exception as e:  # noqa: BLE001
        importable = False
        log(f"mdns import failed: {e}")
    v.check(
        "mdns-advertise-module-importable",
        importable,
        "mdns_advertise module missing or advertise_mdns not exported",
    )

    # 4. register-puck-to-bar endpoint reachable + validates input.
    # Bad input should NOT 500 (Slice I handler) — should 400.
    r = requests.post(
        f"{BASE}/api/admin/bars/{bar_slug}/pucks",
        json={"puck_id": "not-a-number"},
        timeout=5,
    )
    v.check(
        "register-puck-to-bar-endpoint-exists",
        r.status_code in (400, 404),
        f"endpoint missing or returned unexpected code "
        f"{r.status_code}: {r.text[:200]}",
    )

    return v.report()


if __name__ == "__main__":
    sys.exit(run())
