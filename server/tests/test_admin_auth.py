"""
Tests for the admin auth gate (audit 0.1). The firmware/admin endpoints were
unauthenticated (fleet RCE); require_admin gates them on ADMIN_API_TOKEN.
"""

from __future__ import annotations

import pytest
from flask import Flask, jsonify

from admin_auth import require_admin


@pytest.fixture
def app():
    app = Flask(__name__)

    @app.route("/strict", methods=["POST"])
    @require_admin(strict=True)
    def strict_view():
        return jsonify({"ok": True})

    @app.route("/lax", methods=["POST"])
    @require_admin()
    def lax_view():
        return jsonify({"ok": True})

    return app.test_client()


def test_strict_fails_closed_without_token(app, monkeypatch):
    monkeypatch.delenv("ADMIN_API_TOKEN", raising=False)
    # Firmware-class endpoint: refused entirely when unconfigured.
    assert app.post("/strict").status_code == 503


def test_lax_allows_without_token_in_dev(app, monkeypatch):
    monkeypatch.delenv("ADMIN_API_TOKEN", raising=False)
    # Non-strict admin endpoint: allowed (with a warning) for the dev flow.
    assert app.post("/lax").status_code == 200


def test_token_required_when_configured(app, monkeypatch):
    monkeypatch.setenv("ADMIN_API_TOKEN", "s3cret")
    # No token -> 401 on both.
    assert app.post("/strict").status_code == 401
    assert app.post("/lax").status_code == 401
    # Wrong token -> 401.
    assert app.post(
        "/strict", headers={"Authorization": "Bearer nope"}
    ).status_code == 401


def test_correct_token_via_bearer_and_header(app, monkeypatch):
    monkeypatch.setenv("ADMIN_API_TOKEN", "s3cret")
    assert app.post(
        "/strict", headers={"Authorization": "Bearer s3cret"}
    ).status_code == 200
    assert app.post(
        "/lax", headers={"X-Admin-Token": "s3cret"}
    ).status_code == 200
