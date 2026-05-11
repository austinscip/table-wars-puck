# ADR 0001 — Quality Bar, Visual Stack, and No-AI-Slop Rule

**Status:** Accepted
**Date:** 2026-05-11

## Context

Table Wars is a commercial product for bars and restaurants. Patron engagement and bar-owner buy-in both depend on the perceived quality of what plays on the TV. Earlier demos used AI-generated placeholder graphics and Minecraft-style voxel visuals. The owner reviewed these and rejected them outright. We've also confirmed (by reading `games/trivia-buzzer.html`) that some existing in-repo TV games rely on generic CSS gradient + Segoe UI aesthetics — that is exactly the look we will not ship.

We are not a game studio. We will not produce original art. But the visual ceiling we ship at determines whether bars renew their contracts.

## Decision

Lock the visual quality bar and the supporting tech stack now, as a project-wide rule enforced in `AGENTS.md`.

**Hard rules:**
- No AI-generated graphics, music, or SFX. No SDXL / DALL-E sprites, no text-to-3D models, no AI-generated audio.
- No voxel / Minecraft aesthetic.
- No generic CSS gradient slop. No Segoe UI / Verdana, no purple linear-gradient defaults, no rgba opacity as a polish substitute.
- Polish gate: every TV game is screenshotted next to a Jackbox / HQ Trivia / Bar Rescue reference before ship. If it looks worse, it does not ship.

**Approved asset sources (CC0 / royalty-free / professional):**
- 3D: Kenney.nl, Quaternius, Kay Lousberg, Synty POLYGON (paid but cheap), Poly Pizza, Sketchfab CC0
- 2D / UI: Kenney UI packs, shadcn/ui, Heroicons, Phosphor Icons, LottieFiles
- Audio: Pixabay SFX, Freesound CC0, Kenney Audio packs

**TV / web tech stack:**
- 3D scenes (Greyhound Racing, Puck Wars, Space Invaders 3D): Three.js + React Three Fiber + Drei
- 2D arcade (Pong, Puck Golf, Word Association scroll): PixiJS or Phaser 3
- Game-show UI (Speed Pyramid, Trivia Murder Party, scoreboards): React + Tailwind + shadcn/ui + Framer Motion for kinetic typography
- Background motion graphics: Lottie animations from LottieFiles

**Firmware LEDs:**
- Named palettes only (`PALETTE_TRIVIA_CORRECT`, `PALETTE_VICTORY`, `PALETTE_ELIMINATION`, etc.), eased transitions. No raw CRGB literals in game code.

## Consequences

- Existing `games/*.html` and `server/templates/tv_games/*.html` that use the slop aesthetic are technically debt now. They get reskinned during the "Audit existing TV game polish" task, prioritized by which games are anchor genres (trivia first).
- New TV game work goes through React/Three.js/PixiJS — not raw HTML/CSS in a Flask template. Flask templates remain as a runtime shell; the game canvas inside them is React-based going forward.
- Asset licensing must be tracked. Each pack we adopt gets a one-line entry in `docs/assets/LICENSES.md`. No exceptions.
- Polish gate adds review friction. Acceptable cost — it is the rule that prevents the original failure mode.

## Alternatives considered

- **Hire a designer per game.** Right answer in steady state. Wrong answer now: budget and timeline don't support it. Asset packs get us to professional baseline cheaply.
- **Use a single game engine (e.g. Unity WebGL) for everything.** Heavy runtime, slow loads on smart-TV browsers. R3F + PixiJS keep payloads small and stay on the standard web stack.
- **Keep the existing CSS-only TV templates and just retheme them.** Considered. Rejected because the architecture itself (raw HTML + emoji + linear-gradient) hits a hard ceiling before professional polish.

## Related

- `AGENTS.md` — "Discipline & Guardrails" section enforces this ADR
- `CONTEXT.md` — defines Visual Token, LED Palette, North Star Frame
- Future ADRs that will follow: 0002 firmware HAL boundary, 0003 Smart-TV-direct-browse vs on-site host, 0004 Rev A/Rev B coexistence in firmware
