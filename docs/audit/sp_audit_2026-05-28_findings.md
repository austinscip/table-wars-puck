# Speed Pyramid — Master Audit Findings (2026-05-28)

**Date:** 2026-05-28
**Audit scope:** Every screen (Title, Pair, Lobby, Countdown, Question, CategoryPick,
Minigame, Scoreboard) across 1–8 players, all power-up combinations
(DOUBLE / REVEAL / STEAL and their stacks), lifecycle controls
(Play-Again / Back-to-start / Reset-all / leave-match), the narrator + SFX/stinger
audio bus, and the full UX state machine (every state, transition, and edge case).

## BIG CAVEAT — browser-truth verification is DEFERRED

This run produced **triaged findings + authored regression gates only**. It did NOT
perform browser-truth verification, did NOT prove fail-on-current by execution, did NOT
land any fix, and did NOT commit anything. Reason: a Kokoro narration regen
(**PID 73387**) is actively rewriting the narration MP3s under
`server/static/games/speed-pyramid/audio/`, and CPU is contended, so launching
Playwright/Chromium and running the gates was banned this phase. All gate scripts were
authored and (where cheap) byte-compiled / import-checked only. Every expected
fail-on-current → pass-on-fix outcome below is a **prediction from source reading**, to
be empirically proven in the next run (**sp-audit-fix**) once the Kokoro regen finishes
and the MP3 files are stable. Treat every row's status as TBD until that run proves it.

## Kept candidates (20)

