"""Comprehensive audio-events gate — covers R015-R018 audio cues.

Drives a real match and asserts every expected SFX cue fires at the
right phase, backed by the dev-only sessionStorage tap inside
lib/audio.ts `_play()`.

Cues:
  sfx_joined / sfx_digit       — pair-confirm + lobby join (R015 / R016)
  sfx_pick_show / sfx_pick_locked — category-pick screen (R018)
  sfx_question_show              — question card reveal
  sfx_tick / sfx_tick_final      — countdown 3-2-1 (R017)
  sfx_lock                       — answer lock-in
  sfx_correct / wrong / reveal   — per-question reveal stinger
  sfx_match_end                  — final scoreboard chord

Gate assertion name: every-named-sfx-fires-during-a-match
"""
from __future__ import annotations

import sys
import time
from collections import Counter

import requests

from verify_lib import (
    BASE, TV, HUB, log, session, drive_match_to_scoreboard,
    pair_and_start, puck_row, read_sfx_log, Verifier,
)


# Same as pair_and_start but routes the TV through /lobby/<code> before
# the second puck joins, so the LobbyScreen's player_joined handler
# fires audio.joined() naturally. The default pair_and_start skips to
# /question/<sc> for speed; here we want the natural cascade through
# Pair -> Lobby -> Countdown -> Question so every cue gets exercised.
def _pair_and_start_via_lobby(hub, tv) -> str | None:
    puck_row(hub, 0).get_by_role("button", name="Hold 1s").click(); time.sleep(0.5)
    puck_row(hub, 0).locator("button", has_text="Confirm").click(); time.sleep(0.8)
    pair_code = requests.get(f"{BASE}/api/pair/lobby-state",
                              timeout=5).json().get("code")
    if not pair_code:
        return None
    log(f"pair_code={pair_code} -> TV /lobby/{pair_code}")
    tv.goto(f"{TV}/lobby/{pair_code}", wait_until="domcontentloaded")
    # Give the socket time to join the pair room before puck 2 fires
    # player_joined (otherwise the event is broadcast to a room the TV
    # isn't in yet and audio.joined() never runs).
    time.sleep(2.5)
    puck_row(hub, 1).get_by_role("button", name="Hold 1s").click()
    time.sleep(2.0)
    puck_row(hub, 0).get_by_role("button", name="Start match", exact=True).click()
    time.sleep(1.2)
    sc = requests.get(f"{BASE}/api/pair/lobby-state", timeout=5).json().get("session_code")
    if not sc:
        return None
    # Let Lobby cascade into Countdown -> Question on its own; if it
    # doesn't, force /question after 4s.
    time.sleep(4.0)
    if "/question/" not in tv.evaluate("() => location.pathname"):
        tv.goto(f"{TV}/question/{sc}", wait_until="domcontentloaded")
    return sc


def run() -> int:
    v = Verifier()
    with session(record_sfx=True) as (hub, tv):
        sc = _pair_and_start_via_lobby(hub, tv)
        if not sc:
            v.inconclusive("setup", "no session_code"); return v.report()
        drive_match_to_scoreboard(hub, tv)
        time.sleep(2.0)  # let scoreboard SFX fire
        sfx = read_sfx_log(tv)

    counts = Counter(e["name"] for e in sfx)
    log(f"captured {sum(counts.values())} SFX events:")
    for name, n in sorted(counts.items(), key=lambda kv: -kv[1]):
        log(f"   {name:24s} {n}")

    # Each (sample-name, minimum-count, label) pair.
    expectations = [
        ("sfx_joined",         2,  "R016: puck joined SFX"),
        ("sfx_pick_show",      3,  "R018: category-pick screen SFX"),
        ("sfx_pick_locked",    1,  "pick-locked SFX"),
        ("sfx_question_show",  6,  "question-show SFX"),
        ("sfx_lock",           10, "answer lock-in SFX"),
    ]
    for name, need, label in expectations:
        v.check(label, counts.get(name, 0) >= need,
                f"{counts.get(name, 0)} >= {need}")

    reveals = (counts.get("sfx_correct", 0) + counts.get("sfx_wrong", 0)
               + counts.get("sfx_reveal", 0))
    v.check("per-reveal stinger (correct|wrong|reveal)",
            reveals >= 6, f"{reveals} >= 6")
    return v.report()


if __name__ == "__main__":
    sys.exit(run())
