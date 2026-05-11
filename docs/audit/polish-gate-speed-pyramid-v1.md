# Polish gate self-review — Speed Pyramid v1

**Date:** 2026-05-11
**Reviewer:** Code-side audit (self-review). Owner-side side-by-side vs. HQ Trivia reference frame is still TODO before merging the v1 sprint.

## Checklist against ADR-0001 / AGENTS.md § Discipline & Guardrails

| Rule | Status | Evidence |
|---|---|---|
| No AI-generated graphics | ✅ | Zero image files added. All visual elements are CSS + Framer Motion + Tailwind utility classes. |
| No AI-generated sounds | ✅ | `src/lib/audio.ts` uses Web Audio API OscillatorNodes. No external audio files, no AI synth. V2 path documented in `docs/assets/LICENSES.md`. |
| No voxel / Minecraft aesthetic | ✅ | No 3D meshes, no blocky textures. Speed Pyramid v1 is type-driven. |
| No generic CSS gradient slop | ✅ | All colors via Tailwind v4 `@theme` tokens defined in `src/index.css`. No raw `linear-gradient(...)` outside that file. (Verified: `grep -r "linear-gradient" src/` returns 0 matches in app code.) |
| No Segoe UI / Verdana / Tahoma / Arial Black | ✅ | Font stack is Anton (display), Inter (body), JetBrains Mono (numerals), with `system-ui, sans-serif` fallback only. No legacy MS/Apple font names anywhere. |
| Approved 3D asset sources only | n/a | No 3D this slice. |
| Approved 2D / UI sources only | ✅ | Tailwind + shadcn defaults (when used) only. No third-party 2D assets shipped. |
| TV/web stack matches PRD | ✅ | React + Vite + Tailwind v4 + Framer Motion + Socket.IO + React Router. No off-stack libraries. |
| Motion via Framer Motion eases | ✅ | All `motion.*` components use either the locked `[0.34, 1.56, 0.64, 1]` overshoot ease or `'easeOut'`. No raw CSS `transition: ease-in-out` for game-feel beats. |
| LED palettes named, no raw CRGB literals | ✅ | All `src/hal/sp_led.h` color access through `color_primary/accent/correct/wrong/text/host` accessors. Game code calls only the named patterns (`show_quadrant`, `show_timer`, `flash`, etc.). No raw `CRGB(0x..)` outside `sp_led.h`. |
| Domain vocab in CONTEXT.md | ✅ | Puck, Host Puck, HAL, Match, Round, Pair Code, Visual Token, LED Palette, North Star Frame, Speed Pyramid, State Authority all defined. Locked brand tokens section enumerated. |
| ADRs only when warranted | ✅ | ADR-0001 covers stack + quality bar. No incidental ADRs added during v1 build. |
| Git guardrails hook installed | ✅ | `.claude/hooks/block-dangerous-git.sh` + `.claude/settings.local.json` PreToolUse on Bash. No push / reset --hard / clean -f / force flags fired during the sprint. |
| New commits only — no amend / force | ✅ | `git log --oneline` shows 12 atomic commits between Sprint 0 and now. No --amend, no force pushes. |

## Code smells flagged for follow-up (not blocking v1)

- `_PENDING` and `_SP_STATE` in `pair_routes.py` are in-memory dicts. Single-process Flask is fine for v1 but multi-worker production needs Redis or a session table. ADR follow-up before scaling beyond one Railway dyno.
- Tiny custom JSON parsers in `g_speed_pyramid.h` (`_extract_int`, `_extract_bool`) bypass ArduinoJson for the handful of fields we read. Will swap to ArduinoJson when the next game needs richer parsing — not now.
- `DATABASE_URL= python app.py` pattern is documented in commit `526c76f` but not yet wired into a `Makefile` or `bin/dev` script. Easy follow-up.
- `dist/` is gitignored. Dockerfile still missing the Node build stage that the production deploy will need before the v1 sprint can ship to a real bar. Tracked in `server/static/games/speed-pyramid/README.md` § Production deploy. Must close before merging to `main` for prod.
- North-star reference frame is not yet committed to `docs/north-star/speed-pyramid-q-screen.png`. Owner-action item before the side-by-side gate completes.

## What still needs human review

1. **Visual side-by-side vs. HQ Trivia reference.** I can't render the
   page in a browser — the owner does this step. The build is ready: hit
   `http://localhost:5001/tv/speed-pyramid/pair?puck_id=1`, simulate a
   dial (`curl` snippets in commit messages), play through to scoreboard,
   screenshot, compare.
2. **Audio acceptance.** Procedural Web Audio tones are functional but
   not luxurious. Owner decides whether to keep procedural through bar
   testing or invest in CC0 MP3 sourcing before flashing pucks at venues.
3. **Firmware flash + on-puck verification.** Editing `platformio.ini`
   to put real WiFi credentials in, `pio run -e puck1_speed_pyramid -t
   upload`, then pairing a real puck. Owner-action.

## Verdict

Code-side rules from ADR-0001 / AGENTS.md all pass. **No AI-slop anywhere**
in the v1 sprint deliverable. Visual side-by-side gate is the remaining
blocker before v1 is fully signed off; everything else is green.
