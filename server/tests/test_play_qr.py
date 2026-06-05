"""
Tests for the patron bind UI surface (ADR 0005): the QR endpoint the TV
shows and the /play/<id> page the phone opens.

The QR route is exercised through the real Flask blueprint with a fake
container (no DB); qrcode rendering is asserted only when the lib is present
(the runtime CI job installs a minimal set), but the play_url text fallback
is always returned. The /play page render is guarded on flask_socketio
(init_runtime_routes wires the socket handlers).
"""

from __future__ import annotations

import os

import pytest
from flask import Flask

import runtime_routes
from runtime import MatchManager, registry

from conftest import FakeWriter, make_players
from games.speed_pyramid import Question


_TEMPLATES = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "templates")
)


def _fixture():
    return [
        Question(
            id=1, setup="s", question="q",
            answers={"A": "a", "B": "b", "C": "c", "D": "d"},
            correct="A", category="T", time_limit_ms=10_000,
        )
    ]


@pytest.fixture(autouse=True)
def _reset_container():
    yield
    runtime_routes._container = None


def _match_in_container():
    mm = MatchManager(registry=registry, writer=FakeWriter())
    match = mm.create(
        location_id="loc-1", game_slug="speed_pyramid", table_number=1,
        players=make_players(2), questions=_fixture(),
    )
    runtime_routes._container = {"manager": mm}
    return match


def test_qr_returns_play_url_for_known_match():
    match = _match_in_container()
    app = Flask(__name__)
    app.register_blueprint(runtime_routes.runtime_bp)
    client = app.test_client()

    resp = client.get(f"/api/runtime/match/{match.id}/qr")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["play_url"].endswith(f"/play/{match.id}")
    # When the QR lib is installed, a PNG data URI is rendered too.
    try:
        import qrcode  # noqa: F401

        assert data["qr_code"].startswith("data:image/png;base64,")
    except ImportError:
        assert data["qr_code"] is None  # graceful fallback


def test_qr_404_for_unknown_match():
    _match_in_container()
    app = Flask(__name__)
    app.register_blueprint(runtime_routes.runtime_bp)
    client = app.test_client()
    resp = client.get("/api/runtime/match/does-not-exist/qr")
    assert resp.status_code == 404


def test_play_page_renders_with_match_id():
    pytest.importorskip("flask_socketio")
    from flask_socketio import SocketIO

    match = _match_in_container()
    app = Flask(__name__, template_folder=_TEMPLATES)
    sio = SocketIO(app, async_mode="threading")
    runtime_routes.init_runtime_routes(app, sio)
    client = app.test_client()

    resp = client.get(f"/play/{match.id}")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    # The match id is injected into the page's JS, and it binds via the API.
    assert match.id in body
    assert "/bind" in body
