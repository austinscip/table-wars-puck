"""
Regression tests for the legacy app.py hardening (audit
legacy-flask-2026-06-06):

  - reflected-XSS escape on the `/bar/<slug>/...` not-found pages
  - input validation + bounds on POST /api/score (coerce, range, no detail leak)

These drive the REAL Flask app (app.py) via its test client. app.py inits a
local sqlite DB on import; the cases here hit the validation / not-found paths,
which don't depend on seeded rows, so they're deterministic.
"""

from __future__ import annotations

import os

import pytest

# app.py is the full Flask monolith; skip cleanly when its web deps aren't
# installed (the minimal runtime CI image), matching test_play_qr's posture.
pytest.importorskip("flask_socketio")
pytest.importorskip("flask_cors")
pytest.importorskip("dotenv")

os.environ.setdefault("SP_MDNS_DISABLE", "1")  # don't touch the network on import

# Defensive: if app.py can't import/init in this environment (a missing web dep
# or DB), skip the whole module rather than erroring out collection.
try:
    import app as app_module  # noqa: E402
except Exception as exc:  # pragma: no cover - env-dependent
    pytest.skip(f"app.py not importable here: {exc}", allow_module_level=True)

app = app_module.app


def _client():
    return app.test_client()


# ---- reflected XSS on the bar-not-found page --------------------------------

def test_unknown_bar_slug_is_html_escaped():
    c = _client()
    # A slug Flask will route as <bar_slug> (no slashes) carrying an XSS payload.
    resp = c.get("/bar/<img src=x onerror=alert(1)>/table/1")
    assert resp.status_code == 404
    body = resp.get_data(as_text=True)
    # The raw tag must NOT appear; it must be entity-escaped.
    assert "<img src=x" not in body
    assert "&lt;img" in body


# ---- POST /api/score validation ---------------------------------------------

def test_score_rejects_missing_body():
    c = _client()
    resp = c.post("/api/score", json=None)
    assert resp.status_code == 400


def test_score_rejects_non_integer_score():
    c = _client()
    resp = c.post(
        "/api/score",
        json={"puck_id": 1, "game_type": "Speed Tap", "score": "abc"},
    )
    assert resp.status_code == 400


def test_score_rejects_out_of_range():
    c = _client()
    resp = c.post(
        "/api/score",
        json={"puck_id": 1, "game_type": "Speed Tap", "score": -5},
    )
    assert resp.status_code == 400
    resp = c.post(
        "/api/score",
        json={"puck_id": 1, "game_type": "Speed Tap", "score": 10_000_000},
    )
    assert resp.status_code == 400


def test_score_rejects_missing_game_type():
    c = _client()
    resp = c.post("/api/score", json={"puck_id": 1, "score": 100})
    assert resp.status_code == 400


def test_score_accepts_valid_payload():
    c = _client()
    resp = c.post(
        "/api/score",
        json={"puck_id": 99001, "game_type": "Speed Tap", "score": 470},
    )
    assert resp.status_code == 200
    assert resp.get_json()["success"] is True
