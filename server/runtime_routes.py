"""
Flask routes that expose the multi-game runtime over HTTP.

Mounted at /api/runtime/. Coexists with the existing /api/pair/ Speed
Pyramid flow during the cut-over — old firmware keeps working until F1
ships on the new runtime.

LOCATION_ID env var pins this server instance to one Supabase location.
For pilot scale (one server, one bar) this is fine. Multi-tenant routing
will read tenant from the API key or subdomain later.

Endpoints
---------

POST /api/runtime/pair/request   {puck_index, game_slug?, table_number?}
                                 -> {code, role, color, players, ...}
POST /api/runtime/pair/dial      {puck_index, digit_index, digit}
                                 -> {puck_index, progress}
POST /api/runtime/pair/confirm   {puck_index, code}
                                 -> {role, color, players, ...}
POST /api/runtime/pair/start     {puck_index}
                                 -> {match_id, status}
POST /api/runtime/pair/cancel    {puck_index}
                                 -> {ok: true}
GET  /api/runtime/pair/lobby-state
                                 -> {active, code, players, ...}
POST /api/runtime/match/<id>/input
                                 {puck_index, tilt_x?, tilt_y?, shake?,
                                  button_tap?, button_hold?, gyro_z?}
                                 -> {state, status}
GET  /api/runtime/match/<id>/state
                                 -> {state, status, players}
GET  /api/runtime/registry
                                 -> {games: [{slug, display_name, ...}]}
"""

from __future__ import annotations

import os
from typing import Optional

from flask import Blueprint, jsonify, render_template, request

from runtime import (
    PairingManager,
    PairingError,
    MatchManager,
    PersistenceQueue,
    PlayerIdentity,
    TriviaContentCache,
    TickScheduler,
    HeartbeatTracker,
    IdempotencyCache,
    MatchTokenAuthority,
    TvMatchTokenAuthority,
    AuthError,
    RateLimiter,
    configure_logging,
    get_logger,
    init_sentry,
    harden_secrets,
    registry as game_registry,
    event_from_dict,
)
from supabase_client import SupabaseWriter

_log = get_logger("routes")

runtime_bp = Blueprint("runtime", __name__, url_prefix="/api/runtime")

# Default game slug when the puck doesn't specify one. Speed Pyramid is
# the pilot flagship.
DEFAULT_GAME_SLUG = "speed_pyramid"
# Default table_number for the pilot's single-table setup. The TV bind
# flow will override later.
DEFAULT_TABLE_NUMBER = 1
# Seeded Friendly Bar id from the initial schema migration. Used as a
# dev fallback so the route works before LOCATION_ID is set.
DEV_FALLBACK_LOCATION_ID = "10c079c1-a034-442e-9075-dba4ac9bcf15"


# === Lazy singleton container ===
# Built on first request so app startup doesn't require DATABASE_URL.
# Multiple workers each get their own container; for pilot scale that's
# acceptable because gunicorn runs a single worker by default in dev.
# Production split-across-workers is the trigger to push state into
# Redis (see runtime/CONTEXT.md).

_container: Optional[dict] = None

# Set by init_runtime_routes() at app startup. The local-first TV push
# (ADR 0004) emits each frame to a LAN SocketIO room; keeping the reference
# at module scope (read late, at emit time) lets the runtime package stay
# Flask-SocketIO-free — the import lives only inside init_runtime_routes.
_socketio = None


def _state_sink(envelope: dict) -> None:
    """MatchManager.state_sink: push one frame to the TVs subscribed to this
    match's LAN SocketIO room. No-op until a socketio is wired (tests, or
    before startup). Read _socketio late so wiring order doesn't matter."""
    sio = _socketio
    if sio is None:
        return
    match_id = envelope.get("match_id")
    sio.emit("state_update", envelope, room=f"match:{match_id}")