| ID | Sev | Kind | Area | Gate file | Gate name | Description | Fix sketch |
|----|-----|------|------|-----------|-----------|-------------|------------|
| R029 | critical | server-rest | pair_routes.py sp_final_results vs cumulative_scores | gate_r029_final_results_cumulative.py | final-results-matches-cumulative-not-db-sum | Final scoreboard total reads DB SUM(points_earned), excluding minigame bonuses and power-up effects that only mutate in-memory cumulative_scores | Source final-results from cumulative_scores when state exists, or write post-arm points + minigame ledger rows back to trivia_answers |
| R030 | high | server-rest | sp_reset vs final-results session_id filter | gate_r030_replay_answer_leak.py | play-again-clears-prior-answers | Play-Again never deletes prior-match trivia_answers, so replay final-results SUMs both matches (answered > total_rounds) | DELETE trivia_answers WHERE session_id in sp_reset, or allocate a fresh session_code per Play-Again |
| R031 | high | server-rest | _maybe_emit_reveal TIMEOUT fill + _apply_power_up_arms REVEAL | gate_r031_reveal_on_timeout.py | timed-out-puck-with-reveal-not-marked-correct | REVEAL on a timed-out puck forces is_correct=true/1000/LEGENDARY because arms run over TIMEOUT-filled answers (open R014) | Skip REVEAL/DOUBLE for entries whose tier=='TIMEOUT' (continue at top of per-puck arm loop) |
| R032 | high | server-rest | _score_minigame_fire SHOT_CLOCK branch | gate_r032_shotclock_window.py | shotclock-late-fire-scores-zero | SHOT_CLOCK fire has no upper time-window guard; a fire after the 8s deadline still scores full points | Add the BULLSEYE window guard (`if t_ms < 0 or t_ms > duration_ms: return 0`) to the SHOT_CLOCK branch |
| R033 | high | mixed | sp_answer (no revealed_for_question_id guard) | gate_r033_answer_after_reveal.py | answer-after-reveal-rejected | A late answer in the post-reveal pre-advance window passes both 409 guards, returns 200, writes a DB row, flips the TV lane back to LOCKED | Add `if state.get('revealed_for_question_id')==int(question_id): return 409` in sp_answer |
| R034 | high | mixed | missing /api/sp/leave-match + usePuckState + QuestionScreen | gate_r034_leave_match_phantom.py | leave-match-route-prunes-expected-pucks | leave-match is a phantom 404; departed puck stays in expected_pucks, stranding rounds to the 10s force-reveal and orphaning its lane | Add POST /api/sp/leave-match that prunes the puck from state and emits player_left_match; add client handlers; stop swallowing the POST |
| R035 | high | server-rest | _apply_power_up_arms STEAL loop | gate_r035_steal_order.py | steal-order-independent-and-answer-gated | Mutual/multi-target STEAL is order-dependent (in-place mutation) and lossy (floor-division); a timed-out non-answerer still steals | Snapshot pre-steal points, compute all transfers against the snapshot, distribute remainder, require firer non-TIMEOUT answer |
| R036 | high | mixed | QuestionScreen forceReveal advance loop + sp_force_reveal 400 | gate_r036_force_reveal_advance.py | force-reveal-failure-still-advances | force-reveal 400 is swallowed by the empty .catch so the next-question advance is never scheduled; TV strands forever | Schedule advance in .finally (both then+catch), or return 200 {emitted:false} when no current question |
| R037 | high | server-rest | sp_load_question -> _sp_state_for create path | gate_r037_load_question_orphan.py | load-question-rejects-unpaired-session | load-question on an arbitrary code auto-creates orphan _SP_STATE and a phantom category pick for an unpaired session | Guard sp_load_question on a trivia_session/lobby match; reserve create path for /api/pair/start; add TTL sweep |
| R038 | high | server-rest | final-results derive_tier | gate_r038_tier_denominator.py | tier-denominator-is-rounds-played | Tier denominator is answered-row count not rounds played, so a timeout vs a wrong answer yields different tiers for identical performance | Change derive_tier to `avg = total / max(1, total_rounds)` |
| R039 | high | client-browser | VariantC.tsx + usePuckState tap() MINIGAME branch | gate_r039_variantc_aim.py | variantc-bullseye-aim-present | VariantC has no BULLSEYE aim control; tap() defaults pending_quadrant to 'A', so it only wins when target=='A' (R020 unfixed for C) | Add a MINIGAME aim block (A/B/C/D -> actions.tilt) to VariantC mirroring VariantA; optionally require an aim before fire |
| R040 | high | mixed | ScoreboardScreen sort/isWinner + final-results payload | gate_r040_scoreboard_tiebreak.py | scoreboard-tie-break-deterministic | Final scoreboard never applies the documented tie-break; payload omits response-time/rank so ties resolve by V8 sort order | Add aggregate response_time_ms / server rank to final-results, sort total -> avgResponseMs -> puck_id, crown all co-leaders |
| R041 | high | client-browser | lib/audio.ts + every *Screen.tsx unmount cleanup | gate_r041_audio_no_bleed.py | sfx-stopped-on-route-change | audio.ts has no stop/pause API; fire-and-forget samples on a shared element never pause, so SFX/stingers bleed across routes | Add audio.stopAll()/stopSamples() (pause + reset currentTime, ramp osc gains to 0); call it in each screen unmount / route-change effect |
| R042 | medium | server-rest | _maybe_emit_reveal winner tracking + _build_pick_offer | gate_r042_picker_after_wipeout.py | wipeout-round-resets-picker | Who-picks-next reuses the stale last non-zero winner after an all-zero wipeout; last_round_winner_puck_id is never reset | Reset last_round_winner_puck_id to None on a wipeout (best_pts<=0), or track a per-round had_winner flag and fall back to expected[0] |
| R043 | medium | server-rest | sp_reset (no session-existence guard) | gate_r043_reset_phantom_state.py | reset-rejects-unknown-session | reset on an unknown code fabricates phantom _SP_STATE (exists false->true), so a puck recovers to IN_GAME_IDLE and hangs | Guard sp_reset: 404/409 without creating state when the code has no backing session, keeping exists faithful |
| R044 | medium | server-rest | final-results correct vs in-memory reveal | gate_r044_correct_undercount.py | scoreboard-correct-matches-reveals | Scoreboard correct under-counts: REVEAL-forced corrects and timeout-then-revealed rounds have no/stale DB row | Derive correct from in-memory per-round reveal results, or UPDATE post-arm is_correct back to trivia_answers (same root as R029) |
| R045 | medium | server-rest | sp_power_up_activate STEAL branch | gate_r045_steal_target_validation.py | steal-target-validated | STEAL activate accepts any target_puck_id (phantom or self) with no validation, silently consuming the one-shot for zero effect | Validate `int(target) in expected_pucks` and `target != puck_id`; return 400 and do not remove the item on failure |
| R046 | medium | mixed | _maybe_auto_resolve_pick + CategoryPickScreen | gate_r046_pick_timeout_feedback.py | pick-timeout-emits-lock-cue | Pick-timeout auto-default emits no category_picked socket, so the TV plays no pickLocked SFX and never highlights the chosen card (open R019) | Emit category_picked (auto:true) in _maybe_auto_resolve_pick, or call audio.pickLocked()+setChosenId in the TV kicked branch |
| R047 | medium | client-browser | ScoreboardScreen.tsx (no 30s auto-return) | gate_r047_scoreboard_auto_return.py | scoreboard-auto-returns-to-title | ScoreboardScreen never auto-returns to title; a finished match with no puck action pins the bar TV on the scoreboard forever (UX-10 not implemented) | Add a useEffect setTimeout(navigate('/'), 30000) cleared on unmount and cancelled if match_reset/lobby_cancelled fires |
| R048 | medium | client-browser | QuestionScreen handoff breath + narrationTimersRef | gate_r048_breath_timer_leak.py | breath-timer-cancelled-on-unmount | R023 breath setTimeout is not tracked in narrationTimersRef, so on early exit beginAnswering still runs and POSTs start-timer from an unmounted screen | Push the breath timer id to narrationTimersRef; add an aborted flag the cleanup sets and guard beginAnswering on it |

