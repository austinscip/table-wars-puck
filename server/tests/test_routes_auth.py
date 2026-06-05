"""
HTTP-level tests for puck-auth enforcement on the match input route
(Tier 3, item 13). These drive the real Flask blueprint with a fake
container (no DB), so the 401/200 decisions are exercised through the
actual request path, not just the authority unit.
"""

from __future__ import annotations

import pytest
from flask import Flask

import runtime_routes
from runtime import (
    IdempotencyCache,
    MatchManager,
    MatchTokenAuthority,
    registry,
)

from conftest import FakeWriter, make_players
from games.speed_pyramid import Question


SECRET = "test-secret-please-rotate-0123456789-abcdef"


def _fixture():
    return [
        Question(
            id=1,
            setup="s",
            question="q",
            answers={"A": "a", "B": "b", "C": "c", "D": "d"},
            correct="A",
            category="T",
            time_limit_ms=10_000,
        )
    ]


def _client_with(container):
    app = Flask(__name__)
    app.register_blueprint(runtime_routes.runtime_bp)
    runtime_routes._container = container  # inject the lazy singleton
    return app.test_client()


@pytest.fixture(autouse=True)
def _reset_container():
    yield
    runtime_routes._container = None


def _setup(token_authority):
    writer = FakeWriter()
    mm = MatchManager(
        registry=registry, writer=writer, idempotency=IdempotencyCache()
    )
    match = mm.create(
        location_id="loc-1",
        game_slug="speed_pyramid",
        table_number=1,
        players=make_players(2),
        questions=_fixture(),
    )
    container = {
        "manager": mm,
        "token_authority": token_authority,
    }
    return _client_with(container), match


def test_input_rejected_without_token_when_auth_on():
    auth = MatchTokenAuthority(SECRET)
    client, match = _setup(auth)
    r = client.post(
        f"/api/runtime/match/{match.id}/input",
        json={"puck_index": 1, "tilt_y": 30, "button_tap": True},
    )
    assert r.status_code == 401


def test_input_accepted_with_valid_token():
    auth = MatchTokenAuthority(SECRET)
    client, match = _setup(auth)
    token = auth.issue("loc-1", 1, table_number=1)
    r = client.post(
        f"/api/runtime/match/{match.id}/input",
        json={"puck_index": 1, "tilt_y": 30, "button_tap": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200


def test_token_for_other_puck_rejected():
    auth = MatchTokenAuthority(SECRET)
    client, match = _setup(auth)
    token_for_1 = auth.issue("loc-1", 1, table_number=1)
    # Try to drive puck 2 with puck 1's token.
    r = client.post(
        f"/api/runtime/match/{match.id}/input",
        json={"puck_index": 2, "tilt_y": 30, "button_tap": True},
        headers={"Authorization": f"Bearer {token_for_1}"},
    )
    assert r.status_code == 401


def test_open_flow_when_auth_off():
    client, match = _setup(token_authority=None)
    r = client.post(
        f"/api/runtime/match/{match.id}/input",
        json={"puck_index": 1, "tilt_y": 30, "button_tap": True},
    )
    assert r.status_code == 200


def test_token_in_body_also_accepted():
    auth = MatchTokenAuthority(SECRET)
    client, match = _setup(auth)
    token = auth.issue("loc-1", 1, table_number=1)
    r = client.post(
        f"/api/runtime/match/{match.id}/input",
        json={"puck_index": 1, "tilt_y": 30, "button_tap": True, "token": token},
    )
    assert r.status_code == 200
