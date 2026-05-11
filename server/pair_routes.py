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
from trivia_database import (
    create_trivia_session,
    add_player_to_session,
    get_random_question,
)
from database import execute_query, get_placeholder

pair_bp = Blueprint("pair", __name__, url_prefix="/api/pair")
sp_bp = Blueprint("sp", __name__, url_prefix="/api/sp")

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


# ============================================================================
# Speed Pyramid v1 — match flow helpers
# ============================================================================
# These live alongside pair_bp because they're scoped to Speed Pyramid v1's
# sprint and we don't want to dilute trivia_routes.py with v1-specific
# round-counter logic. When more games adopt the same flow, lift these into
# a shared module.

# In-memory round counter per session_code.
# {session_code: {"round": int, "asked_ids": set[int]}}
_SP_STATE: dict[str, dict] = {}

SP_TOTAL_ROUNDS = 7


def _difficulty_for_round(r: int) -> str:
    """Q1-Q2 easy, Q3-Q5 medium, Q6-Q7 hard."""
    if r <= 2:
        return "easy"
    if r <= 5:
        return "medium"
    return "hard"


@sp_bp.route("/load-question/<session_code>", methods=["POST"])
def sp_load_question(session_code: str):
    """Load the next Speed Pyramid question for this session.

    Picks a random unused question at the difficulty matching the next
    round. Increments the round counter. Emits 'question_show' to room=
    session_code. Returns the question payload + round metadata.
    """
    state = _SP_STATE.setdefault(
        session_code, {"round": 0, "asked_ids": set()}
    )

    if state["round"] >= SP_TOTAL_ROUNDS:
        if _socketio is not None:
            _socketio.emit(
                "match_ended",
                {"session_code": session_code, "rounds": SP_TOTAL_ROUNDS},
                room=session_code,
            )
        return jsonify(
            {"error": "match_complete", "rounds": SP_TOTAL_ROUNDS}
        ), 409

    next_round = state["round"] + 1
    difficulty = _difficulty_for_round(next_round)
    exclude = list(state["asked_ids"]) or None
    q = get_random_question(difficulty=difficulty, exclude_ids=exclude)
    if not q:
        # Fall back to any difficulty if the bucket is dry.
        q = get_random_question(exclude_ids=exclude)
    if not q:
        return jsonify({"error": "no questions available"}), 404

    state["round"] = next_round
    state["asked_ids"].add(q["id"])

    # Resolve category for display.
    ph = get_placeholder()
    cat = execute_query(
        f"SELECT name, emoji FROM trivia_categories WHERE id = {ph}",
        (q["category_id"],),
        fetch_one=True,
    )

    payload_question = {
        "id": q["id"],
        "setup": q["setup_text"],
        "question": q["question_text"],
        "answers": {
            "A": q["answer_a"],
            "B": q["answer_b"],
            "C": q["answer_c"],
            "D": q["answer_d"],
        },
        "difficulty": q["difficulty"],
        "time_limit": q["time_limit"] or 10,
        "category": cat["name"] if cat else "",
        "category_emoji": cat["emoji"] if cat else "",
    }

    started_at = _now()
    if _socketio is not None:
        _socketio.emit(
            "question_show",
            {
                "session_code": session_code,
                "question": payload_question,
                "round": next_round,
                "total_rounds": SP_TOTAL_ROUNDS,
                "started_at": started_at,
            },
            room=session_code,
        )

    # Stash question_started_at in trivia_routes' tracker so its
    # /api/trivia/answer handler computes the authoritative response_time.
    try:
        import trivia_routes
        trivia_routes._question_start_times[session_code] = {
            "question_id": q["id"],
            "started_at": started_at,
        }
    except Exception:
        pass

    return jsonify(
        {
            "question": payload_question,
            "round": next_round,
            "total_rounds": SP_TOTAL_ROUNDS,
            "started_at": started_at,
        }
    )


