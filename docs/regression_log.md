# Regression log — table-wars-puck-sandbox

Every bug ever found in this repo, the fix that landed, and the
permanent assertion in `server/scripts/e2e_full_match.py` that
proves it stays fixed. New bugs land here on discovery; new fixes
land here on completion.

**Rule:** if a bug is "fixed" but doesn't have a row in this log
with a gate-assertion name, it's not fixed.

## Format

| ID | Date found | Date fixed | Bug | Gate assertion in e2e_full_match.py |
|----|------------|------------|-----|--------------------------------------|
| R001 | 2026-05-19 | 2026-05-19 | Hub couldn't lock Q2 (polling timer killed by early return on IN_GAME_ANSWERING transition) | every-7-rounds-have-answer-POSTs |
| R002 | 2026-05-19 | 2026-05-19 | Stale ref in selectAnswer → tap: all answers posted as 'A' regardless of clicked letter | every-POST-letter-matches-clicked-letter |
| R003 | 2026-05-19 | 2026-05-19 | Q2+ polling killed after MATCH_ENDED early return | back-to-back-matches-no-state-leak |
| R004 | 2026-05-19 | 2026-05-19 | _QUESTION_TRACKER stale after match end → puck stuck ANSWERING | sp_current_question-returns-false-on-complete |
| R005 | 2026-05-19 | 2026-05-19 | Reset all leaves _SP_STATE so puck2 stuck in MATCH_ENDED | match-state-exists-flag-distinguishes-wipe-vs-natural |
| R006 | 2026-05-19 | 2026-05-19 | Q1 narration silent (sample MP3 status='unknown' falsely truthy) | TBD-Q1-procedural-fallback-fires |
| R007 | 2026-05-26 | 2026-05-26 | Narration countdown ticking during host reading (fallback timeout used NaN duration) | TBD-bar-stays-100pct-during-narration |
| R008 | 2026-05-26 | 2026-05-26 | Back to start did nothing visible (TV didn't react to lobby_cancelled) | TBD-back-to-start-bounces-TV-to-title |
| R009 | 2026-05-26 | 2026-05-26 | Reset all + re-pair failed to bounce TV | TBD-reset-all-bounces-TV-to-title |
| R010 | 2026-05-26 | 2026-05-26 | TV narration echo (REST + socket race created two Audio elements) | TBD-no-duplicate-Audio-elements-per-question |
| R011 | 2026-05-26 | 2026-05-26 | Letters "A" "B" "C" mispronounced by Piper TTS | content-only — verified by listening |
| R012 | 2026-05-27 | TBD | "1/2 correct" on scoreboard — denominator was answered count, not total_rounds | scoreboard-denominator-is-total-rounds |
| R013 | 2026-05-27 | TBD | Hub showed "LOCKED →A" cosmetically when no real POST (puck timed out) | hub-shows-TIMEOUT-not-LOCKED-on-no-tap |
| R014 | 2026-05-27 | TBD | Server claimed pucks "correct" on Q7 when they timed out | timed-out-puck-not-marked-correct |
| R015 | 2026-05-27 | TBD | No audio at pair-code confirm | sfx-pair-confirmed-fires-at-confirm |
| R016 | 2026-05-27 | TBD | No audio when puck joins lobby | sfx-player-joined-fires-on-each-join |
| R017 | 2026-05-27 | TBD | No audio for countdown 3-2-1-GO | sfx-tick-fires-on-each-countdown-step |
| R018 | 2026-05-27 | TBD | No audio on category pick screen | sfx-category-pick-fires-on-screen-show |
| R019 | 2026-05-27 | TBD | Category pick timeout: no visible/audible response | TBD-pick-timeout-shows-default-locked |
| R020 | 2026-05-27 | 2026-05-27 | Minigame Hub controls (◀ A, ▶ B etc.) don't respond — Variant B D-pad was `disabled` during MINIGAME (`tiltActive` excluded minigames); fix enables the D-pad for BULLSEYE aim + adds on-screen minigame instructions | hub-minigame-tilt-buttons-fire |
| R021 | 2026-05-27 | TBD | Q1 commentator audio starts before question card fully renders | commentary-fires-during-reveal-not-question-show |
| R022 | 2026-05-27 | TBD | Commentator keeps talking onto next screen when both pucks answer quickly | reveal-audio-stops-on-navigate-away |
| R023 | 2026-05-27 | TBD | Countdown starts immediately after narration ends with no breath | TBD-gap-between-narration-end-and-countdown |

## How to add a new bug

1. Append a row above with status `TBD` for "Date fixed" and gate assertion name.
2. Implement the fix.
3. Add a named assertion to `server/scripts/e2e_full_match.py` that would FAIL if the bug recurred. Use the same name in this row.
4. Run e2e_full_match.py — the assertion passes.
5. Update this row: set "Date fixed", confirm gate name.

## Gate file

Single primary gate: [`server/scripts/e2e_full_match.py`](../server/scripts/e2e_full_match.py).
Drives a full match through Hub UI + TV. Throwaway `diag_*.py` are
allowed for surfacing a bug, but the durable assertion lands here.
