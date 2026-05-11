# Speed Pyramid v1 — TV view

Vite + React + TypeScript + Tailwind v4 + Framer Motion + Socket.IO client. Built as a static SPA, served by the Flask app at `/tv/speed-pyramid/*`.

## Brand tokens

All color, type, and motion tokens live in `src/index.css` under the Tailwind v4 `@theme {}` block. `tokens.json` is the human-readable mirror (kept in sync with `CONTEXT.md` and `docs/adr/0001-quality-bar-and-stack.md`). No raw RGB literals or font names anywhere in component code.

## Dev workflow

```bash
# from this directory
npm install      # first time
npm run dev      # vite dev server at http://localhost:5173 (HMR)
```

For Flask-integrated dev (talking to the real backend), build once and open via Flask:

```bash
# from this directory
npm run build

# from the repo root
cd server && python app.py
# then open http://localhost:5001/tv/speed-pyramid
```

## Production deploy

Currently the `dist/` output is gitignored and Flask serves whatever's already built locally. For Railway / Docker production, the `Dockerfile` needs a Node stage that runs `npm install && npm run build` before the Python stage copies `dist/` into the image. **TODO** — wire this in when the first slice 1A landing is ready to ship to a bar.

## File layout

```
src/
  main.tsx           # entry
  App.tsx            # router shell
  index.css          # tailwind import + @theme tokens
  screens/
    TitleScreen.tsx  # 'SPEED PYRAMID' title (slice 1A)
    # PairScreen.tsx       (slice 1B)
    # QuestionScreen.tsx   (slice 1C)
    # Scoreboard.tsx       (slice 1D)
  components/
    # PairCodeDisplay.tsx, DigitDial.tsx     (slice 1B)
    # QuestionCard.tsx, AnswerPill.tsx, TimerBar.tsx, TierBadge.tsx (slice 1C)
    # CountUpScore.tsx                       (slice 1D)
  lib/
    # api.ts, socket.ts, audio.ts            (slices 1B, 1C, 1E)
```

## Discipline

Per `AGENTS.md` § Discipline & Guardrails:
- No AI-generated graphics or sounds. CC0 assets only.
- No Segoe UI / Verdana / Tahoma / Arial Black. Anton (display) / Inter (body) / JetBrains Mono (numerals) — already loaded via Google Fonts in `index.html`.
- No generic CSS linear-gradients outside the locked palette.
- Motion uses Framer Motion eases — see `--ease-overshoot` in `index.css`.