def init_runtime_routes(app, socketio) -> None:
    """Register the runtime blueprint and wire the local-first TV path
    (ADR 0004): TVs join/leave a per-match SocketIO room and the
    MatchManager's state_sink emits each frame into it. Called once at app
    startup. The flask_socketio import is local so importing this module
    (e.g. in the runtime pytest job, which has no flask_socketio) never
    needs it."""
    global _socketio
    _socketio = socketio
    app.register_blueprint(runtime_bp)

    @app.route("/play/<match_id>")
    def play_page(match_id):  # noqa: ANN001,ANN202
        """The patron's phone bind page (ADR 0005). Reached by scanning the
        TV's QR. Self-contained: it reads the match's seats and binds via
        /api/runtime/match/<id>/bind, persisting the player token on the
        device for return visits."""
        return render_template("play.html", match_id=match_id)

    from flask_socketio import join_room, leave_room, emit

    @socketio.on("join_match")
    def _on_join_match(data):
        """TV subscribes to a match's room to receive state_update frames
        over the LAN — the local-first render path."""
        match_id = (data or {}).get("match_id")
        if isinstance(match_id, str) and match_id:
            join_room(f"match:{match_id}")
            emit("joined_match", {"match_id": match_id})

    @socketio.on("leave_match")
    def _on_leave_match(data):
        match_id = (data or {}).get("match_id")
        if isinstance(match_id, str) and match_id:
            leave_room(f"match:{match_id}")


