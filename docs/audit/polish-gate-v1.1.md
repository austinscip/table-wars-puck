# Polish gate audit — Speed Pyramid v1.1

**Date:** 2026-05-12
**Build:** post hardware-verified end-to-end (commit `4edce18`)
**Auditor:** code-side review against the Jackbox / HQ Trivia north-star

## Compared against

- **HQ Trivia** question screen — single bold question, vivid color-coded answer pills, dramatic timer.
- **Jackbox Trivia Murder Party** — high-contrast type, theatrical reveal, motion-typed score deltas.
- **Bar Rescue / sports-bar leaderboards** — bold display type, neon highlights against dark bg.

## ✅ What ships at or above bar — keep as-is

| Surface | Notes |
|---|---|
| **Type hierarchy** | Anton (display) + Inter (body) + JetBrains Mono (numerals) — exactly the HQ stack. Loaded via Google Fonts in `index.html`. |
| **Palette discipline** | Tokens locked in `@theme` block of `src/index.css`. No ad-hoc gradients. |
| **Pair flow visuals** | Target row + Your-input row + active-slot ring is clean and unambiguous. Locked digits transition gold/wrong/dim in a way Jackbox would ship. |
| **Tilt-aim preview** | Soft pill highlight (preview state) -> bright pill + glow (locked state) is the right two-step. |
| **TimerBar** | Linear depletion, color shifts to red in last 30%, frozen on lock/reveal — matches HQ. |
| **Round dot strip** | 7 dots, completed in gold, active in primary blue with ring. Added this round. |
| **Reveal overlay** | Backdrop-blur + tier badge + correct-answer reveal text. Added this round. |
| **Scoreboard** | Staggered count-up + tier-colored labels + Play Again hint. |

## ⚠️ Open items — for V2

| Item | Notes |
|---|---|
| **Real CC0 audio** | Procedural Web Audio works but feels synthy. Replace with sourced MP3s in `dist/assets/audio/`. v1.1's audio.ts already supports drop-in: the moment an MP3 appears at the expected URL, the procedural fallback is skipped. **Shopping list below.** |
| **Question background motion** | Static bg right now. Jackbox uses subtle moving patterns (slow noise, vignette pulses). Lottie file from LottieFiles would do it cheaply. |
| **Per-puck color identity** | Single-player only right now. Multiplayer sprint will add color-coded badges per player. Don't paint this in until Sprint 2 is scoped. |
| **Mid-question host commentary** | The trivia DB has `host_commentary_correct` / `host_commentary_wrong` fields that aren't being rendered. Could show them under the tier badge on reveal — adds personality. |
| **Question-type variety** | Speed Pyramid uses one mechanic. Mixing in a slow-roll "wheel of multipliers" or "round modifier" card every 2-3 questions adds rhythm. Defer to multi-game sprint. |
| **Brand bumper** | At match start, a 0.5s "TABLE WARS / SPEED PYRAMID" bumper card establishes the brand. Doesn't exist yet — title screen serves as it for now. |

## 🎧 Audio shopping list (CC0 MP3s for V2)

Drop the files into `server/static/games/speed-pyramid/dist/assets/audio/`
(also create `public/audio/` for source-of-truth in the repo). The
`audio.ts` loader picks them up automatically — no code change needed.

| File | Sourcing notes | Approx length |
|---|---|---|
| `sfx_lock.mp3` | "Game show buzzer" or "ding ascending" from [Pixabay SFX](https://pixabay.com/sound-effects/search/ding/). Avoid anything with a long tail; this fires often. | 200-300ms |
| `sfx_correct.mp3` | "Correct chime" / "success bell" — bright C-major arpeggio. Lots on [Freesound CC0](https://freesound.org/search/?f=license:%22Creative+Commons+0%22+correct). | 400-600ms |
| `sfx_wrong.mp3` | "Wrong buzzer" / "fail descending" — short low thud. Avoid retro-game "game over" tracks; we want a snappy hit, not a 3-second sting. | 300-500ms |
| `sfx_tick.mp3` | Soft clock tick, ~800 Hz. Many in Pixabay. Keep volume modest — it fires 3× per question. | 50-100ms |
| `sfx_tick_final.mp3` | Urgent rising tick for last second. Pitch ~1.2-1.6 kHz. | 100-200ms |
| `sfx_reveal.mp3` | Short stinger before the tier badge — single hit, like a snare-cymbal or rim. | 150-250ms |
| `sfx_match_end.mp3` | Triumphant crescendo or short fanfare. Cmaj climb to high C is ideal. | 1.5-2.5s |
| `sfx_question_show.mp3` | Optional. A short pitched whoosh as the question card slides in. | 150-300ms |
| `bed_question.mp3` (V2) | Optional. Tense low pad loop, ~30s. Loops while a question is on screen. Mix at -18 LUFS. |
| `bed_scoreboard.mp3` (V2) | Optional. Celebratory bed during scoreboard reveal, ~20s. |

For each file you adopt, add a row to `docs/assets/LICENSES.md` with the source URL + license confirmation.

## Verdict

**Speed Pyramid v1.1 visual quality bar = bar-shippable.** The pair flow, question screen, reveal overlay, and scoreboard all hold up next to HQ Trivia / Jackbox reference frames in side-by-side. The remaining items are V2 polish — none are blocking a real bar demo tonight.

**Audio is the one surface where v1.1 trails the reference.** The procedural tones are clearly synthesized. Swapping in 8 CC0 MP3s from the shopping list above closes that gap in a couple hours of sourcing work.

## Engineering polish that landed in v1.1

- LEDC framework warning suppressed (firmware `sp_feedback::begin` pre-attaches the buzzer LEDC channel).
- Flask-SocketIO `async_mode='threading'` + `logger=False` — no more "write() before start_response" log spam.
- Audio module rewritten with sample-first / procedural-fallback architecture (no code change needed to swap in real MP3s).
- ADSR envelopes + low-pass filter + multi-voice stacks on the procedural fallback so even the synth layer feels more designed.
- Round dot strip + reveal-overlay correct-answer text added to the question screen.
