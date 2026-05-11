# North Star reference frames

The polish gate (see `docs/adr/0001-quality-bar-and-stack.md`, `AGENTS.md` §
Discipline & Guardrails) requires every TV game to be screenshotted next
to a real reference frame before it ships. The references live here.

## Speed Pyramid v1

**Reference target:** HQ Trivia question screen.

**What to source:**
- A high-resolution still frame of an HQ Trivia question card (or, if HQ
  imagery is hard to find at acceptable quality, a Jackbox "You Don't
  Know Jack" question screen). Save as `speed-pyramid-q-screen.png` in
  this directory.

**What we're matching:**
- Question text dominance: the question is the loudest element on screen,
  not the UI chrome.
- Answer pills have generous padding, strong type hierarchy
  (letter prefix + body text), and clear focus states.
- Cohesive palette — no incidental gradients, no decorative emoji as
  game art.
- Typography: bold display face for the question (Anton in our build),
  geometric sans for body (Inter), monospace for numerals
  (JetBrains Mono).
- Motion: every transition has an intentional ease. Nothing snap-cuts.

**What we're explicitly NOT matching:**
- HQ's full live-host video frame (we have no host).
- Mid-question countdown banners.
- Sponsor branding overlays.

## How to use during the polish gate

1. Build the Vite app: `cd server/static/games/speed-pyramid && npm run build`
2. Run Flask: `cd server && DATABASE_URL= python app.py`
3. Navigate to a live question screen.
4. Screenshot at the same aspect ratio + display size as the reference.
5. Place side-by-side. If our frame looks meaningfully cheaper, the gate
   fails and the slice does not ship.

## License note

Any reference frame committed here must be either CC0, fair-use static
reference for internal review (never reshipped), or a frame we've
produced ourselves. No paid stock without a license entry in
`docs/assets/LICENSES.md`.