def _get_container() -> dict:
    global _container
    if _container is not None:
        return _container
    # Import the games package so every game module registers itself
    # on the runtime before the first request lands. Import is here
    # rather than at module top-level so the routes blueprint can be
    # registered even when DATABASE_URL is unset (e.g. test imports).
    import games  # noqa: F401

    # Stand up logging + (optional) Sentry before any match runs so a
    # tick-loop exception is captured rather than lost to stdout.
    configure_logging()
    init_sentry()

    # Pooled writer in the live runtime so a score write doesn't pay a
    # fresh TCP+TLS handshake each time. Falls back to per-call connect
    # when psycopg_pool isn't installed.
    base_writer = SupabaseWriter.with_pool()
    # Decouple cloud I/O from the tick loop (ADR 0004): the PersistenceQueue
    # implements the same writer protocol but routes high-frequency
    # snapshots + round scores to a best-effort async drain, keeping finals,
    # lifecycle, and create synchronous. The MatchManager calls it exactly
    # like the raw writer.
    writer = PersistenceQueue(base_writer)
    writer.start()
    heartbeat = HeartbeatTracker()

    # Trivia content: sync the active question bank from Supabase into a
    # local cache (offline-resilient, ADR 0008) and wire it as Speed
    # Pyramid's question source. Best-effort — if the content table isn't
    # present or the cloud is unreachable, the game falls back to the legacy
    # local SQLite bank / built-in defaults.
    trivia_cache = None
    try:
        import games.speed_pyramid as _sp

        trivia_cache = TriviaContentCache(base_writer)
        trivia_cache.refresh()
        _sp.set_question_source(trivia_cache.load)
        _log.info(
            "trivia content cache wired (%d questions, version %s)",
            trivia_cache.size,
            trivia_cache.version or "—",
        )
    except Exception:  # noqa: BLE001
        _log.exception("trivia content cache init failed; using local fallback")

    # Durable match store + shared idempotency when REDIS_URL is set. The
    # store lets a restarted worker recover active matches (and is the
    # foundation for multi-worker state sharing). Falls back to in-process
    # idempotency + no store when Redis isn't configured/available.
    store = None
    idempotency: IdempotencyCache = IdempotencyCache()
    redis_url = os.environ.get("REDIS_URL")
    if redis_url:
        try:
            import redis as _redis
            from runtime import RedisMatchStore, RedisIdempotencyCache

            _client = _redis.Redis.from_url(redis_url)
            _client.ping()
            store = RedisMatchStore(_client)
            idempotency = RedisIdempotencyCache(_client)
            _log.info("Redis store + idempotency enabled (REDIS_URL set)")
        except Exception:  # noqa: BLE001
            _log.exception(
                "REDIS_URL set but Redis init failed; using in-process state"
            )

    # Puck auth: enforced only when PUCK_JWT_SECRET is configured. In prod
    # set it to require signed tokens on every input; unset in dev for the
    # open flow. We log loudly which mode we're in so a misconfigured prod
    # box doesn't silently run unauthenticated.
    secret = os.environ.get("PUCK_JWT_SECRET")
    if secret:
        token_authority = MatchTokenAuthority(secret)
        _log.info("puck auth ENABLED (PUCK_JWT_SECRET set)")
    else:
        token_authority = None
        _log.warning(
            "puck auth DISABLED — set PUCK_JWT_SECRET to require signed "
            "puck tokens on match input"
        )

    # TV match-token authority, signed with the Supabase JWT secret so
    # Realtime accepts it. Lets the TV read exactly one match under the
    # anon RLS policies. Enabled when SUPABASE_JWT_SECRET is set.
    supabase_secret = os.environ.get("SUPABASE_JWT_SECRET")
    tv_token_authority = (
        TvMatchTokenAuthority(supabase_secret) if supabase_secret else None
    )

    manager = MatchManager(
        registry=game_registry,
        writer=writer,
        heartbeat=heartbeat,
        idempotency=idempotency,
        store=store,
        # Local-first TV push (ADR 0004): emit each frame to the match's LAN
        # SocketIO room. No-op until init_runtime_routes wires a socketio.
        state_sink=_state_sink,
    )
    scheduler = TickScheduler(match_manager=manager)
    manager.scheduler = scheduler
    pairing = PairingManager(
        match_manager=manager,
        # Pairing needs SupabaseWriter methods outside the writer protocol
        # (puck resolution, lobby writes), so it gets the raw writer — the
        # PersistenceQueue only fronts the match-lifecycle write path.
        puck_resolver=base_writer,
        token_authority=token_authority,
        lobby_writer=base_writer,
    )
    scheduler.start()
    # Restart recovery: rebuild any active matches the store still holds.
    # (Single-worker safe; multi-worker ownership claiming is the next step
    # — see CONTEXT.md.)
    if store is not None:
        try:
            recovered = manager.recover()
            if recovered:
                _log.info("recovered %d active match(es) on boot", len(recovered))
        except Exception:  # noqa: BLE001
            _log.exception("match recovery failed on boot")
    _container = {
        "writer": base_writer,
        "persistence": writer,
        "manager": manager,
        "scheduler": scheduler,
        "pairing": pairing,
        "heartbeat": heartbeat,
        "idempotency": idempotency,
        "token_authority": token_authority,
        "tv_token_authority": tv_token_authority,
        "rate_limiter": RateLimiter(),
        "trivia_cache": trivia_cache,
        # Player identity (ADR 0005). Phone recovery is enabled only when
        # PLAYER_PHONE_PEPPER is set (otherwise phone hashing returns None).
        "player_identity": PlayerIdentity(
            os.environ.get("PLAYER_PHONE_PEPPER")
        ),
    }
    # Every secret has now been read into a long-lived object (the pool's
    # conninfo, the authority's key, database.py's module constant). If
    # SCRUB_SECRETS_AFTER_BOOT is set, drop them from os.environ so a
    # later in-process compromise can't read them back.
    harden_secrets()
    return _container


def _location_id() -> str:
    return os.environ.get("LOCATION_ID") or DEV_FALLBACK_LOCATION_ID


def _bad(message: str, status: int = 400):
    return jsonify({"error": message}), status


# === Health ===


@runtime_bp.route("/health", methods=["GET"])
def health():
    """Liveness/readiness for load balancers + deploy checks. Stays cheap
    and DB-free: it never forces the (DB-touching) container to build, so a
    health probe works even before the first real request or if the DB is
    briefly unreachable."""
    import games  # noqa: F401 — ensure the registry is populated

    info: dict = {
        "status": "ok",
        "games": game_registry.list_slugs(),
        "runtime_initialized": _container is not None,
    }
    if _container is not None:
        mm: MatchManager = _container["manager"]
        info["active_matches"] = sum(
            1 for m in mm.matches.values() if m.status == "active"
        )
        info["puck_auth"] = _container.get("token_authority") is not None
        info["durable_store"] = mm.store is not None
    return jsonify(info), 200


