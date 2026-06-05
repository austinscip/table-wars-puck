"""
Regression tests for multi-lobby pairing (Tier 2, item 10).

PairingManager keys lobbies by (location_id, table_number), so one server
hosts many simultaneous tables. These assert that two tables stay
independent, a puck's later calls resolve to its own table's lobby, and a
match starts with only that table's players.
"""

from __future__ import annotations

import time

import pytest

from runtime import MatchManager, PairingError, PairingManager, registry

from conftest import FakeWriter


class FakeResolver:
    def ensure_puck(self, puck_index: int, location_id: str) -> str:
        return f"uuid-{location_id}-{puck_index}"


def _pairing():
    writer = FakeWriter()
    mm = MatchManager(registry=registry, writer=writer)
    pm = PairingManager(match_manager=mm, puck_resolver=FakeResolver())
    return pm, mm, writer


def test_two_tables_are_independent_lobbies():
    pm, _, _ = _pairing()
    r1 = pm.request_code(1, "speed_pyramid", "loc", 1)
    r2 = pm.request_code(2, "speed_pyramid", "loc", 2)
    assert r1["role"] == "host"
    assert r2["role"] == "host"

    snap1 = pm.lobby_snapshot("loc", 1)
    snap2 = pm.lobby_snapshot("loc", 2)
    assert snap1["host_puck_index"] == 1
    assert snap2["host_puck_index"] == 2
    assert snap1["table_number"] == 1
    assert snap2["table_number"] == 2


def test_joiner_joins_its_own_table():
    pm, _, _ = _pairing()
    host1 = pm.request_code(1, "speed_pyramid", "loc", 1)
    pm.request_code(2, "speed_pyramid", "loc", 2)  # a different table's host

    # Puck 3 pairs at table 1 and confirms table 1's code.
    pm.request_code(3, "speed_pyramid", "loc", 1)
    pm.confirm_code(3, host1["code"])

    snap1 = pm.lobby_snapshot("loc", 1)
    snap2 = pm.lobby_snapshot("loc", 2)
    assert {p["puck_index"] for p in snap1["players"]} == {1, 3}
    assert {p["puck_index"] for p in snap2["players"]} == {2}


def test_dial_and_confirm_resolve_via_locator():
    pm, _, _ = _pairing()
    host = pm.request_code(1, "speed_pyramid", "loc", 5)
    pm.request_code(4, "speed_pyramid", "loc", 5)
    # Dial without passing a table — resolved from the puck locator.
    prog = pm.dial_progress(4, 0, 7)
    assert prog["progress"][0] == 7
    pm.confirm_code(4, host["code"])
    snap = pm.lobby_snapshot("loc", 5)
    assert {p["puck_index"] for p in snap["players"]} == {1, 4}


def test_start_match_is_table_scoped():
    pm, mm, _ = _pairing()
    host = pm.request_code(1, "speed_pyramid", "loc", 1)
    pm.request_code(3, "speed_pyramid", "loc", 1)
    pm.confirm_code(3, host["code"])
    # A second table with its own players that must NOT bleed in.
    pm.request_code(2, "speed_pyramid", "loc", 2)

    match = pm.start_match(1)
    assert match.table_number == 1
    assert {p.puck_index for p in match.players} == {1, 3}
    assert match.id in mm.matches


def test_confirm_wrong_code_rejected():
    pm, _, _ = _pairing()
    pm.request_code(1, "speed_pyramid", "loc", 1)
    pm.request_code(2, "speed_pyramid", "loc", 1)
    with pytest.raises(PairingError):
        pm.confirm_code(2, "000000")


def test_unknown_puck_has_no_lobby():
    pm, _, _ = _pairing()
    with pytest.raises(PairingError, match="No active lobby"):
        pm.dial_progress(99, 0, 1)


def test_cancel_clears_only_that_table():
    pm, _, _ = _pairing()
    pm.request_code(1, "speed_pyramid", "loc", 1)
    pm.request_code(2, "speed_pyramid", "loc", 2)
    pm.cancel(1)  # host of table 1
    assert pm.lobby_snapshot("loc", 1) == {"active": False}
    assert pm.lobby_snapshot("loc", 2)["active"] is True


def test_lobby_snapshot_reports_multiple_tables():
    pm, _, _ = _pairing()
    pm.request_code(1, "speed_pyramid", "loc", 1)
    pm.request_code(2, "speed_pyramid", "loc", 2)
    snap = pm.lobby_snapshot()  # no table specified
    assert snap["active"] is False
    assert snap["reason"] == "multiple_tables"
    assert len(snap["tables"]) == 2


def test_single_lobby_snapshot_back_compat():
    pm, _, _ = _pairing()
    pm.request_code(1, "speed_pyramid", "loc", 1)
    # Exactly one lobby -> no-arg snapshot returns it (pilot path).
    snap = pm.lobby_snapshot()
    assert snap["active"] is True
    assert snap["host_puck_index"] == 1


def test_expired_lobby_is_purged():
    pm, _, _ = _pairing()
    pm.request_code(1, "speed_pyramid", "loc", 1)
    pm._lobbies[("loc", 1)].expires_at = time.time() - 1
    assert pm.lobby_snapshot("loc", 1) == {"active": False}
    # Locator entry cleaned up too -> the puck resolves to nothing.
    with pytest.raises(PairingError):
        pm.dial_progress(1, 0, 1)


def test_game_slug_mismatch_at_same_table_rejected():
    pm, _, _ = _pairing()
    pm.request_code(1, "speed_pyramid", "loc", 1)
    with pytest.raises(PairingError, match="not 'puck_golf'"):
        pm.request_code(2, "puck_golf", "loc", 1)
