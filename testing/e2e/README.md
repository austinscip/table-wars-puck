# End-to-end testing — Speed Pyramid

The audit follow-ups flagged that "nothing was run as a live system (Flask +
web TV + a simulated puck through a full match)". This directory is the e2e
scaffold that closes most of that gap and documents the remaining layer.

## What exists now (runs in CI)

**Server-side full-match e2e** — `server/tests/test_e2e_full_match.py`
(built on `server/tests/sp_harness.py`).

It drives the **real Flask `pair`/`sp` blueprints** against a throwaway SQLite
DB through a **complete 7-round match**:

- pairing two pucks (host + joiner) and the host-start,
- the category-pick phases (rounds 1/3/5/7) and minigame phases (rounds 2/4/6),
  resolved exactly as a puck would,
- per-round answers (with the per-puck capability **token**) and reveals,
- match completion (`match_complete` + `match_ended`) and lobby clear,
- final results / standings / winner,

asserting the **exact socket-event stream the TV would receive**
(`match_started`, `category_offer`, `minigame_start`, `question_show`,
`answer_locked`, `reveal`, `match_ended`) plus an impersonation attempt being
rejected mid-match. This exercises how every unit-tested piece fits **together**.

The socket *transport* itself (flask-socketio room delivery) is covered for the
shared mechanism by `server/tests/test_socketio_emit.py` (a real `SocketIO`
server + `test_client` + room-membership assertions); the SP path emits to the
same `join_session_room` rooms (`server/app.py`).

Run it:

```bash
cd server && . venv/bin/activate && python -m pytest tests/test_e2e_full_match.py -v
```

## What's covered vs the unit tests

The unit suites verify pieces in isolation (token auth, the phase state machine,
reveal scoring, crash-recovery, reconnect). This e2e verifies their **integration
across a whole match** — a regression in how the pick→minigame→question→reveal
transitions chain, or in cumulative scoring across 7 rounds, surfaces here even
when each unit still passes.

## Browser-rendered layer (now built) — `test_browser_tv.py`

A real headless **Chromium (Playwright)** renders the actual built TV bundle
served by the real Flask app, and drives it over the wire:

- `test_tv_title_renders` — the React SPA actually paints ("SPEED PYRAMID" +
  the pair prompt) when Flask serves `dist/`. Proves the build + serve + render
  path, not just the data.
- `test_tv_navigates_to_pair_when_a_puck_requests` — the TV's title screen joins
  the lobby room on its socket; a puck `POST /api/pair/request` makes the server
  emit `pair_started`, and **the browser navigates itself to the pair screen** —
  a genuine Flask + Socket.IO + browser round-trip.

`conftest.py` boots `python app.py` on a free port (`SP_MDNS_DISABLE` +
`SP_PERSIST_DISABLE`), waits for readiness, and tears it down.

Run it (kept out of the main suite — it needs a browser):

```bash
cd server && . venv/bin/activate
python -m playwright install chromium      # one time
python -m pytest ../testing/e2e -q
```

CI runs it as the **`browser-e2e`** job (builds the bundle + installs Playwright
chromium). The server-side full-match e2e covers the deep game logic; this covers
that the TV actually renders and reacts. The remaining stretch (driving a *full
match* in the browser end-to-end and asserting the scoreboard DOM) layers
directly on this — same fixture, more steps.
