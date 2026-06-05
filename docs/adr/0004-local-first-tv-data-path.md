# ADR 0004 — Local-First TV Data Path

**Status:** Accepted
**Date:** 2026-06-05

## Context

Every gameplay actor at a venue is local — the Pucks, the Flask box (the
**State Authority**), and the **TV View** — yet visible state flows all the
way through the cloud and back:

```
puck → Flask (local) → Postgres (cloud) → Realtime (cloud) → TV (local)
```

Two harms fall out of that round-trip:

1. **Latency.** Real-time games (Puck Racer, Smash @ 10 Hz) inherit a full
   cloud round-trip on every visible change. Worse, the write itself is on
   the critical path: `MatchManager._tick_locked` calls
   `writer.update_match_snapshot(...)` — a Supabase Postgres write —
   **synchronously, while holding the per-match `RLock`**
   (`server/runtime/match.py:469`, under the lock taken at `:423`). A
   50–200 ms cloud write therefore blows the 100 ms tick budget *and*
   serialises `on_input` for that match behind the same lock. Moving the TV
   *read* local is necessary but not sufficient; the *write* must come off
   the tick's critical path too.
2. **Offline fragility.** The TV gameplay view subscribes **only** to
   Supabase Realtime (`TableWarsTV/src/lib/useMatchState.ts`). A venue
   internet drop blanks the TVs mid-match even though every local actor is
   fine — and bar Wi-Fi is flaky by nature.

What already exists and reshapes the fix:

- A **Flask-SocketIO** server is already running in `app.py`
  (`async_mode="threading"` in dev; gunicorn
  `GeventWebSocketWorker --workers 1` in prod), with room-based emit used by
  the legacy trivia/multiplayer/pair stacks. `eventlet`, `gevent-websocket`,
  and `gunicorn` are already in `requirements.txt`.
- The runtime already exposes the authoritative state locally over HTTP:
  `GET /api/runtime/match/<id>/state` returns `match.game.get_state()`
  straight from the in-memory `MatchManager`. It is just *polled*, and the
  TV gameplay view ignores it.
- The **TV View is a native app** (`TableWarsTV`, `react-native-tvos`),
  **not** a cloud-hosted web page (the glossary entry was stale; corrected
  in `CONTEXT.md`). A native app has no `https→http` mixed-content
  restriction, so it can hold a LAN socket to the Flask box *and* an
  `https` Supabase connection at the same time.

So this is not a rewrite — it is wiring the runtime into the socket server
already present and flipping the TV's data layer to prefer it.

## Decision

**The TV View renders gameplay local-first: the venue Flask box pushes
match state to the TV over a LAN Flask-SocketIO connection, and Supabase is
demoted from the render path to an asynchronous persistence/analytics sink
plus a cold-standby fallback.**

### Transport

Reuse the **existing Flask-SocketIO** server. The runtime emits
`state_update` into a per-match room `match:<id>`. The native TV swaps
`@supabase/realtime` for `socket.io-client` on the gameplay path. (Raw
WebSocket and SSE were rejected: SocketIO's rooms/reconnect/backoff are
already proven in this codebase and keep one socket paradigm in the app.)

### Authority and failover

- **Local-primary, cloud-fallback.** The TV connects to the box's LAN
  socket first (reusing the existing `API_BASE_URL` origin). **Local wins
  whenever the local socket is connected**; Supabase Realtime is consulted
  only while the local socket is down (box rebooting, TV on a different
  VLAN).
- A single monotonic **`snapshot_seq`** (extending the existing `cue_seq`
  pattern) is stamped **once at snapshot generation** and carried on *both*
  the local emit and the cloud `matches.snapshot` write. The TV renders a
  frame only if its `seq` exceeds the last rendered `seq`, so failover in
  either direction never paints an older frame over a newer one.

### Emit seam

A transport-agnostic **`state_sink`** dependency is injected into
`MatchManager` (same DI style as `scheduler` / `lock_provider` / `store`).
The manager invokes `state_sink(match_id, payload)` **after** the locked
section returns — never while holding the per-match `RLock`. The actual
`socketio.emit(room=f"match:{id}")` lives in app wiring, so the `runtime`
package stays free of any Flask-SocketIO import and tests inject a fake
sink. Emit fires on the **existing state-changed condition**
(`match.py:465–480`: state-changing ticks, state-changing inputs, lifecycle
transitions), so emit volume tracks meaningful change, not a flat 10 Hz ×
tables.