**Severity breakdown:** 1 critical (R029), 11 high (R030–R041), 8 medium (R042–R048).

## Verification split — REST-now vs browser-truth-required

These gates were authored against `http://localhost:5002` (REST) or as in-process unit
gates and can be PROVEN fail-on-current with curl/requests + the server venv as soon as
CPU frees up — no browser needed:

**Server-REST / unit verifiable now (12):**

- R029 — final-results-matches-cumulative-not-db-sum (in-process unit: drives real scoring fns)
- R030 — play-again-clears-prior-answers (REST pair + match drive)
- R032 — shotclock-late-fire-scores-zero (REST drive + unit control on _score_minigame_fire)
- R035 — steal-order-independent-and-answer-gated (unit: imports _apply_power_up_arms)
- R037 — load-question-rejects-unpaired-session (pure REST)
- R038 — tier-denominator-is-rounds-played (REST, read-only DB for deterministic answers)
- R040 — scoreboard-tie-break-deterministic (pure REST)
- R042 — wipeout-round-resets-picker (REST, read-only DB for round-1 winner)
- R043 — reset-rejects-unknown-session (pure REST)
- R044 — scoreboard-correct-matches-reveals (REST drive; browser used ONLY to pair pucks)
- R045 — steal-target-validated (pure REST, retries matches to land a STEAL)
- R031 — timed-out-puck-with-reveal-not-marked-correct (REST drive + python-socketio reveal capture; no browser)

**Browser-truth required (8) — deferred to sp-audit-fix:**

- R033 — answer-after-reveal-rejected (mixed; browser only to pair, but classed mixed)
- R034 — leave-match-route-prunes-expected-pucks (mixed; browser pair + lane observation)
- R036 — force-reveal-failure-still-advances (mixed; needs TV advance observation)
- R039 — variantc-bullseye-aim-present (client-browser; drives two VariantC pucks, intercepts fire POSTs)
- R041 — sfx-stopped-on-route-change (client-browser; audio element/waveform truth — touches audio, run only after Kokoro regen ends)
- R046 — pick-timeout-emits-lock-cue (mixed; decisive check is __sfxLog browser truth)
- R047 — scoreboard-auto-returns-to-title (client-browser; observes TV self-navigation)
- R048 — breath-timer-cancelled-on-unmount (client-browser; in-page fetch tap)