# === Pair endpoints ===


@runtime_bp.route("/pair/request", methods=["POST"])
def pair_request():
    body = request.get_json(silent=True) or {}
    try:
        puck_index = int(body["puck_index"])
    except (KeyError, ValueError, TypeError):
        return _bad("puck_index is required (int 1-8)")
    game_slug = body.get("game_slug", DEFAULT_GAME_SLUG)
    table_number = int(body.get("table_number", DEFAULT_TABLE_NUMBER))

    pm: PairingManager = _get_container()["pairing"]
    try:
        result = pm.request_code(
            puck_index=puck_index,
            game_slug=game_slug,
            location_id=_location_id(),
            table_number=table_number,
        )
    except PairingError as e:
        return _bad(str(e), 409)
    return jsonify(result)


@runtime_bp.route("/pair/dial", methods=["POST"])
def pair_dial():
    body = request.get_json(silent=True) or {}
    try:
        puck_index = int(body["puck_index"])
        digit_index = int(body["digit_index"])
        digit = int(body["digit"])
    except (KeyError, ValueError, TypeError):
        return _bad("puck_index, digit_index, digit required")
    pm: PairingManager = _get_container()["pairing"]
    try:
        result = pm.dial_progress(puck_index, digit_index, digit)
    except PairingError as e:
        return _bad(str(e), 409)
    return jsonify(result)


@runtime_bp.route("/pair/confirm", methods=["POST"])
def pair_confirm():
    body = request.get_json(silent=True) or {}
    try:
        puck_index = int(body["puck_index"])
        code = str(body["code"])
    except (KeyError, ValueError, TypeError):
        return _bad("puck_index and code required")
    pm: PairingManager = _get_container()["pairing"]
    try:
        result = pm.confirm_code(puck_index, code)
    except PairingError as e:
        return _bad(str(e), 409)
    return jsonify(result)


@runtime_bp.route("/pair/start", methods=["POST"])
def pair_start():
    body = request.get_json(silent=True) or {}
    try:
        puck_index = int(body["puck_index"])
    except (KeyError, ValueError, TypeError):
        return _bad("puck_index required")
    pm: PairingManager = _get_container()["pairing"]
    try:
        match = pm.start_match(puck_index)
    except PairingError as e:
        return _bad(str(e), 409)
    except KeyError as e:
        # No game registered with the lobby's slug.
        return _bad(str(e), 404)
    return jsonify({"match_id": match.id, "status": match.status})


@runtime_bp.route("/pair/cancel", methods=["POST"])
def pair_cancel():
    body = request.get_json(silent=True) or {}
    try:
        puck_index = int(body["puck_index"])
    except (KeyError, ValueError, TypeError):
        return _bad("puck_index required")
    pm: PairingManager = _get_container()["pairing"]
    try:
        pm.cancel(puck_index)
    except PairingError as e:
        return _bad(str(e), 409)
    return jsonify({"ok": True})


@runtime_bp.route("/pair/lobby-state", methods=["GET"])
def pair_lobby_state():
    pm: PairingManager = _get_container()["pairing"]
    # ?table_number=N scopes to one table; omitted returns the sole lobby
    # (single-table pilot) or a list when several tables are active.
    table_number = request.args.get("table_number", type=int)
    location_id = _location_id() if table_number is not None else None
    return jsonify(
        pm.lobby_snapshot(location_id=location_id, table_number=table_number)
    )


# === Match endpoints ===


def _bearer_token() -> Optional[str]:
    header = request.headers.get("Authorization", "")
    if header.startswith("Bearer "):
        return header[len("Bearer ") :].strip()
    return None