### Persistence decoupling (the latency fix)

The tick loop becomes pure **in-memory mutate + non-blocking enqueue**; all
Supabase I/O moves to an asynchronous drainer, in two lanes:

- **Snapshots** — coalesced, latest-wins per match, best-effort, ≤ ~1 s
  freshness target (so the cloud fallback isn't stale on failover).
  Intermediate frames may be dropped.
- **Scores + lifecycle** (`insert_score` round/final,
  `update_match_finished` / `update_match_abandoned`) — durable FIFO with
  retry, at-least-once, **re-flushed on recovery** via the existing
  `MatchStore`. A re-flushed `final` is idempotent against the
  `uniq_final_score_per_match_puck` index. Round scores are analytics-only
  (they don't reach `leaderboards` — the trigger filters for `final`), so
  they are loss-tolerant; finals and lifecycle are the truth the queue
  guarantees.

### Async model (unchanged)

No async rewrite. The runtime stays pure-`threading` (the `TickScheduler`
is a `threading.Thread`; `MatchManager` serialises with `threading.RLock`).
Under the prod `GeventWebSocketWorker`, gunicorn's `GeventWorker.patch()`
runs `monkey.patch_all()` **before** the app is imported, so the scheduler
thread becomes a cooperative greenlet and the loop's `self._stop.wait(...)`
yields the hub each tick. The scheduler is started lazily inside
`_get_container()` on first request — i.e. post-fork, post-patch — so the
emit greenlet is spawned correctly. Single-process emit needs **no Redis
message queue**.

### Deploy constraints (documented, not new)

- `--workers 1` stays required (already mandated by the runtime's
  authoritative in-process state + single ticker; the socket path inherits
  it — a second worker would not share the room membership or the ticker).
- **Never add gunicorn `--preload`** and never build the container at
  import time: that would spawn the scheduler thread *before* gevent
  monkey-patches, blocking the hub.

### Scope

This ADR covers the **gameplay match state** path. Lobby discovery is
unchanged: the TV still polls `/api/runtime/pair/lobby-state` to learn the
`match_id`, then joins `match:<id>`. Moving lobby state onto the socket is
a documented follow-up (the same room pattern). The LAN socket is
server→TV read-only and **unauthenticated within the venue LAN** —
consistent with the already-unauthenticated `/state` endpoint, and
acceptable because gameplay state is already publicly visible on the TV.
The cloud fallback keeps its existing TV-match-token RLS.

## Consequences

- The tick loop no longer blocks on cloud I/O; Racer/Smash render at true
  LAN latency, and a WAN drop no longer blanks the TVs. This also relieves
  the tick-fidelity concern (gap #5b): a slow cloud write can no longer
  stall the tick clock.
- The TV data layer (`useMatchState.ts`) becomes a **source-selector**
  behind one interface: socket-primary, Realtime-fallback, reconciled by
  `snapshot_seq`. Both sources must be exercised in tests.
- Cloud snapshot writes become **best-effort and coalesced** — the cloud
  `matches.snapshot` is no longer guaranteed to hold every intermediate
  frame, only a recent one. Anything that needs every frame must read the
  durable score/lifecycle lane, not the snapshot.
- `final` scores move from synchronous-guaranteed-before-return to
  **durable at-least-once** (re-flushed on recovery). No leaderboard truth
  is lost, but the guarantee shape changed; the recovery path must re-flush
  unacked finals on boot, and that must be covered by a real-flow
  regression test.
- A new transport-agnostic `state_sink` seam exists on `MatchManager`;
  games and the runtime core remain Flask-SocketIO-free.
- The `--workers 1` and **no `--preload`** constraints are now also
  load-bearing for the socket path; they belong in `deploy/README.md` and
  the systemd/Docker comments.
- This is consistent with the **State Authority** invariant
  (`CONTEXT.md`): the Flask box remains the single owner of canonical
  state; the TV is still a dumb client — it just reads from the authority
  directly over the LAN instead of through the cloud.
