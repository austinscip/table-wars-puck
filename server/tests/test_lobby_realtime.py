"""
Tests for lobby-via-Realtime write-through (Tier 2, item 12).

PairingManager mirrors each lobby mutation into the lobbies table (via an
injected writer) so the TV can subscribe instead of polling. A fake writer
records the calls; a publish failure must never break pairing.
"""

from __future__ import annotations

from runtime import MatchManager, PairingManager, registry

from conftest import FakeWriter


class FakeResolver:
    def ensure_puck(self, puck_index, location_id):
        return f"uuid-{puck_index}"


class RecordingLobbyWriter:
    def __init__(self):
        self.upserts: list[tuple[str, int, dict]] = []
        self.deletes: list[tuple[str, int]] = []

    def upsert_lobby(self, location_id, table_number, snapshot):
        self.upserts.append((location_id, table_number, snapshot))

    def delete_lobby(self, location_id, table_number):
        self.deletes.append((location_id, table_number))


def _pairing(lobby_writer):
    mm = MatchManager(registry=registry, writer=FakeWriter())
    return PairingManager(
        match_manager=mm,
        puck_resolver=FakeResolver(),
        lobby_writer=lobby_writer,
    )


def test_host_join_publishes_lobby():
    lw = RecordingLobbyWriter()
    pm = _pairing(lw)
    pm.request_code(1, "speed_pyramid", "loc-1", 3)  # host
    assert lw.upserts, "host join should publish the lobby"
    loc, tbl, snap = lw.upserts[-1]
    assert (loc, tbl) == ("loc-1", 3)
    assert snap["host_puck_index"] == 1


def test_joiner_confirm_publishes_updated_roster():
    lw = RecordingLobbyWriter()
    pm = _pairing(lw)
    host = pm.request_code(1, "speed_pyramid", "loc-1", 1)
    pm.request_code(2, "speed_pyramid", "loc-1", 1)  # joiner requests
    before = len(lw.upserts)
    pm.confirm_code(2, host["code"])  # joiner confirms -> joins
    assert len(lw.upserts) > before
    _, _, snap = lw.upserts[-1]
    assert {p["puck_index"] for p in snap["players"]} == {1, 2}


def test_start_publishes_started_lobby():
    lw = RecordingLobbyWriter()
    pm = _pairing(lw)
    pm.request_code(1, "speed_pyramid", "loc-1", 1)
    pm.start_match(1)
    _, _, snap = lw.upserts[-1]
    assert snap["started"] is True
    assert snap["match_id"] is not None


def test_cancel_deletes_lobby_row():
    lw = RecordingLobbyWriter()
    pm = _pairing(lw)
    pm.request_code(1, "speed_pyramid", "loc-1", 1)
    pm.cancel(1)
    assert ("loc-1", 1) in lw.deletes


def test_expiry_deletes_lobby_row():
    import time
    lw = RecordingLobbyWriter()
    pm = _pairing(lw)
    pm.request_code(1, "speed_pyramid", "loc-1", 1)
    pm._lobbies[("loc-1", 1)].expires_at = time.time() - 1
    pm.lobby_snapshot("loc-1", 1)  # triggers purge
    assert ("loc-1", 1) in lw.deletes


def test_publish_failure_does_not_break_pairing():
    class Boom:
        def upsert_lobby(self, *a):
            raise RuntimeError("db down")

        def delete_lobby(self, *a):
            raise RuntimeError("db down")

    pm = _pairing(Boom())
    # Pairing still succeeds despite the publish raising.
    resp = pm.request_code(1, "speed_pyramid", "loc-1", 1)
    assert resp["role"] == "host"


def test_no_writer_is_a_noop():
    pm = _pairing(lobby_writer=None)
    resp = pm.request_code(1, "speed_pyramid", "loc-1", 1)
    assert resp["role"] == "host"  # no crash without a writer