@runtime_bp.route("/match/<match_id>/input", methods=["POST"])
def match_input(match_id: str):
    body = request.get_json(silent=True) or {}
    try:
        puck_index = int(body["puck_index"])
    except (KeyError, ValueError, TypeError):
        return _bad("puck_index required")

    container = _get_container()
    mm: MatchManager = container["manager"]
    match = mm.matches.get(match_id)
    if match is None:
        return _bad("Match not found", 404)

    # Auth: when an authority is configured, require a token scoped to
    # this match's location and the submitting puck_index. A token issued
    # for puck 3 can't drive puck 5; a token for another venue can't drive
    # this one.
    authority = container.get("token_authority")
    if authority is not None:
        token = _bearer_token() or body.get("token")
        try:
            authority.verify(
                token or "",
                location_id=match.location_id,
                puck_index=puck_index,
            )
        except AuthError as e:
            return _bad(f"unauthorized: {e}", 401)

    # Rate limit per (match, puck) AFTER auth so an unauthenticated flood
    # can't drain a real puck's bucket. A misbehaving but paired puck that
    # exceeds the cap gets 429s until its bucket refills.
    limiter: Optional[RateLimiter] = container.get("rate_limiter")
    if limiter is not None and not limiter.allow(f"{match_id}:{puck_index}"):
        return _bad("rate limited", 429)

    # event_from_dict is defensive (coerces/clamps, never raises), but guard
    # the route anyway so a future stricter parser returns 400, not 500.
    try:
        event = event_from_dict(puck_index, body)
    except (ValueError, TypeError):
        return _bad("invalid input payload", 400)
    # Idempotency key: prefer the standard header, fall back to an
    # event_id in the body so firmware that can't set headers still gets
    # dedupe. None means "no key" — processed every time (legacy pucks).
    event_id = request.headers.get("Idempotency-Key") or body.get("event_id")
    if event_id is not None:
        event_id = str(event_id)
    try:
        update = mm.on_input(match_id, event, event_id=event_id)
    except KeyError:
        return _bad("Match not found", 404)
    return jsonify({"state": update.state, "status": match.status})


@runtime_bp.route("/match/<match_id>/tv-token", methods=["POST"])
def match_tv_token(match_id: str):
    """Mint the Supabase Realtime token the TV uses to read this match
    under the anon RLS policies. The location is the SERVER's
    (LOCATION_ID), never the caller's, and we verify the match belongs to
    it — so this endpoint can only ever produce a token for a match at
    this venue, even though it's unauthenticated within the venue LAN."""
    container = _get_container()
    authority: Optional[TvMatchTokenAuthority] = container.get(
        "tv_token_authority"
    )
    if authority is None:
        return _bad("TV auth not configured (set SUPABASE_JWT_SECRET)", 503)
    mm: MatchManager = container["manager"]
    match = mm.matches.get(match_id)
    if match is None:
        return _bad("Match not found", 404)
    if match.location_id != _location_id():
        # A match at another venue — refuse, don't mint a cross-venue token.
        return _bad("Match not at this location", 403)
    token = authority.issue(match_id=match_id, location_id=match.location_id)
    return jsonify({"token": token, "match_id": match_id})