Note: R033/R034/R036/R046 are "mixed" — the bug is observable over REST but the
decisive assertion needs a browser session (to pair pucks or observe TV navigation / SFX
log), so they are grouped with browser-truth-required for execution scheduling.

## Dropped candidates (with reasons — nothing silently ignored)

| Dropped candidate | Reason |
|-------------------|--------|
| Host can never reach 'start' state until /confirm | Tagged R016 (FIXED+gated). Re-description of the by-design dial-confirm handshake; no regression evidence. |
| Demo-mode Lobby auto-start race on null hostPuckId | Speculative demo-only race, no concrete repro; demo path is not the bar-kiosk flow. |
| Audio bus has no stop(); Pair/Lobby MP3s keep playing | Duplicate of R041 (canonical no-stop-API finding). Merged. |
| TitleScreen pair_started ignores host_puck_id; joiner bounces TV | Contrived sequence the single-TV bar deployment never produces. Speculative. |
| PairScreen joiner branch unreachable dead-end | Self-described unreachable dead code contingent on the dropped pair_started edge. |
| LobbyScreen mid-lobby refresh double-navigates / races match_started | Speculative ~50ms race, at most a duplicate history entry; no functional break. |
| PairScreen demo auto-dial setError-after-unmount warning | Demo-only React unmount warning; no production impact. |
| CountdownScreen plays sfx_reveal on GET READY instead of a tick | Cosmetic cadence nit / product decision; risks over-fixing an intentional cue. |
| CategoryPickScreen replays pickShow() on every mount | Only on TV reload/remount in the 10s window; nit, not a regression. |
| Answer scoring runs on load-time clock not narration-end clock | Overstated; R007 FIXED (start-timer realigns clocks). Normal flow does not reproduce. |
| Late answer for a puck NOT in expected_pucks recorded but never scored | Merged into R033 (same revealed_for_question_id root fix). |
| Narration-skip branch on duplicate applyQuestionShown never arms beginAnswering | Speculative React-18-StrictMode chain; narratedQidRef guard is the R010 fix working. |
| R023 breath unobservable on no-narration path | By-design narrow; the concrete defect (untracked breath timer) is kept as R048. |
| start-timer emits timer_started but QuestionScreen never listens | Acknowledged UX-06 PARTIAL (reconnect resync); covered by force-reveal+advance loop. |
| BULLSEYE fire-blind defaults to quadrant A in usePuckState.tap() | Merged into R039; the actionable concrete bug is VariantC lacking any aim UI. |
| TV MinigameScreen does not rehydrate landed fires on reload | Low-value reload-resilience nit; markers repopulate from live sockets, round resolves. |
| BULLSEYE aim reticle can persist after fire (socket ordering) | Speculative cosmetic, no scoring impact, contrived repro. |
| minigame/preview accepts invalid quadrant strings unvalidated | Benign; invalid quadrants dropped client-side; hardening nit. |
| SHOT_CLOCK sweep pointer visually lags scored position | Client-truth pixel claim; cannot be REST-verified, deferred to browser phase. |
| SHOT_CLOCK gives no on-bar indication of where each puck fired | UX polish, not a correctness defect. |
| SHOT_CLOCK t_ms floors to 0 producing a guaranteed miss at window start | In-Hub benign; clock-skew portion unverifiable; overlaps R032 work. |
| Play-Again leaves Slice-E in-memory keys stale | Did NOT reproduce live (dict replaced wholesale, defaults backfilled). Real reset defect is R030. |
| No MAX_PLAYERS cap: pucks > 8 accepted with white fallback | Out of documented 8-puck envelope; bar table never exceeds it; risks breaking test setups. |
| Power-up earned in a minigame can't be activated until next question | By-design (SP_PICK_ROUNDS timing); consistent with the catalog. |
| DOUBLE stacks with STEAL for a 2.5x swing | Self-described "balance only"; no correctness defect. |
| sp_reset relies on lazy setdefault backfill (fragile) | No crash/KeyError reproduces; code-hygiene note. Real reset bug is R030. |
| Solo (N=1) match strips the power-up layer | Internally consistent, no crash; degenerate-mode design consequence. |
| Empty-results final-results shows players:[] for all-timeout match | Same DB-as-source root as R029/R044; folds into the R029 fix. |
| Tie for first place crowns only one puck arbitrarily | Duplicate of R040 (canonical tie-break). Merged. |
| Host HOLD_3S cancel emits room-scoped while clear emits globally | Tagged R008 (FIXED+gated); failure needs reconnect-to-wrong-room (UX-06 PARTIAL). |
| _resolve_minigame sets minigame_resolved_round=round+1 using stale round | Self-described static risk; normal path correct; speculative double-mount. |
| No grace/opt-out window on Play-Again | Documented spec UX-08 GAP; product decision, not a code defect. |
| Left/absent picker still in expected_pucks | Downstream of R034; folds into its expected_pucks pruning fix. |

