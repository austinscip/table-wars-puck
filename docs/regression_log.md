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
| R015 | 2026-05-27 | 2026-05-28 | No audio at pair-code confirm. Verified: sfx_digit fires 6× (one per dial) + sfx_joined fires on confirm. Captured by `gate_audio_events.py` via a dev-only sessionStorage tap in lib/audio.ts `_play()`. | every-named-sfx-fires-during-a-match |
| R016 | 2026-05-27 | 2026-05-28 | No audio when puck joins lobby. Verified: sfx_joined fires ≥3 (host + joiners, ×2 for StrictMode double-mount). The previous "TBD" hid a real testing gap: the harness was navigating the TV straight to /question, skipping Pair/Lobby screens entirely. Now exercises the natural Title→Lobby→Countdown→Question cascade. | every-named-sfx-fires-during-a-match |
| R017 | 2026-05-27 | 2026-05-28 | No audio for countdown 3-2-1-GO. Verified: sfx_tick ×3 + sfx_tick_final ×1 captured during the countdown phase. | every-named-sfx-fires-during-a-match |
| R018 | 2026-05-27 | 2026-05-28 | No audio on category pick screen. Verified: sfx_pick_show fires ≥3 (once per pick round) + sfx_pick_locked fires ≥1. | every-named-sfx-fires-during-a-match |
| R019 | 2026-05-27 | TBD | Category pick timeout: no visible/audible response | TBD-pick-timeout-shows-default-locked |
| R020 | 2026-05-27 | 2026-05-27 | Minigame Hub controls (◀ A, ▶ B etc.) don't respond — Variant B D-pad was `disabled` during MINIGAME (`tiltActive` excluded minigames); fix enables the D-pad for BULLSEYE aim + adds on-screen minigame instructions | hub-minigame-tilt-buttons-fire |
| R021 | 2026-05-27 | TBD | Q1 commentator audio starts before question card fully renders | commentary-fires-during-reveal-not-question-show |
| R022 | 2026-05-27 | 2026-05-27 | Narration voice "bleeds into next screen". GROUND-TRUTH verified NOT occurring in current build: verify_audio_bleed.py drives a full match, confirms narration actually plays (6/6 rounds), forces reveal mid-narration, and asserts the narration playback clock NEVER advances while the TV route ≠ /question. Could not reproduce on either build — both paths already guarded (reveal→pause; mid-question navigation→`emptied` cancels the delayed play()). Most likely user hit a STALE bundle pre-dating the R021/R022 fixes. Added R022b defensive timer-tracking (narrationTimersRef) to stop relying on the async `emptied` side-effect. | verify_audio_bleed.py (narration-clock-never-off-/question; INCONCLUSIVE if narration didn't play) + gate_r022b_no_bleed.py (invariant: no narration play() after mid-question nav — note: passes on both builds, guards the existing `emptied` clear) |
| R023 | 2026-05-27 | TBD | Countdown starts immediately after narration ends with no breath | TBD-gap-between-narration-end-and-countdown |
| R027 | 2026-05-27 | 2026-05-27 | ~9% of questions (116/1296) have no narration MP3 and 404 → host silent on those rounds. sp_load_question now prefers a question that has a narration MP3 (re-draws up to 12× keeping category, relaxing difficulty; graceful fallback). Verified 21/21 questions narrated across 3 matches (pre-fix averaged ~2 404s per 21). | every-served-question-has-narration (gate_r027_narration_present.py — full match, asserts 0 narration 404s; statistical per single run) |
| R026 | 2026-05-27 | 2026-05-27 | Final question (Q7) skipped → scoreboard shows X/7 after only 6 questions. load-question marked the match complete the instant round>=SP_TOTAL_ROUNDS, BEFORE the final question was revealed. A second load-question call while Q7 was active (the R024 pick-timeout kick advances to Q7, then QuestionScreen mounts and re-issues load-question) hit round>=7 and ended the match, skipping Q7. Fix: complete only when the final round's question has been revealed (load-question now idempotently returns active Q7). Surfaced by the hardened phase-driven e2e_full_match (was consistently 6/7, now 7/7). | exactly-7-answer-POSTs-per-puck (e2e_full_match.py — phase-driven driver answers each distinct question once; PROVEN 6/7 pre-fix → 7/7 post-fix) |
| R025 | 2026-05-27 | 2026-05-27 | "Bullseye minigame had no results" — NOT a separate bug; downstream of R020. With the aim D-pad dead (or in fire-only variants), every fire defaulted to quadrant A; unless the target was A, all fires missed → 0 points → no winner/bonus awarded → results panel shows only "no bonus". Verified the chain is resolved: aiming at the real target now yields 🥇+500/🥈+200. Aim added to BOTH VariantA (compact A/B/C/D pills) and VariantB (D-pad); gate proves a winner in both. VariantC (workshop/debug) remains fire-only by design. | bullseye-aim-produces-a-winner (verify_bullseye_scoring.py — variants A + B) — see [[R020]] |
| R024 | 2026-05-27 | 2026-05-27 | Category pick HANGS at 0s — TV never re-calls load-question on deadline expiry, so the server's auto-default (which only fires when load-question is called after the deadline; pucks never call it) never runs and the whole match freezes. Surfaced by ground-truth diag (diag_narration.py) + user report. CategoryPickScreen countdown now kicks loadQuestion on expiry. | pick-timeout-auto-advances-to-question (gate_r024_pick_timeout.py — proven to FAIL on pre-fix build, PASS on fix) |

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
