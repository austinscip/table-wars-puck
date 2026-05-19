# Virtual Puck mirrors firmware polling, not TV sockets

When building the sandbox Virtual Puck (a browser-rendered control panel that POSTs the same `/api/*` endpoints a Puck's firmware does), we had to choose between subscribing to the same socket.io events the TV View consumes (`question_show`, `reveal`, `match_started`, etc.) or polling the same HTTP endpoints the firmware polls (`/api/sp/current-question` 500ms, `/api/sp/match-state` 500ms, `/api/pair/lobby-state` 1s). The sockets path would feel snappier — instant UI updates with no polling overhead. We picked polling anyway, because the entire reason the Virtual Puck exists is to catch firmware-class bugs without flashing hardware, and the firmware does not subscribe to sockets. A Virtual Puck that listens for `question_show` is just a second TV; a polling Virtual Puck exercises the same race conditions and stale-cache scenarios real pucks hit.

## Consequences

- Up to ~500ms UI lag between server state change and the Virtual Puck panel reflecting it. Acceptable for sandbox testing; matches firmware reality.
- The Hub itself (the wrapper page at `/dev/hub`) MAY subscribe to sockets for its own read-only meta display (current pair code, round number) — it is dev tooling, not a Puck.
- Polling-specific firmware bugs (e.g., handling of intermittent 5xx responses, race between `current-question` and `match-state`) now show up in sandbox e2e runs instead of escaping to flashed hardware at the bar.