## Next run (sp-audit-fix) checklist

Run only after the Kokoro narration regen (PID 73387) finishes and the MP3 files under
`server/static/games/speed-pyramid/audio/` are stable. For EACH id below, in order:

1. **Run the gate, prove FAIL on current** — execute the gate against the live build
   and confirm the decisive assertion is RED (records the fail-on-current proof). If the
   gate reports inconclusive, fix the gate, not the build — inconclusive counts as fail.
2. **Apply the minimal fix** — implement the fixSketch above; touch only the named file(s).
3. **Prove PASS + regression sweep** — re-run the gate (GREEN) and run the full
   `e2e_full_match.py` + any sibling gates to confirm no regression of R001–R028.
4. **Finalize the regression_log row** — set Date fixed = run date, confirm the gate name.
5. **Per-bug commit** — stage ONLY the specific changed files for that bug
   (`git add <file> <gate> docs/regression_log.md`). NEVER `git add -A` /
   `git add .` — Kokoro is churning MP3s and a broad add would sweep regenerated audio
   and untracked junk into the commit. One commit per bug id.

Per-id list:

- [ ] R029 — gate_r029_final_results_cumulative.py (critical, run first)
- [ ] R030 — gate_r030_replay_answer_leak.py
- [ ] R031 — gate_r031_reveal_on_timeout.py
- [ ] R032 — gate_r032_shotclock_window.py
- [ ] R033 — gate_r033_answer_after_reveal.py
- [ ] R034 — gate_r034_leave_match_phantom.py
- [ ] R035 — gate_r035_steal_order.py
- [ ] R036 — gate_r036_force_reveal_advance.py
- [ ] R037 — gate_r037_load_question_orphan.py
- [ ] R038 — gate_r038_tier_denominator.py
- [ ] R039 — gate_r039_variantc_aim.py (browser)
- [ ] R040 — gate_r040_scoreboard_tiebreak.py
- [ ] R041 — gate_r041_audio_no_bleed.py (browser; audio — run only after Kokoro regen ends)
- [ ] R042 — gate_r042_picker_after_wipeout.py
- [ ] R043 — gate_r043_reset_phantom_state.py
- [ ] R044 — gate_r044_correct_undercount.py
- [ ] R045 — gate_r045_steal_target_validation.py
- [ ] R046 — gate_r046_pick_timeout_feedback.py (browser sfx log)
- [ ] R047 — gate_r047_scoreboard_auto_return.py (browser)
- [ ] R048 — gate_r048_breath_timer_leak.py (browser)

**Suggested ordering:** clear the 12 server-REST/unit gates first (cheapest, no browser),
then the 8 browser-truth gates. R029, R030, R044 share the DB-as-source-of-truth root —
fixing final-results authoritatively from cumulative_scores may green more than one at
once; verify each gate independently regardless. R031 and R035 share the
TIMEOUT-answer-gate fix in _apply_power_up_arms.
