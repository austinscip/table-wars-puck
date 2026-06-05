"""
HTTP-level tests for the player-bind route (ADR 0005). Drive the real Flask
blueprint with a fake container (no DB), so the endpoint's decisions — mint
vs. echo a token, status gating, puck/match resolution, phone linking — are
exercised through the actual request path.
"""

from __future__ import annotations

import pytest
from flask import Flask

import runtime_routes
from runtime import MatchManager, PlayerIdentity, registry

from conftest import FakeWriter, make_players
from games.speed_pyramid import Question


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


@pytest.fixture(autouse=True)
def _reset_container():
    import os

    prev_loc = os.environ.get("LOCATION_ID")
    yield
    runtime_routes._container = None
    # Don't leak the LOCATION_ID we set into other tests.
    if prev_loc is None:
        os.environ.pop("LOCATION_ID", None)
    else:
        os.environ["LOCATION_ID"] = prev_loc


def _setup(*, phone_pepper=None, location_id="loc-1"):
    import os

    os.environ["LOCATION_ID"] = location_id
    writer = FakeWriter()
    mm = MatchManager(registry=registry, writer=writer)
    match = mm.create(
        location_id=location_id,
        game_slug="speed_pyramid",
        table_number=1,
        players=make_players(2),
        questions=_fixture(),
    )
    container = {
        "manager": mm,
        "writer": writer,
        "player_identity": PlayerIdentity(phone_pepper),
    }
    app = Flask(__name__)
    app.register_blueprint(runtime_routes.runtime_bp)
    runtime_routes._container = container
    return app.test_client(), match, writer


def test_bind_mints_token_when_none_provided():
    client, match, writer = _setup()
    resp = client.post(
        f"/api/runtime/match/{match.id}/bind",
        json={"puck_index": 1, "display_name": "Mae"},
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["token"], "a fresh token must be returned for the device"
    assert data["created"] is True
    # The bind hit the writer with the right match_puck for puck_index 1.
    mp_id = match.match_puck_ids[1]
    assert writer.bindings == [(mp_id, data["player_id"], "Mae")]


def test_bind_with_existing_token_does_not_echo_it():
    client, match, writer = _setup()
    token = PlayerIdentity.new_token()
    # First bind establishes the player.
    client.post(
        f"/api/runtime/match/{match.id}/bind",
        json={"puck_index": 1, "token": token},
    )
    # Second bind (same token, puck 2) returns the SAME player, no echoed token.
    resp = client.post(
        f"/api/runtime/match/{match.id}/bind",
        json={"puck_index": 2, "token": token},
    )
    data = resp.get_json()
    assert data["token"] is None, "must never echo a caller-provided token"
    assert data["created"] is False
    # Same human token -> same player across both seats.
    assert {b[1] for b in writer.bindings} == {data["player_id"]}


def test_bind_rejects_unknown_puck_index():
    client, match, _ = _setup()
    resp = client.post(
        f"/api/runtime/match/{match.id}/bind", json={"puck_index": 7}
    )
    assert resp.status_code == 404


def test_bind_rejects_when_match_over():
    client, match, _ = _setup()
    match.status = "finished"
    resp = client.post(
        f"/api/runtime/match/{match.id}/bind", json={"puck_index": 1}
    )
    assert resp.status_code == 409


def test_bind_rejects_other_location_match():
    client, match, _ = _setup(location_id="loc-1")
    match.location_id = "some-other-location"
    resp = client.post(
        f"/api/runtime/match/{match.id}/bind", json={"puck_index": 1}
    )
    assert resp.status_code == 403


def test_phone_linked_only_when_pepper_configured():
    # No pepper -> phone ignored.
    client, match, writer = _setup(phone_pepper=None)
    resp = client.post(
        f"/api/runtime/match/{match.id}/bind",
        json={"puck_index": 1, "phone": "313-555-1212"},
    )
    assert resp.get_json()["phone_linked"] is False
    assert writer.phone_hashes == {}

    # With a pepper -> phone hashed + linked.
    client2, match2, writer2 = _setup(phone_pepper="pep")
    resp2 = client2.post(
        f"/api/runtime/match/{match2.id}/bind",
        json={"puck_index": 1, "phone": "313-555-1212"},
    )
    data = resp2.get_json()
    assert data["phone_linked"] is True
    assert writer2.phone_hashes.get(data["player_id"])


def test_bind_requires_puck_index():
    client, match, _ = _setup()
    resp = client.post(f"/api/runtime/match/{match.id}/bind", json={})
    assert resp.status_code == 400
