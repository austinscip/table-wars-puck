"""Crash-recovery / rehydrate regression tests for the LIVE Speed Pyramid
engine (audit live-speed-pyramid-2026-06-06).

These drive the real serialization round-trip in `state_persistence` and the
rehydrate-side fixups in `pair_routes`, not re-implementations.
"""
from __future__ import annotations

import pair_routes
import state_persistence as sp


def _roundtrip(obj):
    """Run a value through the exact JSON coerce/restore the writer + loader
    use, so a test sees what a real snapshot file would reconstruct."""
    return sp._restore_from_json(sp._coerce_for_json(obj))


def test_pending_minigame_fires_keys_restored_to_int():
    """SP-CR2: pending_minigame.fires is int-keyed by puck_id; JSON stringifies
    the keys. fix_int_keys_after_rehydrate must coerce them back, or the
    all-fired gate (`pid in fires`) silently fails after a restart."""
    sp_state = {
        "ABC123": {
            "expected_pucks": {1, 2},
            "pending_minigame": {
                "flavor": "BULLSEYE",
                "fires": {1: {"t_ms": 10, "quadrant": "A", "points": 990},
                          2: {"t_ms": 20, "quadrant": "B", "points": 0}},
            },
            "left_match_pucks": {2},
        }
    }
    restored = _roundtrip(sp_state)
    # After JSON round-trip the fires keys are strings...
    assert set(restored["ABC123"]["pending_minigame"]["fires"].keys()) == {"1", "2"}

    sp.fix_int_keys_after_rehydrate(None, restored, {})
    fires = restored["ABC123"]["pending_minigame"]["fires"]
    assert set(fires.keys()) == {1, 2}, "fires keys must be re-coerced to int"
    # The all-fired gate the live resolver uses now works again.
    expected = restored["ABC123"]["expected_pucks"]
    assert all(pid in fires for pid in expected)
    # left_match_pucks comes back as a set of int (the __set__ sentinel path).
    assert restored["ABC123"]["left_match_pucks"] == {2}


def test_rehydrate_rebases_all_absolute_times():
    """SP-CR1: every absolute wall-clock timestamp must be shifted forward by
    the downtime gap so deadlines/last_seen aren't interpreted as ancient
    (which instantly ghost-sweeps everyone and auto-resolves pending phases)."""
    base = 1000.0
    drift = 120.0  # snapshot was 2 minutes before this restart
    lobby = {
        "expires_at": base + 600,
        "players": {1: {"joined_at": base, "last_seen": base},
                    2: {"joined_at": base, "last_seen": base + 5}},
    }
    sp_state = {
        "S": {
            "current_round_started_at": base + 3,
            "pending_category_pick": {"started_at": base, "deadline_at": base + 10},
            "pending_minigame": {"started_at": base + 1, "deadline_at": base + 9},
        }
    }
    qt = {"S": {"started_at": base + 2}}

    pair_routes._rebase_times_after_rehydrate(lobby, sp_state, qt, drift)

    assert lobby["expires_at"] == base + 600 + drift
    assert lobby["players"][1]["last_seen"] == base + drift
    assert lobby["players"][2]["last_seen"] == base + 5 + drift
    st = sp_state["S"]
    assert st["current_round_started_at"] == base + 3 + drift
    assert st["pending_category_pick"]["deadline_at"] == base + 10 + drift
    assert st["pending_minigame"]["deadline_at"] == base + 9 + drift
    assert qt["S"]["started_at"] == base + 2 + drift


def test_rebase_preserves_remaining_deadline_after_real_restart():
    """End-to-end intent: a pick with 8s left at snapshot still has ~8s left
    after a 2-minute restart (not a deadline 112s in the past)."""
    now = pair_routes._now()
    saved_at = now - 120.0          # restart happened 2 min after the snapshot
    deadline_at = saved_at + 8.0    # 8s remained when the snapshot was taken
    sp_state = {"S": {"pending_category_pick": {"started_at": saved_at,
                                                "deadline_at": deadline_at}}}
    pair_routes._rebase_times_after_rehydrate(None, sp_state, {}, now - saved_at)
    remaining = sp_state["S"]["pending_category_pick"]["deadline_at"] - now
    assert 7.0 < remaining < 9.0, "the pick should still have ~8s left, not be expired"


def test_rebase_noop_for_zero_drift():
    sp_state = {"S": {"current_round_started_at": 500.0}}
    pair_routes._rebase_times_after_rehydrate(None, sp_state, {}, 0.0)
    assert sp_state["S"]["current_round_started_at"] == 500.0


def test_puck_tokens_survive_rehydrate():
    """Per-puck tokens live in _LOBBY['players'][pid]['token']; a restart must
    preserve them (int keys + token value) so pucks aren't 401'd after recovery,
    and the token must never appear in the public lobby snapshot."""
    lobby = {
        "code": "274591",
        "host_puck_id": 1,
        "started": True,
        "session_code": "ABC123",
        "players": {1: {"color": "#3B82F6", "color_name": "blue",
                        "joined_at": 1.0, "last_seen": 1.0, "token": "tok-aaa"},
                    2: {"color": "#EC4899", "color_name": "pink",
                        "joined_at": 1.0, "last_seen": 1.0, "token": "tok-bbb"}},
        "expires_at": 10.0,
    }
    restored = _roundtrip(lobby)
    # Keys come back as strings from JSON...
    assert set(restored["players"].keys()) == {"1", "2"}
    sp.fix_int_keys_after_rehydrate(restored, {}, {})
    assert set(restored["players"].keys()) == {1, 2}
    assert restored["players"][1]["token"] == "tok-aaa"
    assert restored["players"][2]["token"] == "tok-bbb"

    # The public snapshot must NOT expose tokens.
    pair_routes._LOBBY = restored
    try:
        snap = pair_routes._lobby_snapshot()
        for p in snap["players"]:
            assert "token" not in p
    finally:
        pair_routes._LOBBY = None
