"""
Tests for token-bucket rate limiting (Tier 3, item 15) — the unit
(deterministic via an injected clock) and the route-level 429.
"""

from __future__ import annotations

import pytest
from flask import Flask

import runtime_routes
from runtime import IdempotencyCache, MatchManager, RateLimiter, registry

from conftest import FakeWriter, make_players
from games.speed_pyramid import Question


def test_burst_then_limited_then_refills():
    clock = [0.0]
    rl = RateLimiter(rate_per_sec=1.0, burst=3.0, now=lambda: clock[0])
    # Burst of 3 allowed.
    assert rl.allow("k")
    assert rl.allow("k")
    assert rl.allow("k")
    # 4th denied — bucket empty.
    assert not rl.allow("k")
    # 2 seconds later -> 2 tokens refilled.
    clock[0] = 2.0
    assert rl.allow("k")
    assert rl.allow("k")
    assert not rl.allow("k")


def test_keys_are_independent():
    rl = RateLimiter(rate_per_sec=1.0, burst=1.0, now=lambda: 0.0)
    assert rl.allow("a")
    assert not rl.allow("a")  # a exhausted
    assert rl.allow("b")  # b is a fresh bucket


def test_drop_resets_matching_keys():
    rl = RateLimiter(rate_per_sec=1.0, burst=1.0, now=lambda: 0.0)
    assert rl.allow("m1:1")
    assert not rl.allow("m1:1")
    rl.drop("m1:")
    assert rl.allow("m1:1")  # bucket forgotten -> full again


def test_invalid_config_rejected():
    with pytest.raises(ValueError):
        RateLimiter(rate_per_sec=0)
    with pytest.raises(ValueError):
        RateLimiter(burst=-1)


# --- Route level ---


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
    yield
    runtime_routes._container = None


def test_route_returns_429_when_bucket_empty():
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
    # burst=2 -> the 3rd request in the same instant is limited.
    limiter = RateLimiter(rate_per_sec=0.001, burst=2.0, now=lambda: 0.0)
    runtime_routes._container = {
        "manager": mm,
        "token_authority": None,
        "rate_limiter": limiter,
    }
    app = Flask(__name__)
    app.register_blueprint(runtime_routes.runtime_bp)
    client = app.test_client()

    path = f"/api/runtime/match/{match.id}/input"
    body = {"puck_index": 1}
    assert client.post(path, json=body).status_code == 200
    assert client.post(path, json=body).status_code == 200
    assert client.post(path, json=body).status_code == 429
    # A different puck has its own bucket and is unaffected.
    assert client.post(path, json={"puck_index": 2}).status_code == 200
