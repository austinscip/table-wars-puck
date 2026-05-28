# Sandbox session handoff

If this chat hits context limits, start a new conversation with:
> "Read `~/table-wars-puck-sandbox/docs/handoff.md` and continue."

## What this project is

`~/table-wars-puck-sandbox/` — git worktree off `~/table-wars-puck/`,
branch `sandbox`. Flask on **:5002**, prod is **:5001** and untouched.
`puck1_dev_speed_pyramid` / `puck2_dev_speed_pyramid` envs point at
:5002. Bar pucks stay on prod envs. **Never** edit `~/table-wars-puck/`
directly; sandbox-first is the locked working agreement.

## How to start a session

1. Read `~/.claude/projects/-Users-austinscipione/memory/feedback_no_unguarded_fixes.md`
   first — the user is allergic to "fixed" claims that aren't backed by a
   permanent gate assertion.
2. Read `~/.claude/projects/-Users-austinscipione/memory/project_table_wars_sandbox.md`
   for the sandbox architecture (Flask :5002, dev pucks, etc.).
3. Read `docs/regression_log.md` (this directory) — every bug ever found
   + the gate assertion that proves it stays fixed.
4. Read `docs/handoff.md` (this file).
5. Check Flask is running on :5002 (`lsof -iTCP:5002 -sTCP:LISTEN -n -P`).
   Start it if not: `cd ~/table-wars-puck-sandbox/server && DATABASE_URL= PORT=5002 venv/bin/python app.py &`.

## Verification commands

Run these to make sure you're starting from a known-green baseline:

```bash
cd ~/table-wars-puck-sandbox/server
DATABASE_URL= venv/bin/python scripts/e2e_smoke.py              # → 11/11
DATABASE_URL= venv/bin/python scripts/diag_e1_pick.py           # → ALL PASS
DATABASE_URL= venv/bin/python scripts/diag_e2_minigame.py       # → ALL PASS
DATABASE_URL= venv/bin/python scripts/diag_e2_hub.py            # → ALL PASS
DATABASE_URL= venv/bin/python scripts/diag_e3_power_ups.py      # → ALL PASS
DATABASE_URL= venv/bin/python scripts/diag_f_aim_preview.py     # → PASS
cd ~/table-wars-puck-sandbox && pio run -e puck1_dev_speed_pyramid  # → SUCCESS
```

Strong end-to-end gate:
```bash
DATABASE_URL= venv/bin/python scripts/e2e_full_match.py
# (currently partial PASS — see "still open" section below)
```

## Working agreement with the user

User is **fed up with regressions**. The discipline (now also stored
as user-level memory) is:

1. **Every bug fix lands with a permanent gate.** Add a named assertion
   to `e2e_full_match.py` that would FAIL if the bug recurred. Add a row
   to `docs/regression_log.md`. No exceptions.
2. **No "tests pass" claims for synthetic conditions.** If the gate
   doesn't exercise the real-user flow (Hub UI + TV via Playwright),
   say so explicitly.
3. **Past bugs need retroactive coverage too**, not just future ones.
4. **State-machine bugs need full-cycle exercise** (multi-round + Play
   again). Single-question tests miss these.
5. **Real audio capture** for audio bugs (browser `__audioEvents`
   probe, not just API-field checks).

The user explicitly said: "i'm tired of fixing the same mistakes. you
make sure anything you do is planned in development such that no bug
keeps persisting EVER — for both past, present, and future bugs."

## 2026-05-28 — end-to-end audit batch (R029–R048)

A multi-agent audit swept every screen, all 1–8 player counts, every
power-up combination (incl. SHIELD-blocks-STEAL), lifecycle controls
(Reset-all / Back-to-start / leave-match), narrator timing, audio
cleanup, and the full state machine. 73 raw findings → 20 confirmed →
**18 fixed + committed**, R039 dropped (VariantC fire-only is by-design),
R041 left open (audio-bleed: real `audio.ts` has no `stopAll`, but the
gate can't be exercised — no `sfx_*.mp3` sample assets exist; do not
fake-green it). Highlights: R029 final-results now uses in-match
`cumulative_scores` not DB-SUM; R031 closes R014 (REVEAL no longer
force-corrects a timed-out puck); R046 closes R019; R048 closes R023;
R040 adds a server-computed deterministic tie-break. Each fix has a
fail-on-current gate in `server/scripts/gate_r0XX_*.py` and a row in
`docs/regression_log.md`. Full report: `docs/audit/sp_audit_2026-05-28_findings.md`.

