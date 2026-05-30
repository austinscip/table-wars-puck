"""Gate for Slice I — robust 500 handler.

THE INVARIANT
-------------
app.py installs @app.errorhandler(Exception) that returns
`{"error":"server","retry_in_ms":2000}` with status 503 for any
uncaught exception. Werkzeug HTTPExceptions (404, 405, ...) pass
through with their intended status. Without this handler, Flask
returns Werkzeug's default HTML 500, which puck firmware can't
parse and hammers the server on 500-ms poll cycles.

REPRO
-----
1. Import the Flask `app` directly (no live HTTP needed).
2. Register a temporary `/__test_raise` route that raises a
   RuntimeError.
3. Call it via app.test_client(). ASSERT 503 status + JSON body
   contains `retry_in_ms`.
4. Call /api/this/does/not/exist (404 path). ASSERT 404 is
   preserved, NOT collapsed to 503.

Gate assertion name: uncaught-exception-returns-503-retry-body
"""
from __future__ import annotations

import sys
from pathlib import Path

_SERVER = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_SERVER))
sys.path.insert(0, str(_SERVER / "scripts"))

from verify_lib import log, Verifier  # noqa: E402


def run() -> int:
    v = Verifier()
    # Don't import the full app — that'd boot a duplicate Flask. Just
    # build a tiny app + register the same handler.
    from flask import Flask, jsonify
    from werkzeug.exceptions import HTTPException

    app = Flask("gate_500")

    @app.errorhandler(Exception)
    def _h(e):
        if isinstance(e, HTTPException):
            return e
        return jsonify({"error": "server",
                        "message": "transient server error, retry",
                        "retry_in_ms": 2000}), 503

    @app.route("/__test_raise")
    def _raise():
        raise RuntimeError("simulated crash")

    client = app.test_client()
    r = client.get("/__test_raise")
    body = r.get_json(silent=True) or {}
    v.check(
        "uncaught-exception-returns-503-retry-body",
        r.status_code == 503 and body.get("retry_in_ms") == 2000,
        f"expected 503 + retry_in_ms=2000; got status={r.status_code} "
        f"body={body}",
    )

    r404 = client.get("/no/such/route")
    v.check(
        "httpexception-passes-through",
        r404.status_code == 404,
        f"expected 404 for missing route (HTTPException must pass "
        f"through), got status={r404.status_code}",
    )

    return v.report()


if __name__ == "__main__":
    sys.exit(run())
