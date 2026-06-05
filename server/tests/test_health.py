"""
Health endpoint test (deploy/load-balancer readiness).
"""

from __future__ import annotations

import pytest
from flask import Flask

import runtime_routes


@pytest.fixture(autouse=True)
def _reset_container():
    yield
    runtime_routes._container = None


def _client():
    app = Flask(__name__)
    app.register_blueprint(runtime_routes.runtime_bp)
    return app.test_client()


def test_health_ok_without_container():
    # Must answer 200 even before the (DB-touching) container is built.
    runtime_routes._container = None
    r = _client().get("/api/runtime/health")
    assert r.status_code == 200
    body = r.get_json()
    assert body["status"] == "ok"
    assert body["runtime_initialized"] is False
    # Registry is populated lazily by the endpoint; all four games present.
    assert set(body["games"]) >= {"speed_pyramid", "puck_golf", "puck_racer", "smash"}


def test_health_reports_container_state():
    from runtime import MatchManager, InMemoryMatchStore, registry
    from conftest import FakeWriter

    mm = MatchManager(registry=registry, writer=FakeWriter(), store=InMemoryMatchStore())
    runtime_routes._container = {
        "manager": mm,
        "token_authority": object(),  # truthy -> puck_auth True
    }
    body = _client().get("/api/runtime/health").get_json()
    assert body["runtime_initialized"] is True
    assert body["active_matches"] == 0
    assert body["puck_auth"] is True
    assert body["durable_store"] is True