**Process lesson (important):** per-bug gates each verified against the
build *at their own commit*, so they missed a cross-fix interaction —
R044's gate (committed early) contradicted R031 (committed later). The
sequential **green-together** sweep (`/tmp/sp_green_together.sh` runs the
whole suite one-at-a-time) caught it; R044's gate was then reconciled to
the answered-REVEAL invariant. **Always run the whole gate suite together
after a batch, sequentially** (parallel Playwright runs cause CPU
contention → false greens).

**Still open after the audit:** R041 (needs SFX sample assets + a
`stopAll`), R012 (scoreboard X/N denominator — not separately gated),
R013 (Hub LOCKED-vs-TIMEOUT cosmetic, dev-tool only), R021 (commentary
fires before question card renders — needs a browser-truth gate). Letter
pronunciation (R011 family) is the Kokoro voice thread, separate.

**Caveat — uncommitted:** the 1,296 Kokoro-regenerated `audio/questions/*.mp3`
are unstaged on purpose (big binary change tied to the Piper→Kokoro voice
decision). Per-bug commits stage explicit paths only — never `git add -A`.

## What's done (commits since start of this work)

```
6b2a69e fix(sp): regression batch — scoreboard, hub TIMEOUT, audio gaps, commentator timing
270bf7b feat(sp): Slice E3 — Hub virtual puck UI for power-ups
a27dd45 feat(sp): Slice E3 — power-ups + sabotage (server-side)
8257974 feat(sp): Slice F — BULLSEYE aim preview reticles
ad3a55e feat(sp): Slice E2 — minigames (BULLSEYE + SHOT CLOCK) end-to-end
4cf2cbf chore(sp): finalize Slice L narration regen — all 1,180 MP3s present
af82067 feat(sp): Slice E1 — category picker end-to-end + Slice L data refill
e55e948 feat(sp): 8-player TV sidebar + scoreboard, tie-break documented
373fd85 fix(sp): narration uses Piper TTS + no more echo + cache-bust
b866c2d fix(sp): Back to start, Reset all, and narration timing — all wire to TV
8325040 feat(sp): hybrid reveal audio + per-puck feedback + narration MP3s
ec22924 feat(sp): wire audio_url + start-timer + host commentary on reveal
20c947c fix(audio): Q1 procedural fallback now fires
3edbdc9 fix(sandbox): Hub now plays unlimited matches end-to-end
cdf4a5c feat(sandbox): Virtual Puck Hub prototype + autoplay primer
ec32224 fix(sp): make sp_load_question idempotent
815b90c test(sandbox): Playwright e2e smoke harness
e509133 chore(sandbox): add puck1/puck2_dev_speed_pyramid envs
1130956 wip(sprint-2E): in-flight multiplayer hardening — pre-stabilization baseline
```

Big slices complete: L (data), K (8-player), E1 (picks), E2
(minigames), F (aim preview), E3 (power-ups). The forward plan is in
`~/.claude/plans/abundant-cuddling-dove.md`.

## What's still open

Pending slices from the original plan:
- **Slice G — TV visual polish.** Asset packs (Kenney / Quaternius /
  Synty / Kay Lousberg), Three.js / PixiJS canvas, Framer Motion
  choreography. The user's `feedback_puck_graphics` standard. Biggest
  visible quality jump. 2–3 sessions.
- **Slice I — Robustness.** Puck disconnect handling, Flask crash
  recovery, in-memory state → SQLite snapshot, late-join, tie-break
  documented (done) but not implemented as policy yet.
- **Slice M — Dead code cleanup.** Unused TierBadge, obsolete trivia
  seed scripts, dead diag_*.py once they're folded into the strong
  harness.
- **Slice J — Bar deployment readiness.** Firmware NVS config (currently
  hardcoded WiFi/server URL in `platformio.ini`), mDNS via
  python-zeroconf, real Jinja templates for the stub admin routes at
  `app.py:312,475`.
- **Slice H — Dev tooling hardening.** Fold `diag_*.py` into
  `e2e_full_match.py`, hide build chips + debug overlay behind
  `?debug=1`, A/B voice picker.

