"""
TABLE WARS - Pair Code Flow
Adds /api/pair/{request,dial,confirm} so a Puck and a TV View can bind to
the same Match.

Flow:
1. Puck POST /api/pair/request {puck_id}
   -> server generates a 6-digit decimal code, stores in pending dict
   -> response: {pair_code, expires_at}
2. TV opens /tv/speed-pyramid (Flask route serves the React SPA).
   The React app subscribes to a Socket.IO room keyed by pair_code.
3. Puck enters digit-dial mode. For each of 6 digits:
     POST /api/pair/dial {puck_id, digit_index, digit}
     -> server emits 'pair_dial_progress' to room=pair_code
4. After all 6 digits, puck POST /api/pair/confirm {puck_id, code}
   -> server validates code matches the pending code
   -> creates trivia session via create_trivia_session
   -> emits 'paired' to room=pair_code with {session_code}
   -> response: {session_code}
"""

import random
import string
import time
from typing import Optional

from flask import Blueprint, jsonify, request
from trivia_database import create_trivia_session, add_player_to_session
from database import execute_query, get_placeholder

pair_bp = Blueprint("pair", __name__, url_prefix="/api/pair")

# Set by init_pair_routes(). Module-level so route handlers can access it
# without a Flask current_app extension dance.
_socketio = None

# In-memory pending codes. Keyed by puck_id.
# {puck_id: {"code": "274591", "expires_at": 1234567890.0,
#            "progress": [None,None,None,None,None,None]}}
# Single-process Flask is fine for v1; move to Redis or session table
# before multi-worker production deploy (ADR follow-up).
_PENDING: dict[int, dict] = {}
_TTL_SECONDS = 600  # 10 minutes


def _now() -> float:
    return time.time()


def _new_code() -> str:
    """6-digit decimal pair code, leading zeros allowed."""
    return "".join(random.choices(string.digits, k=6))


def _purge_expired() -> None:
    now = _now()
    expired = [k for k, v in _PENDING.items() if v["expires_at"] < now]
    for k in expired:
        _PENDING.pop(k, None)


def _resolve_speed_pyramid_type_id() -> Optional[int]:
    """Look up game_type_id for 'speed_pyramid' in trivia_game_types."""
    ph = get_placeholder()
    row = execute_query(
        f"SELECT id FROM trivia_game_types WHERE name = {ph}",
        ("speed_pyramid",),
        fetch_one=True,
    )
    return row["id"] if row else None


@pair_bp.route("/request", methods=["POST"])
def request_code():
    """Puck calls this on entering pair mode to claim a pair code."""
    _purge_expired()
    data = request.get_json(silent=True) or {}
    puck_id = data.get("puck_id")
    if puck_id is None:
        return jsonify({"error": "puck_id required"}), 400

    existing = _PENDING.get(puck_id)
    if existing and existing["expires_at"] > _now():
        return jsonify(
            {
                "pair_code": existing["code"],
                "expires_at": existing["expires_at"],
                "reused": True,
            }
        )

    code = _new_code()
    _PENDING[puck_id] = {
        "code": code,
        "expires_at": _now() + _TTL_SECONDS,
        "progress": [None] * 6,
    }
    return jsonify(
        {
            "pair_code": code,
            "expires_at": _PENDING[puck_id]["expires_at"],
            "reused": False,
        }
    )


@pair_bp.route("/dial", methods=["POST"])
def dial_digit():
    """Puck reports one digit of dial progress. TV mirrors via WS."""
    _purge_expired()
    data = request.get_json(silent=True) or {}
    puck_id = data.get("puck_id")
    digit_index = data.get("digit_index")
    digit = data.get("digit")

    if puck_id is None or digit_index is None or digit is None:
        return jsonify({"error": "puck_id, digit_index, digit required"}), 400
    if not isinstance(digit_index, int) or not (0 <= digit_index < 6):
        return jsonify({"error": "digit_index must be 0..5"}), 400
    if not isinstance(digit, int) or not (0 <= digit <= 9):
        return jsonify({"error": "digit must be 0..9"}), 400

    pending = _PENDING.get(puck_id)
    if not pending:
        return jsonify({"error": "no pending pair code for this puck_id"}), 404

    pending["progress"][digit_index] = digit
    if _socketio is not None:
        _socketio.emit(
            "pair_dial_progress",
            {
                "puck_id": puck_id,
                "digit_index": digit_index,
                "digit": digit,
                "progress": pending["progress"],
            },
            room=pending["code"],
        )
    return jsonify({"accepted": True, "progress": pending["progress"]})


@pair_bp.route("/confirm", methods=["POST"])
def confirm_code():
    """Puck submits the full 6-digit code. If matches its pending code,
    server creates a trivia session and binds the puck."""
    _purge_expired()
    data = request.get_json(silent=True) or {}
    puck_id = data.get("puck_id")
    code = data.get("code")

    if puck_id is None or code is None:
        return jsonify({"error": "puck_id and code required"}), 400

    pending = _PENDING.get(puck_id)
    if not pending:
        return jsonify({"error": "no pending pair code for this puck_id"}), 404

    if str(code) != pending["code"]:
        return jsonify({"error": "code does not match"}), 401

    game_type_id = _resolve_speed_pyramid_type_id()
    if game_type_id is None:
        return jsonify({"error": "speed_pyramid game type not seeded"}), 500

    # For v1: bar_id=1, table_number=1 placeholder. Multi-bar lands later
    # when we add a bar-account UX.
    session_code = create_trivia_session(
        bar_id=1, table_number=1, game_type_id=game_type_id
    )

    ph = get_placeholder()
    session_row = execute_query(
        f"SELECT id FROM trivia_sessions WHERE session_code = {ph}",
        (session_code,),
        fetch_one=True,
    )
    if session_row:
        add_player_to_session(
            session_id=session_row["id"], puck_id=puck_id, player_name=None
        )

    if _socketio is not None:
        _socketio.emit(
            "paired",
            {"puck_id": puck_id, "session_code": session_code},
            room=pending["code"],
        )
    _PENDING.pop(puck_id, None)

    return jsonify({"session_code": session_code, "puck_id": puck_id})


def init_pair_routes(app, socketio):
    """Wire pair_bp into the Flask app and stash socketio for emits."""
    global _socketio
    _socketio = socketio
    app.register_blueprint(pair_bp)
