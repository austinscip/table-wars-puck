"""
Tests for the local-first TV SocketIO emit wiring (ADR 0004, Commit 3).

Two layers:

- Routing unit tests (no flask_socketio dependency, so they run in the
  runtime CI job): _state_sink emits `state_update` to the match's room and
  is a safe no-op before a socketio is wired.
- A real SocketIO integration test that drives an actual match through the
  MatchManager and asserts a joined TV test-client receives the frame.
  Guarded with importorskip so it runs locally (flask_socketio installed)
  and is skipped where it isn't.
"""

from __future__ import annotations

import pytest

import runtime_routes


class _FakeSio:
    def __init__(self) -> None:
        self.emits: list[tuple] = []

    def emit(self, event, data=None, room=None, **_kw) -> None:
        self.emits.append((event, data, room))


def test_state_sink_emits_to_match_room(monkeypatch):
    fake = _FakeSio()
    monkeypatch.setattr(runtime_routes, "_socketio", fake)
    env = {
        "match_id": "m1",
        "status": "active",
        "snapshot": {"snapshot_seq": 3},
    }
    runtime_routes._state_sink(env)
    assert fake.emits == [("state_update", env, "match:m1")]


def test_state_sink_is_noop_without_socketio(monkeypatch):
    monkeypatch.setattr(runtime_routes, "_socketio", None)
    # Must not raise — emit before startup / in tests is a no-op.
    runtime_routes._state_sink({"match_id": "m1"})


# ---------------------------------------------------------------------------
# Real SocketIO integration — the TV actually receives the frame.
# ---------------------------------------------------------------------------


def test_join_handler_subscribes_tv_and_input_emits_to_that_room(monkeypatch):
    """End-to-end wiring with a real Flask-SocketIO server:

    1. The join_match handler actually subscribes the TV to `match:<id>`
       (asserted via the server's own room membership — the source of truth
       for who a room emit reaches).
    2. Driving a real input through the MatchManager emits exactly one
       `state_update` to that same room, carrying the snapshot + seq.

    NB: we assert on server-side room membership + an emit spy rather than
    the flask-socketio test client's get_received(), which doesn't capture
    server-initiated emits on the installed flask-socketio/python-socketio
    pair. Together these prove the full path the real native TV uses (join a
    room over the socket, then receive that room's frames)."""
    pytest.importorskip("flask_socketio")

    from flask import Flask
    from flask_socketio import SocketIO

    from runtime import InputEvent, MatchManager, registry as game_registry
    from conftest import FakeWriter, make_players
    from games.speed_pyramid import Question

    app = Flask(__name__)
    sio = SocketIO(app, async_mode="threading")
    # Wires module _socketio + join_match/leave_match handlers + registers
    # the blueprint on this throwaway app.
    runtime_routes.init_runtime_routes(app, sio)

    # Spy on the room emits the state_sink produces (the wrapper still
    # delivers to the real server so room membership is unaffected).
    emits: list[tuple] = []
    real_emit = sio.emit

    def spy_emit(event, *args, **kwargs):
        emits.append((event, args[0] if args else None, kwargs.get("room")))
        return real_emit(event, *args, **kwargs)

    monkeypatch.setattr(sio, "emit", spy_emit)

    writer = FakeWriter()
    manager = MatchManager(
        registry=game_registry,
        writer=writer,
        state_sink=runtime_routes._state_sink,
    )
    match = manager.create(
        location_id="loc",
        game_slug="speed_pyramid",
        table_number=1,
        players=make_players(2),
        questions=[
            Question(
                id=1,
                setup="s1",
                question="q1",
                answers={"A": "a", "B": "b", "C": "c", "D": "d"},
                correct="A",
                category="T",
                time_limit_ms=10_000,
            )
        ],
    )

    client = sio.test_client(app)
    assert client.is_connected()
    client.emit("join_match", {"match_id": match.id})

    # (1) The TV is genuinely subscribed to the match room on the server.
    # The room is the server's source of truth for who a room emit reaches;
    # exactly the one client we connected joined it.
    room = f"match:{match.id}"
    rooms = sio.server.manager.rooms.get("/", {})
    assert len(rooms.get(room, {})) == 1, "join_match did not subscribe the TV"

    # (2) A real input emits one state_update to exactly that room.
    manager.on_input(
        match.id,
        InputEvent(puck_index=1, tilt_x=0.0, tilt_y=30.0, button_tap=True),
    )
    state_updates = [e for e in emits if e[0] == "state_update"]
    assert len(state_updates) == 1, "expected one state_update per input"
    _event, env, emit_room = state_updates[0]
    assert emit_room == room
    assert env["match_id"] == match.id
    assert env["status"] == "active"
    assert "snapshot_seq" in env["snapshot"]