@sp_bp.route("/match-state/<session_code>", methods=["GET"])
def sp_match_state(session_code: str):
    """Lightweight match progress lookup for the TV (mostly for debugging
    and for slice 1D's scoreboard query)."""
    state = _SP_STATE.get(session_code)
    if not state:
        return jsonify({"round": 0, "total_rounds": SP_TOTAL_ROUNDS})
    return jsonify(
        {
            "round": state["round"],
            "total_rounds": SP_TOTAL_ROUNDS,
            "questions_asked": len(state["asked_ids"]),
        }
    )


@sp_bp.route("/final-results/<session_code>", methods=["GET"])
def sp_final_results(session_code: str):
    """Final scoreboard data after match_ended. Sums points_earned across
    all answers in this session, grouped by puck_id. Returns per-puck
    totals + a derived 'tier' label based on average per-question."""
    ph = get_placeholder()
    session = execute_query(
        f"SELECT id FROM trivia_sessions WHERE session_code = {ph}",
        (session_code,),
        fetch_one=True,
    )
    if not session:
        return jsonify({"error": "session not found"}), 404

    rows = execute_query(
        f"""SELECT puck_id,
                   COALESCE(SUM(points_earned), 0) AS total,
                   COUNT(*) AS answered,
                   SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) AS correct
              FROM trivia_answers
             WHERE session_id = {ph}
             GROUP BY puck_id""",
        (session["id"],),
        fetch_all=True,
    ) or []

    def derive_tier(total: int, answered: int) -> str:
        if answered == 0:
            return "NONE"
        avg = total / answered
        if avg >= 700:
            return "LEGENDARY"
        if avg >= 400:
            return "EXPERT"
        if avg >= 150:
            return "AVERAGE"
        return "TIMEOUT"

    state = _SP_STATE.get(session_code, {})
    return jsonify(
        {
            "session_code": session_code,
            "round": state.get("round", SP_TOTAL_ROUNDS),
            "total_rounds": SP_TOTAL_ROUNDS,
            "players": [
                {
                    "puck_id": r["puck_id"],
                    "total": int(r["total"] or 0),
                    "answered": int(r["answered"] or 0),
                    "correct": int(r["correct"] or 0),
                    "tier": derive_tier(int(r["total"] or 0), int(r["answered"] or 0)),
                }
                for r in rows
            ],
        }
    )


@sp_bp.route("/reset/<session_code>", methods=["POST"])
def sp_reset(session_code: str):
    """Play Again — clear the round counter + asked-question set for this
    session so /load-question starts at Round 1 again. The trivia
    session itself stays the same, so we get a fresh leaderboard but the
    same puck<>TV binding."""
    _SP_STATE[session_code] = {"round": 0, "asked_ids": set()}
    try:
        import trivia_routes
        trivia_routes._question_start_times.pop(session_code, None)
    except Exception:
        pass
    if _socketio is not None:
        _socketio.emit(
            "match_reset",
            {"session_code": session_code},
            room=session_code,
        )
    return jsonify({"ok": True, "session_code": session_code})


@sp_bp.route("/current-question/<session_code>", methods=["GET"])
def sp_current_question(session_code: str):
    """Polled by the puck firmware to know which question is active +
    when it started + how much time is left. Cheap GET — no DB hit
    beyond what trivia_routes already tracks."""
    try:
        import trivia_routes
        sst = trivia_routes._question_start_times.get(session_code)
    except Exception:
        sst = None
    if not sst:
        return jsonify({"active": False})

    ph = get_placeholder()
    q = execute_query(
        f"SELECT id, time_limit FROM trivia_questions WHERE id = {ph}",
        (sst["question_id"],),
        fetch_one=True,
    )
    if not q:
        return jsonify({"active": False})

    time_limit = q["time_limit"] or 10
    elapsed = _now() - sst["started_at"]
    remaining = max(0.0, time_limit - elapsed)
    return jsonify(
        {
            "active": True,
            "question_id": q["id"],
            "time_limit": time_limit,
            "started_at": sst["started_at"],
            "remaining_sec": remaining,
        }
    )


def init_pair_routes(app, socketio):
    """Wire pair_bp + sp_bp into the Flask app and stash socketio for emits."""
    global _socketio
    _socketio = socketio
    app.register_blueprint(pair_bp)
    app.register_blueprint(sp_bp)
