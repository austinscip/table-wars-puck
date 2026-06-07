"""Browser end-to-end: a real headless Chromium renders the actual TV bundle
served by the real Flask app, and the TV reacts to a real puck over real
sockets. This is the rendering layer the server-side full-match e2e
(server/tests/test_e2e_full_match.py) can't see — together they cover the whole
"Flask + web TV + simulated puck" loop.
"""
from __future__ import annotations

import json
import urllib.request

import pytest

pytest.importorskip("playwright")


def _puck_post(base: str, path: str, body: dict) -> dict:
    req = urllib.request.Request(
        base + path,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=5) as r:
        return json.loads(r.read().decode())


def test_tv_title_renders(live_server, page):
    """The built SPA actually paints in a browser when served by Flask."""
    page.goto(f"{live_server}/tv/speed-pyramid", wait_until="networkidle")
    # The hero title is rendered client-side from the React bundle.
    page.wait_for_selector("text=SPEED PYRAMID", timeout=10_000)
    assert page.is_visible("text=SPEED PYRAMID")
    assert page.is_visible("text=Hold the puck button to pair")


def test_tv_navigates_to_pair_when_a_puck_requests(live_server, page):
    """End-to-end over the wire: the TV (title screen) joins the lobby room on
    its socket; when a puck POSTs /api/pair/request the server emits
    pair_started, and the TV navigates itself to the pair screen."""
    page.goto(f"{live_server}/tv/speed-pyramid", wait_until="networkidle")
    page.wait_for_selector("text=SPEED PYRAMID", timeout=10_000)
    # Give the socket a moment to connect + emit join_lobby before the puck pairs.
    page.wait_for_timeout(1500)

    resp = _puck_post(live_server, "/api/pair/request", {"puck_id": 1})
    assert "pair_code" in resp  # puck 1 is the host; its token is issued on /confirm

    # The TV reacts to the real pair_started socket event and routes itself.
    page.wait_for_url("**/pair**", timeout=10_000)
    assert "/pair" in page.url
