"""
Regression tests for the monotonic cue watermark (Tier 1, item 6).

The TV dedupes cues across snapshot updates by comparing each cue's
watermark to the highest it has seen. A wall-clock `ts` can run backwards
(NTP step, container restart), sticking the watermark and silently
dropping every later cue. The fix: the MatchManager stamps each cue with
a per-match `seq` that only ever increases, and the TV dedupes on that.

These assert the server side: every persisted cue carries a `seq`, and
the sequence is strictly increasing and gap-free across the whole match,
independent of the cues' own `ts` values.
"""

from __future__ import annotations

from runtime import InputEvent, MatchManager, registry

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
        ),
        Question(
            id=2,
            setup="s2",
            question="q2",
            answers={"A": "a", "B": "b", "C": "c", "D": "d"},
            correct="B",
            category="T",
            time_limit_ms=10_000,
        ),
    ]


def test_cue_seq_is_strictly_increasing_and_gapless():
    writer = FakeWriter()
    mgr = MatchManager(registry=registry, writer=writer)
    players = make_players(2)
    match = mgr.create(
        location_id="loc",
        game_slug="speed_pyramid",
        table_number=1,
        players=players,
        questions=_fixture(),
    )

    # Drive a full match so many cues fire (match_start, round_start,
    # lock-ins, correct/wrong, round_end, next round_start, match_end).
    def answer(puck, letter):
        tilt = {"A": (0.0, 30.0), "B": (30.0, 0.0)}[letter]
        mgr.on_input(
            match.id,
            InputEvent(
                puck_index=puck,
                tilt_x=tilt[0],
                tilt_y=tilt[1],
                button_tap=True,
            ),
        )

    answer(1, "A")
    answer(2, "A")  # both locked -> round advances
    answer(1, "B")
    answer(2, "B")  # match ends

    seqs = writer.cue_seqs(match.id)
    assert seqs, "no cues were stamped with a seq"
    # Strictly increasing AND contiguous from 0 — the manager assigns one
    # per cue with no reuse and no gap.
    assert seqs == list(range(len(seqs))), f"seqs not gapless/monotonic: {seqs}"


def test_every_cue_carries_a_seq():
    writer = FakeWriter()
    mgr = MatchManager(registry=registry, writer=writer)
    players = make_players(1)
    match = mgr.create(
        location_id="loc",
        game_slug="speed_pyramid",
        table_number=1,
        players=players,
        questions=_fixture(),
    )
    mgr.on_input(
        match.id,
        InputEvent(puck_index=1, tilt_x=0.0, tilt_y=30.0, button_tap=True),
    )

    # Inspect raw snapshots: any snapshot that carries cues must carry a
    # seq on every one of them.
    seen_cue = False
    for mid, snap in writer.snapshots:
        if mid != match.id:
            continue
        for cue in snap.get("cues", []) or []:
            seen_cue = True
            assert "seq" in cue, f"cue without seq: {cue}"
    assert seen_cue, "expected at least one cue across the match"
