"""
Regression tests for two lifecycle correctness fixes:
- audit 1.6: golf charges MAX_STROKES per unplayed hole, so quitting early
  can't out-rank a player who finished the course.
- audit 1.8: heartbeat state survives serialize/restore, preserving the
  exactly-once disconnect (PLAYER_LEFT) semantics across recovery.
"""

from __future__ import annotations

from runtime import HeartbeatTracker

from games.puck_golf import PuckGolf, Hole, MAX_STROKES, STROKE_PENALTY
from conftest import make_players


def _two_hole_course():
    return [Hole(number=1, distance=200.0, par=4),
            Hole(number=2, distance=200.0, par=4)]


def test_golf_quitter_cannot_outrank_finisher():
    game = PuckGolf(players=make_players(2), course=_two_hole_course())
    s1 = game.player_state[1]
    s2 = game.player_state[2]
    # Player 1 finished both holes at 2 strokes each (total 4).
    s1.holes_strokes = [2, 2]
    # Player 2 played ONE great hole (1 stroke) then quit.
    s2.holes_strokes = [1]
    s2.disconnected = True

    finals = game.final_scores()
    # Quitter is charged MAX_STROKES for the unplayed hole: 1 + 6 = 7 strokes.
    assert finals[2] == (1 + MAX_STROKES) * STROKE_PENALTY
    # Finisher (4 strokes) must rank ABOVE the quitter (higher = better).
    assert finals[1] > finals[2]


def test_golf_normal_finish_unaffected():
    game = PuckGolf(players=make_players(2), course=_two_hole_course())
    game.player_state[1].holes_strokes = [3, 3]
    game.player_state[2].holes_strokes = [2, 5]
    finals = game.final_scores()
    # No unplayed holes -> plain stroke sum, fewest wins.
    assert finals[1] == 6 * STROKE_PENALTY
    assert finals[2] == 7 * STROKE_PENALTY
    assert finals[1] > finals[2]


def test_heartbeat_export_restore_preserves_stale_flag():
    import json

    hb = HeartbeatTracker(stale_threshold_s=8.0)
    hb.register("m1", [1, 2])
    # Age puck 1 past stale and sweep -> marks it emitted; puck 2 stays fresh.
    hb._beats["m1"][1].last_seen -= 100.0
    assert hb.sweep("m1") == {1}
    assert hb._beats["m1"][1].stale_emitted is True

    # Round-trip through JSON like the Redis/JSON store does (int keys -> str).
    exported = json.loads(json.dumps(hb.export("m1")))

    # Restart: fresh tracker, re-register (fresh), then restore.
    hb2 = HeartbeatTracker(stale_threshold_s=8.0)
    hb2.register("m1", [1, 2])
    hb2.restore("m1", exported)
    assert hb2._beats["m1"][1].stale_emitted is True
    # The already-emitted disconnect for puck 1 must NOT re-fire; puck 2 fresh.
    assert hb2.sweep("m1") == set()