@runtime_bp.route("/match/<match_id>/bind", methods=["POST"])
def match_bind(match_id: str):
    """Bind a Player to a Match Participant — the binding moment (ADR 0005).

    The patron's phone (having scanned the TV's QR) POSTs their existing
    player token + the puck_index (seat) they're in. With no token we mint a
    new one and return it for the device to persist. Bindable only while the
    match is live (lobby/active); once it's over the final score has already
    written, so a late bind wouldn't count toward the leaderboard.

    The token is the patron's capability — possession identifies the Player —
    so within the venue LAN this needs no other auth (consistent with the
    other runtime endpoints). We never echo a token the caller already sent;
    only a freshly-minted one is returned."""
    body = request.get_json(silent=True) or {}
    try:
        puck_index = int(body["puck_index"])
    except (KeyError, ValueError, TypeError):
        return _bad("puck_index required")

    container = _get_container()
    mm: MatchManager = container["manager"]
    match = mm.matches.get(match_id)
    if match is None:
        return _bad("Match not found", 404)
    if match.location_id != _location_id():
        return _bad("Match not at this location", 403)
    if match.status not in ("lobby", "active"):
        return _bad("Match already over; cannot bind a player", 409)
    mp_id = match.match_puck_ids.get(puck_index)
    if mp_id is None:
        return _bad("puck_index not in this match", 404)

    writer = container["writer"]
    ident: PlayerIdentity = container["player_identity"]

    provided = (body.get("token") or "").strip() or None
    display_name = (body.get("display_name") or "").strip() or None
    token = provided or ident.new_token()
    minted = provided is None

    try:
        player_id, created = writer.resolve_or_create_player(
            ident.hash_token(token), display_name=display_name
        )
        writer.bind_player_to_match_puck(
            mp_id, player_id, display_name=display_name
        )
        phone = (body.get("phone") or "").strip()
        phone_linked = False
        if phone and ident.phone_recovery_enabled:
            phone_hash = ident.hash_phone(phone)
            if phone_hash:
                writer.attach_phone_hash(player_id, phone_hash)
                phone_linked = True
    except Exception:  # noqa: BLE001
        _log.exception(
            "player bind failed (match=%s puck=%s)", match_id, puck_index
        )
        return _bad("bind failed", 503)

    return jsonify(
        {
            "player_id": player_id,
            "puck_index": puck_index,
            "created": created,
            "phone_linked": phone_linked,
            # Only return a token we minted — never echo the caller's own.
            "token": token if minted else None,
        }
    )


@runtime_bp.route("/match/<match_id>/qr", methods=["GET"])
def match_qr(match_id: str):
    """QR (PNG data URI) the TV displays so a patron's phone can open the
    bind page for this match (ADR 0005). It encodes the /play/<id> URL on
    THIS host — the box the TV reached, which a phone on the same venue LAN
    can also reach — so the TV renders it as a plain image, no native QR
    dependency. `play_url` is returned too as a text fallback (and so the TV
    can show it if QR rendering isn't available)."""
    mm: MatchManager = _get_container()["manager"]
    if mm.matches.get(match_id) is None:
        return _bad("Match not found", 404)
    play_url = f"{request.host_url}play/{match_id}"
    qr_code = _qr_data_uri(play_url)
    return jsonify({"play_url": play_url, "qr_code": qr_code})


def _qr_data_uri(url: str) -> Optional[str]:
    """A base64 PNG data URI for `url`, or None when the QR lib isn't
    available (the caller falls back to showing the URL as text)."""
    try:
        import base64
        from io import BytesIO

        import qrcode

        qr = qrcode.QRCode(version=1, box_size=10, border=2)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = BytesIO()
        img.save(buf, format="PNG")
        return "data:image/png;base64," + base64.b64encode(
            buf.getvalue()
        ).decode("ascii")
    except Exception:  # noqa: BLE001
        _log.exception("QR generation failed for %s", url)
        return None


@runtime_bp.route("/match/<match_id>/state", methods=["GET"])
def match_state(match_id: str):
    mm: MatchManager = _get_container()["manager"]
    match = mm.matches.get(match_id)
    if match is None:
        return _bad("Match not found", 404)
    return jsonify(
        {
            "state": match.game.get_state(),
            "status": match.status,
            "players": [
                {
                    "puck_index": p.puck_index,
                    "name": p.name,
                    "color": p.color,
                }
                for p in match.players
            ],
        }
    )


# === Registry inspection ===


@runtime_bp.route("/registry", methods=["GET"])
def registry_index():
    games = []
    for slug in game_registry.list_slugs():
        cls = game_registry.get(slug)
        games.append(
            {
                "slug": cls.slug,
                "display_name": cls.display_name,
                "min_players": cls.min_players,
                "max_players": cls.max_players,
                "input_schema": list(cls.input_schema),
            }
        )
    return jsonify({"games": games})
