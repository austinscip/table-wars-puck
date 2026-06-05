# Deploying the Table Wars runtime

The runtime is an **authoritative single-process game server** per venue.
Run **one** instance per venue (keyed by `LOCATION_ID`); do not add gunicorn
workers (see "Why one worker" below).

## Option A — Docker (recommended)

```bash
docker build -t tablewars .
docker run -d --name tablewars \
  --env-file deploy/tablewars.env \
  -p 5001:5001 \
  tablewars
```

The image runs gunicorn with `--workers 1`, drops to a non-root user, and
ships a `HEALTHCHECK` against `/api/runtime/health`.

## Option B — systemd on a bare-metal venue box

```bash
sudo useradd -r -s /usr/sbin/nologin tablewars
sudo mkdir -p /opt/tablewars /etc/tablewars
# deploy the repo to /opt/tablewars and build the venv:
python -m venv /opt/tablewars/venv
/opt/tablewars/venv/bin/pip install -r /opt/tablewars/server/requirements.txt gunicorn
sudo cp deploy/tablewars.env.example /etc/tablewars/tablewars.env   # then edit
sudo cp deploy/tablewars-runtime.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now tablewars-runtime
```

## Configuration

All config is environment variables — see `deploy/tablewars.env.example`
and `docs/audit/manual-items-2026-06-05.md`. The security-relevant ones
(`PUCK_JWT_SECRET`, `SUPABASE_JWT_SECRET`, `PUCK_AUTOPROVISION=0`,
`CORS_ALLOWED_ORIGINS`, `SCRUB_SECRETS_AFTER_BOOT=1`) must be set before a
public launch.

## Health check

`GET /api/runtime/health` → `200` with JSON (status, registered games,
active match count, auth/store flags). DB-free, so a load balancer can use
it for liveness even when the database is briefly unreachable.

## Why one worker

The multi-game runtime holds authoritative match state (the live `Game`
objects) in process memory and runs the 10 Hz tick loop in that process.
A second worker would double-tick matches and 404 inputs for matches it
doesn't hold. The scaling axis is **per venue** — one box/container per
bar — which trivially handles a venue's handful of tables. With `REDIS_URL`
set, a restart/redeploy recovers active matches on boot. True multi-worker
needs per-match ownership claiming (the seams — distributed lock,
serialization, store — are built; see `server/runtime/CONTEXT.md`).

**Do NOT add gunicorn `--preload`** (ADR 0004). The runtime's tick
scheduler and the local-first TV SocketIO emit run on a background thread
that must spawn *after* the gevent worker forks and monkey-patches —
otherwise it spawns as a real thread that blocks the gevent hub. The
container builds its runtime lazily on first request (post-fork), so the
default (no preload) is correct; preloading would break that ordering.

## TLS

Terminate TLS at a reverse proxy (Caddy/nginx) or the venue edge. Puck
auth raises the floor, but tokens ride plain HTTP between puck and box —
TLS keeps them from being sniffed on bar Wi-Fi.
