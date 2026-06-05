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

from flask import Blueprint, jsonify, request

from runtime import (
    PairingManager,
    PairingError,
    MatchManager,
    TickScheduler,
    HeartbeatTracker,
    IdempotencyCache,
    configure_logging,
    init_sentry,
    registry as game_registry,
    event_from_dict,
)
from supabase_client import SupabaseWriter

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
    writer = SupabaseWriter.with_pool()
    heartbeat = HeartbeatTracker()
    idempotency = IdempotencyCache()
    manager = MatchManager(
        registry=game_registry,
        writer=writer,
        heartbeat=heartbeat,
        idempotency=idempotency,
    )
    scheduler = TickScheduler(match_manager=manager)
    manager.scheduler = scheduler
    pairing = PairingManager(match_manager=manager, puck_resolver=writer)
    scheduler.start()
    _container = {
        "writer": writer,
        "manager": manager,
        "scheduler": scheduler,
        "pairing": pairing,
        "heartbeat": heartbeat,
        "idempotency": idempotency,
    }
    return _container


def _location_id() -> str:
    return os.environ.get("LOCATION_ID") or DEV_FALLBACK_LOCATION_ID


def _bad(message: str, status: int = 400):
    return jsonify({"error": message}), status


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


@runtime_bp.route("/match/<match_id>/input", methods=["POST"])
def match_input(match_id: str):
    body = request.get_json(silent=True) or {}
    try:
        puck_index = int(body["puck_index"])
    except (KeyError, ValueError, TypeError):
        return _bad("puck_index required")
    event = event_from_dict(puck_index, body)
    # Idempotency key: prefer the standard header, fall back to an
    # event_id in the body so firmware that can't set headers still gets
    # dedupe. None means "no key" — processed every time (legacy pucks).
    event_id = request.headers.get("Idempotency-Key") or body.get("event_id")
    if event_id is not None:
        event_id = str(event_id)
    mm: MatchManager = _get_container()["manager"]
    try:
        update = mm.on_input(match_id, event, event_id=event_id)
    except KeyError:
        return _bad("Match not found", 404)
    match = mm.matches.get(match_id)
    status = match.status if match else "unknown"
    return jsonify({"state": update.state, "status": status})


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