User-found bugs still open (from `docs/regression_log.md`):
- **R014** — Q7 timed out but server awarded "correct" to both pucks.
  Not yet reproduced. Suspect: REVEAL power-up was active without user
  realizing, or scoring path has a bug for TIMEOUT.
- **R019** — Pick timeout UX: when the 10s deadline expires, server
  auto-defaults silently. No visible/audible feedback.
- **R020** — Hub minigame controls (`◀ A`, `▶ B` etc.) don't respond.
  Most urgent — user can't actually play minigames in the Hub.
- Letter pronunciation: A/B/C/D sometimes sound bad even after the
  `A: <answer>` format fix. Specific to Piper output. User said "B and
  C sound like shit" most often.
- No instructions on minigame / category-pick screens — user doesn't
  know HOW to interact.

## How to fix bugs (the discipline)

For each bug:

1. **Find a row in `docs/regression_log.md`** or add one. Use a fresh
   `R0XX` ID, today's date, brief description, gate-assertion name TBD.
2. **Reproduce in a script first.** Either via Playwright through the
   Hub UI (preferred), or via curl/REST. Don't rely on user testing
   to verify — write the reproduction.
3. **Fix the code.** Tight scope; don't refactor unrelated areas.
4. **Add a permanent assertion** in `e2e_full_match.py` (preferred)
   or in `e2e_smoke.py` (acceptable for narrower scope). Use the same
   gate-assertion name as in the log row.
5. **Run the gate.** Confirm it passes. Also run the per-slice diag
   sweep above to confirm no regression.
6. **Commit with R0XX in the message.** Update `docs/regression_log.md`
   row: set "Date fixed", confirm gate name.
7. **Tell the user**: "Fixed R0XX, gate assertion `<name>` passes.
   Refresh + retest please." No "fixed" claims without that gate.

## Architecture notes

- Sandbox runs on Flask :5002. Build artifacts in
  `server/static/games/speed-pyramid/dist/` (via `npm run build:sandbox`
  in `server/static/games/speed-pyramid/`). VITE_DEV_TOOLS=1 enables
  the Hub at `/dev/hub`.
- State per session lives in `pair_routes.py` `_SP_STATE[sc]` dict
  (in-memory; Flask restart loses all). Slice I will add SQLite
  persistence.
- Round flow: pick (rounds 1/3/5/7) → question; minigame
  (rounds 2/4/6) → question. Pick auto-defaults to first offer at 10s.
- Round-N winner picks for round N+1 (most recent question-round
  winner). Tie-break: highest points → faster response_time_ms →
  lowest puck_id.
- Power-up catalog: DOUBLE / SHIELD / REVEAL / STEAL. Granted to
  minigame winners only. Activated between rounds (pending pick or
  minigame phase). Applied at next reveal.
- Cache-busted MP3 narration via `?v=<mtime>` in audio_url. 1,180
  question MP3s on disk (116 setup-less questions silently 404 and
  the TV gracefully handles).

## Useful greps when investigating bugs

```bash
# What does the server emit when X happens?
grep -n "_socketio.emit" ~/table-wars-puck-sandbox/server/pair_routes.py

# How does the TV navigate?
grep -rn "navigate(" ~/table-wars-puck-sandbox/server/static/games/speed-pyramid/src/screens/

# What's in match-state?
curl -s http://localhost:5002/api/sp/match-state/SESSION_CODE | python3 -m json.tool

# What's the puck state shape?
grep -n "kind:" ~/table-wars-puck-sandbox/server/static/games/speed-pyramid/src/dev/usePuckState.ts | head
```

## Most urgent thing right now

User can't play minigames in the Hub — R020. Most likely cause: the
"Fire" button text in `VariantA` MINIGAME conditional isn't what the
user expects to click, OR SHOT_CLOCK flavor doesn't render a usable
button. Look at:

- `server/static/games/speed-pyramid/src/dev/variants/VariantA.tsx`
  line ~150 (MINIGAME conditional block)
- `server/static/games/speed-pyramid/src/dev/usePuckState.ts` `tap()`
  in MINIGAME branch — confirm it fires `/api/sp/minigame/fire` for
  both flavors.

Also, the MinigameScreen has no on-screen instructions. Players don't
know what to do. Add "Tap when in green" or "Tilt and tap" instructions.
