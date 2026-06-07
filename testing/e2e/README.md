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

## Deferred: the browser-rendered layer (owner / next step)

The one thing this scaffold does NOT do is render the actual **web TV SPA in a
browser**. The server-side e2e asserts the *events* the TV consumes, but not that
the React app paints them correctly (that's covered piecemeal by the web TV's
vitest unit tests + the ErrorBoundary). A full browser e2e would:

1. `npm --prefix server/static/games/speed-pyramid run build` to produce `dist/`,
2. boot the real Flask app (`SP_PERSIST_DISABLE=1`, a temp DB, a free port),
3. open `/tv/speed-pyramid` in a headless browser (Playwright),
4. run a scripted puck (HTTP via the `pair`/`sp` endpoints, carrying its token)
   through a full match,
5. assert the TV DOM transitions (title → lobby → question → reveal →
   scoreboard) and that the operator-token control-plane calls succeed.

This needs a browser in CI (Playwright) + the built bundle, so it's left as the
next infra step. The server-side e2e above is the foundation it would layer on:
the same match-driving flow, with a browser observing the rendered result.
