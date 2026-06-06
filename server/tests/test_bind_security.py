"""
Tests for seat-bind security (audit 0.4 — bind-once) and mandatory puck auth
in production (audit 0.5).
"""

from __future__ import annotations

import os

import pytest
from flask import Flask

import runtime_routes
from runtime import MatchManager, PlayerIdentity, registry

from conftest import FakeWriter, make_players
from games.speed_pyramid import Question


def _fixture():
    return [
        Question(id=1, setup="s", question="q",
                 answers={"A": "a", "B": "b", "C": "c", "D": "d"},
                 correct="A", category="T", time_limit_ms=10_000)
    ]


@pytest.fixture(autouse=True)
def _reset():
    prev = os.environ.get("LOCATION_ID")
    yield
    runtime_routes._container = None
    if prev is None:
        os.environ.pop("LOCATION_ID", None)
    else:
        os.environ["LOCATION_ID"] = prev


def _client():
    os.environ["LOCATION_ID"] = "loc-1"
    writer = FakeWriter()
    mm = MatchManager(registry=registry, writer=writer)
    match = mm.create(location_id="loc-1", game_slug="speed_pyramid",
                      table_number=1, players=make_players(2),
                      questions=_fixture())
    runtime_routes._container = {
        "manager": mm, "writer": writer, "player_identity": PlayerIdentity(),
    }
    app = Flask(__name__)
    app.register_blueprint(runtime_routes.runtime_bp)
    return app.test_client(), match, writer


# --- bind-once (0.4) ---

def test_second_player_cannot_steal_a_claimed_seat():
    client, match, _ = _client()
    a = PlayerIdentity.new_token()
    b = PlayerIdentity.new_token()
    # Player A claims seat 1.
    r1 = client.post(f"/api/runtime/match/{match.id}/bind",
                     json={"puck_index": 1, "token": a})
    assert r1.status_code == 200
    # Player B tries to take seat 1 -> refused.
    r2 = client.post(f"/api/runtime/match/{match.id}/bind",
                     json={"puck_index": 1, "token": b})
    assert r2.status_code == 409


def test_same_player_can_rebind_their_own_seat():
    client, match, _ = _client()
    a = PlayerIdentity.new_token()
    client.post(f"/api/runtime/match/{match.id}/bind",
                json={"puck_index": 1, "token": a})
    # Same token re-binding the same seat is idempotent, not a 409.
    r = client.post(f"/api/runtime/match/{match.id}/bind",
                    json={"puck_index": 1, "token": a, "display_name": "Mae"})
    assert r.status_code == 200


def test_writer_bind_once_returns_false_for_foreign_claim():
    w = FakeWriter()
    assert w.bind_player_to_match_puck("mp1", "playerA") is True
    assert w.bind_player_to_match_puck("mp1", "playerA") is True   # idempotent
    assert w.bind_player_to_match_puck("mp1", "playerB") is False  # foreign


# --- mandatory puck auth in production (0.5) ---

def test_container_refuses_to_boot_unauthenticated_in_production(monkeypatch):
    monkeypatch.setenv("TABLEWARS_ENV", "production")
    monkeypatch.delenv("PUCK_JWT_SECRET", raising=False)
    runtime_routes._container = None
    # Fails fast at the top of container build, before any DB/writer setup.
    with pytest.raises(RuntimeError, match="PUCK_JWT_SECRET is required"):
        runtime_routes._get_container()


def test_is_production_detection(monkeypatch):
    for var in ("TABLEWARS_ENV", "FLASK_ENV"):
        monkeypatch.delenv(var, raising=False)
    assert runtime_routes._is_production() is False
    monkeypatch.setenv("FLASK_ENV", "production")
    assert runtime_routes._is_production() is True
