# Virtual Puck Hub — Prototype Notes

## Question this prototype answers

What should a per-puck control panel look like in the Sandbox **Hub** (`/dev/hub`)? Underlying state machine + endpoint POSTs are identical across all three variants; only the rendering differs.

## Three variants on `/dev/hub?variant=A|B|C`

| Key | Name | Shape | Best for |
|---|---|---|---|
| **A** | Compact stacked | One row per puck. State badge + inline buttons. Minimal vertical footprint, 8 fit on screen. | Watching many pucks race through states |
| **B** | Game controller | Chunky controller card per puck. D-pad + ABCD face buttons. Mimics holding the real ESP32. | Solo "I'm pretending to play" |
| **C** | Workshop form | Tall vertical, every state field labeled. Every action a separate row. | Debugging state machine bugs |

Floating switcher at the bottom cycles them; `←` / `→` keys too.

## Verdict

_(fill in when picked)_

**Winner:** ___ — because ___.

## Bugs surfaced by the prototype

These got caught during the first Hub test run and feed back into Slice C / future work:

1. **Round-2 start** — `sp_load_question` increments `state["round"]` unconditionally on every POST. Two Virtual Pucks each polling load-question caused the round counter to advance twice → match started on round 2. **Fixed in the prototype** by removing the load-question POST from `usePuckState` (real firmware doesn't call it either; the TV is the sole caller). **Server-side fix still needed** for Slice C: make load-question idempotent so two callers can't double-advance state. File a separate ADR if we want to permanently encode "load-question is TV-only" as an architectural invariant.

2. **No category pick at sandbox HEAD** — that's not a bug; category picker, minigames, and sabotage are prod-only working-tree edits that haven't been committed yet. Sandbox HEAD plays linear 7-question matches. Those features land via Slice C cherry-picks.

## Absorption checklist (after verdict)

- [ ] Delete the two losing variant files under `./variants/`.
- [ ] Delete `./PrototypeSwitcher.tsx`.
- [ ] Inline the winner's render into `./Hub.tsx` directly (no more variant prop).
- [ ] Delete this NOTES.md.
- [ ] Update CONTEXT.md to reference the chosen layout if it's load-bearing for future readers.
- [ ] Run `npm run build:sandbox` — verify no orphan imports.
- [ ] Re-run `python scripts/e2e_smoke.py` — should still pass (Hub isn't on the e2e path yet, but make sure nothing broke).

## What this prototype does NOT cover (deferred to v1.1)

- Active power-up use (2X / REVEAL / TIME buttons per puck).
- Sabotage targeting (cross-puck "fire sabotage at puck 3").
- Aim selection in minigames (currently `tap` fires a fixed-quadrant shot).
- Per-puck LED ring visualization.

These are all real features but the lean MVP brief was "play a full match end-to-end via mouse." The Hub already does that.

## How to run

```bash
# Sandbox Flask on :5002 (separate from prod on :5001)
cd ~/table-wars-puck-sandbox/server
DATABASE_URL= PORT=5002 venv/bin/python app.py &

# Built TV bundle includes /dev/hub when VITE_DEV_TOOLS=1
cd static/games/speed-pyramid
npm run build:sandbox

# Open in browser
open 'http://localhost:5002/tv/speed-pyramid/dev/hub'
open 'http://localhost:5002/tv/speed-pyramid/'  # TV in another window
```
