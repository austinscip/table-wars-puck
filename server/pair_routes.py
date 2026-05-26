"""
TABLE WARS - Pair Code Flow + Speed Pyramid lobby

v2: shared-code multiplayer lobby. Only one active lobby per server at
a time. First puck to enter pair mode becomes host; subsequent pucks
join by dialing the same code. Host taps to start when ready, which
creates the underlying trivia session and lets the match begin.

Single-player Speed Pyramid is the degenerate case: 1 player + host-
tap-start. Same flow, no special-casing.

Endpoints:
- POST /api/pair/request {puck_id}         -> {pair_code, role, color, players}
- POST /api/pair/dial    {puck_id, ...}    -> updates host's live mirror only
- POST /api/pair/preview {puck_id, ...}    -> emits pair_dial_preview only for host
- POST /api/pair/confirm {puck_id, code}   -> {role, color, players} (joins lobby)
- POST /api/pair/start   {puck_id}         -> {session_code} (host only)
- GET  /api/pair/lobby-state               -> current lobby snapshot

Speed Pyramid endpoints (unchanged from v1.1):
- POST /api/sp/load-question/<code>
- GET  /api/sp/current-question/<code>
- GET  /api/sp/match-state/<code>
- GET  /api/sp/final-results/<code>
- POST /api/sp/reset/<code>
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

_socketio = None

# Local question tracker (Speed Pyramid v1.1) — keyed by session_code.
_QUESTION_TRACKER: dict[str, dict] = {}

# ============================================================================
# Lobby model (v2)
# ============================================================================
# A single active lobby on the server. None when no lobby pending.
# {
#   "code": "274591",            # shared 6-digit pair code
#   "host_puck_id": 1,
#   "started": False,
#   "session_code": None,        # set after host calls /start
#   "players": {                 # puck_id -> {color_hex, color_name, joined_at}
#     1: {"color": "#3B82F6", "color_name": "blue",  "joined_at": 1.0},
#   },
#   "dials_in_progress": {       # puck_id -> [None|digit, ...]   (host only)
#     1: [None] * 6,
#   },
#   "expires_at": 1234567.0,
# }
_LOBBY: Optional[dict] = None
_TTL_SECONDS = 600

# Puck color palette (matches design tokens locked in src/index.css).
# Index by puck_id, fall back to white for unknown IDs.
PUCK_COLORS: dict[int, tuple[str, str]] = {
    1: ("#3B82F6", "blue"),
    2: ("#EC4899", "pink"),
    3: ("#FBBF24", "gold"),
    4: ("#10B981", "green"),
    5: ("#A855F7", "purple"),
    6: ("#F97316", "orange"),
    7: ("#06B6D4", "cyan"),
    8: ("#EF4444", "red"),
}


def _color_for(puck_id: int) -> tuple[str, str]:
    return PUCK_COLORS.get(int(puck_id), ("#F8FAFC", "white"))


def _now() -> float:
    return time.time()


def _new_code() -> str:
    return "".join(random.choices(string.digits, k=6))


def _purge_lobby_if_expired() -> None:
    global _LOBBY
    if _LOBBY is None:
        return
    if _LOBBY["expires_at"] < _now() and not _LOBBY["started"]:
        _LOBBY = None


def _clear_lobby() -> None:
    global _LOBBY
    _LOBBY = None


def _lobby_snapshot() -> dict:
    """Serializable view of current lobby for clients / debug."""
    if _LOBBY is None:
        return {"active": False}
    return {
        "active": True,
        "code": _LOBBY["code"],
        "host_puck_id": _LOBBY["host_puck_id"],
        "started": _LOBBY["started"],
        "session_code": _LOBBY.get("session_code"),
        "players": [
            {
                "puck_id": pid,
                "color": p["color"],
                "color_name": p["color_name"],
                "joined_at": p["joined_at"],
                "is_host": pid == _LOBBY["host_puck_id"],
            }
            for pid, p in sorted(_LOBBY["players"].items(), key=lambda kv: kv[1]["joined_at"])
        ],
    }


def _resolve_speed_pyramid_type_id() -> Optional[int]:
    ph = get_placeholder()
    row = execute_query(
        f"SELECT id FROM trivia_game_types WHERE name = {ph}",
        ("speed_pyramid",),
        fetch_one=True,
    )
    return row["id"] if row else None


# ============================================================================
# Pair endpoints
# ============================================================================

@pair_bp.route("/request", methods=["POST"])
def request_code():
    """First puck to call this creates the lobby and becomes the host.
    Subsequent pucks get the existing lobby code and a 'joiner' role.
    A puck calling /request twice is idempotent — same code returned."""
    global _LOBBY
    _purge_lobby_if_expired()

    data = request.get_json(silent=True) or {}
    puck_id_raw = data.get("puck_id")
    if puck_id_raw is None:
        return jsonify({"error": "puck_id required"}), 400
    puck_id = int(puck_id_raw)

    color_hex, color_name = _color_for(puck_id)

    # If a lobby exists and the match has started, reject new pair attempts.
    if _LOBBY is not None and _LOBBY["started"]:
        return jsonify(
            {"error": "match_in_progress",
             "message": "A match is already in progress. Wait for it to end."}
        ), 409

    if _LOBBY is None:
        # First puck — create new lobby with this puck as host.
        code = _new_code()
        _LOBBY = {
            "code": code,
            "host_puck_id": puck_id,
            "started": False,
            "session_code": None,
            "players": {},  # host added on confirm; joiners added below.
            "dials_in_progress": {puck_id: [None] * 6},
            "expires_at": _now() + _TTL_SECONDS,
        }
        role = "host"
        is_first = True
    else:
        role = "host" if _LOBBY["host_puck_id"] == puck_id else "joiner"
        _LOBBY["dials_in_progress"].setdefault(puck_id, [None] * 6)
        is_first = False

    # Joiners skip the dial-confirm step entirely — adding to the lobby on
    # request is the entire join action. The host still has to dial+confirm
    # so the TV can mirror the code in the air.
    joiner_added = False
    if role == "joiner" and puck_id not in _LOBBY["players"]:
        _LOBBY["players"][puck_id] = {
            "color": color_hex,
            "color_name": color_name,
            "joined_at": _now(),
        }
        joiner_added = True

    if _socketio is not None:
        # Title-screen browsers waiting in 'lobby' room jump to the
        # lobby/pair page when ANY puck requests pairing.
        _socketio.emit(
            "pair_started",
            {
                "puck_id": puck_id,
                "pair_code": _LOBBY["code"],
                "host_puck_id": _LOBBY["host_puck_id"],
                "is_first_player": is_first,
            },
            room="lobby",
        )

        # If a joiner was just added, broadcast player_joined to the pair
        # room so the LobbyScreen shows the new avatar without waiting for
        # a confirm that will never come.
        if joiner_added:
            _socketio.emit(
                "player_joined",
                {
                    "puck_id": puck_id,
                    "color": color_hex,
                    "color_name": color_name,
                    "role": role,
                    "players": _lobby_snapshot()["players"],
                },
                room=_LOBBY["code"],
            )

    return jsonify({
        "pair_code": _LOBBY["code"],
        "role": role,
        "color": color_hex,
        "color_name": color_name,
        "host_puck_id": _LOBBY["host_puck_id"],
        "players": _lobby_snapshot()["players"],
        "expires_at": _LOBBY["expires_at"],
        # Joiners get the lobby_code on request so the puck can jump
        # straight to LOBBY_WAITING with no dial step.
        "lobby_code": _LOBBY["code"] if role == "joiner" else None,
    })


@pair_bp.route("/preview", methods=["POST"])
def dial_preview():
    """Real-time dial preview. Only the HOST puck's preview is mirrored
    to the TV (joiners dial blind, trusting their puck LED)."""
    _purge_lobby_if_expired()
    if _LOBBY is None:
        return jsonify({"error": "no active lobby"}), 404

    data = request.get_json(silent=True) or {}
    puck_id_raw = data.get("puck_id")
    digit_index = data.get("digit_index")
    digit = data.get("digit")
    if puck_id_raw is None or digit_index is None or digit is None:
        return jsonify({"error": "puck_id, digit_index, digit required"}), 400
    puck_id = int(puck_id_raw)

    if puck_id != _LOBBY["host_puck_id"]:
        # Joiner — don't mirror to the TV. Silent success.
        return jsonify({"ok": True, "mirrored": False})

    if _socketio is not None:
        _socketio.emit(
            "pair_dial_preview",
            {"puck_id": puck_id, "digit_index": digit_index, "digit": digit},
            room=_LOBBY["code"],
        )
    return jsonify({"ok": True, "mirrored": True})


@pair_bp.route("/dial", methods=["POST"])
def dial_digit():
    """Locked-digit broadcast. Only the host's dial is mirrored on the TV;
    joiner dials are recorded server-side but not broadcast (joiners dial
    blind)."""
    _purge_lobby_if_expired()
    if _LOBBY is None:
        return jsonify({"error": "no active lobby"}), 404

    data = request.get_json(silent=True) or {}
    puck_id_raw = data.get("puck_id")
    digit_index = data.get("digit_index")
    digit = data.get("digit")
    if puck_id_raw is None or digit_index is None or digit is None:
        return jsonify({"error": "puck_id, digit_index, digit required"}), 400
    puck_id = int(puck_id_raw)
    if not isinstance(digit_index, int) or not (0 <= digit_index < 6):
        return jsonify({"error": "digit_index must be 0..5"}), 400
    if not isinstance(digit, int) or not (0 <= digit <= 9):
        return jsonify({"error": "digit must be 0..9"}), 400

    progress = _LOBBY["dials_in_progress"].setdefault(puck_id, [None] * 6)
    progress[digit_index] = digit

    if _socketio is not None and puck_id == _LOBBY["host_puck_id"]:
        _socketio.emit(
            "pair_dial_progress",
            {
                "puck_id": puck_id,
                "digit_index": digit_index,
                "digit": digit,
                "progress": progress,
            },
            room=_LOBBY["code"],
        )
    return jsonify({"accepted": True, "progress": progress})


@pair_bp.route("/confirm", methods=["POST"])
def confirm_code():
    """Puck submits its 6-digit dial. Adds the puck to the lobby's
    players. Does NOT create the trivia session yet — that happens when
    the host calls /api/pair/start."""
    _purge_lobby_if_expired()
    if _LOBBY is None:
        return jsonify({"error": "no active lobby"}), 404
    if _LOBBY["started"]:
        return jsonify({"error": "match_in_progress"}), 409

    data = request.get_json(silent=True) or {}
    puck_id_raw = data.get("puck_id")
    code = data.get("code")
    if puck_id_raw is None or code is None:
        return jsonify({"error": "puck_id and code required"}), 400
    puck_id = int(puck_id_raw)

    if str(code) != _LOBBY["code"]:
        return jsonify({"error": "code does not match"}), 401

    color_hex, color_name = _color_for(puck_id)
    if puck_id not in _LOBBY["players"]:
        _LOBBY["players"][puck_id] = {
            "color": color_hex,
            "color_name": color_name,
            "joined_at": _now(),
        }

    snapshot = _lobby_snapshot()
    role = "host" if _LOBBY["host_puck_id"] == puck_id else "joiner"

    if _socketio is not None:
        _socketio.emit(
            "player_joined",
            {
                "puck_id": puck_id,
                "color": color_hex,
                "color_name": color_name,
                "role": role,
                "players": snapshot["players"],
            },
            room=_LOBBY["code"],
        )
    return jsonify({
        "role": role,
        "color": color_hex,
        "color_name": color_name,
        "players": snapshot["players"],
        "host_puck_id": _LOBBY["host_puck_id"],
        "lobby_code": _LOBBY["code"],
    })


@pair_bp.route("/start", methods=["POST"])
def start_match():
    """Host puck taps to start the match. Creates the underlying trivia
    session, registers all lobby players, transitions the lobby to
    started state."""
    _purge_lobby_if_expired()
    if _LOBBY is None:
        return jsonify({"error": "no active lobby"}), 404
    if _LOBBY["started"]:
        # Idempotent: returning the existing session_code is fine if the
        # host taps again.
        return jsonify({
            "ok": True,
            "session_code": _LOBBY["session_code"],
            "already_started": True,
        })

    data = request.get_json(silent=True) or {}
    puck_id_raw = data.get("puck_id")
    if puck_id_raw is None:
        return jsonify({"error": "puck_id required"}), 400
    puck_id = int(puck_id_raw)
    if puck_id != _LOBBY["host_puck_id"]:
        return jsonify({"error": "only host can start"}), 403

    if not _LOBBY["players"]:
        return jsonify({"error": "no players have confirmed yet"}), 400

    game_type_id = _resolve_speed_pyramid_type_id()
    if game_type_id is None:
        return jsonify({"error": "speed_pyramid game type not seeded"}), 500

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
        for pid in _LOBBY["players"]:
            add_player_to_session(
                session_id=session_row["id"], puck_id=pid, player_name=None
            )

    _LOBBY["started"] = True
    _LOBBY["session_code"] = session_code

    if _socketio is not None:
        _socketio.emit(
            "match_started",
            {
                "session_code": session_code,
                "host_puck_id": _LOBBY["host_puck_id"],
                "players": _lobby_snapshot()["players"],
            },
            room=_LOBBY["code"],
        )
    return jsonify({"ok": True, "session_code": session_code})


@pair_bp.route("/lobby-state", methods=["GET"])
def lobby_state():
    """Read the current lobby state. Used by both pucks (polling to
    learn 'has the host started yet?') and any browser tab that
    refreshes mid-lobby."""
    _purge_lobby_if_expired()
    return jsonify(_lobby_snapshot())


@pair_bp.route("/clear", methods=["POST"])
def clear_lobby_endpoint():
    """Admin/debug: full server reset. Clears the active lobby AND every
    cached Speed Pyramid session state + question tracker. Without the
    full wipe, stale _SP_STATE[old_sc].complete=true would keep any
    polling puck pinned in its MATCH_ENDED state even after the lobby
    is gone — the puck would never recover to IDLE for a fresh pair.

    Broadcasts `lobby_cancelled` so any TV currently parked on the
    scoreboard or mid-question reverts to the title screen."""
    _clear_lobby()
    _SP_STATE.clear()
    _QUESTION_TRACKER.clear()
    try:
        import trivia_routes
        trivia_routes._question_start_times.clear()
    except Exception:
        pass
    if _socketio is not None:
        _socketio.emit("lobby_cancelled", {"reason": "admin_reset"})
    return jsonify({"ok": True})


@pair_bp.route("/cancel", methods=["POST"])
def cancel_lobby():
    """Player-initiated lobby cancel via HOLD_3S on the puck.

    - If the host cancels: kill the whole lobby, emit lobby_cancelled to
      the pair room so all joiners (and the TV) bounce back to title.
    - If a joiner cancels: remove just that joiner from the lobby and
      emit player_left so the LobbyScreen can drop their avatar.
    """
    global _LOBBY
    _purge_lobby_if_expired()
    if _LOBBY is None:
        return jsonify({"ok": True, "noop": True})

    data = request.get_json(silent=True) or {}
    puck_id_raw = data.get("puck_id")
    if puck_id_raw is None:
        return jsonify({"error": "puck_id required"}), 400
    puck_id = int(puck_id_raw)

    if _LOBBY["started"]:
        return jsonify({"error": "match_in_progress"}), 409

    code = _LOBBY["code"]
    is_host = _LOBBY["host_puck_id"] == puck_id

    if is_host:
        if _socketio is not None:
            _socketio.emit(
                "lobby_cancelled",
                {"by_puck_id": puck_id, "reason": "host_cancelled"},
                room=code,
            )
        _clear_lobby()
        return jsonify({"ok": True, "scope": "lobby"})

    # Joiner: drop just this puck.
    _LOBBY["players"].pop(puck_id, None)
    _LOBBY["dials_in_progress"].pop(puck_id, None)
    if _socketio is not None:
        _socketio.emit(
            "player_left",
            {
                "puck_id": puck_id,
                "players": _lobby_snapshot()["players"],
            },
            room=code,
        )
    return jsonify({"ok": True, "scope": "self"})


# ============================================================================
# Speed Pyramid v1.1 endpoints (unchanged from previous slice)
# ============================================================================

_SP_STATE: dict[str, dict] = {}
# {
#   "round": int,                 # round_number of the LATEST loaded Q
#   "asked_ids": set[int],
#   "complete": bool,
#   "expected_pucks": set[int],   # pucks registered to this session
#   "current_question_id": int | None,
#   "current_round_started_at": float | None,
#   "current_round_answers": dict[puck_id, dict],
#     # puck_id -> {answer, is_correct, points, tier, response_time_ms, color, color_name}
#   "cumulative_scores": dict[puck_id, int],
#   "revealed_for_question_id": int | None,  # idempotency guard
# }
SP_TOTAL_ROUNDS = 7


def _load_expected_pucks_for_session(session_code: str) -> set[int]:
    """Read trivia_session_players to learn which pucks are in this match.
    Cache result in _SP_STATE['expected_pucks']."""
    ph = get_placeholder()
    row = execute_query(
        f"SELECT id FROM trivia_sessions WHERE session_code = {ph}",
        (session_code,),
        fetch_one=True,
    )
    if not row:
        return set()
    rows = execute_query(
        f"SELECT puck_id FROM trivia_session_players WHERE session_id = {ph}",
        (row["id"],),
        fetch_all=True,
    ) or []
    return {int(r["puck_id"]) for r in rows}


def _sp_state_for(session_code: str) -> dict:
    """Get or initialize the per-session state, including expected_pucks
    loaded from DB on first access."""
    state = _SP_STATE.get(session_code)
    if state is None:
        state = {
            "round": 0,
            "asked_ids": set(),
            "complete": False,
            "expected_pucks": _load_expected_pucks_for_session(session_code),
            "current_question_id": None,
            "current_round_started_at": None,
            "current_round_answers": {},
            "cumulative_scores": {},
            "revealed_for_question_id": None,
        }
        _SP_STATE[session_code] = state
    elif "expected_pucks" not in state:
        # Backfill missing fields for sessions created by earlier code paths.
        state.setdefault("expected_pucks", _load_expected_pucks_for_session(session_code))
        state.setdefault("current_question_id", None)
        state.setdefault("current_round_started_at", None)
        state.setdefault("current_round_answers", {})
        state.setdefault("cumulative_scores", {})
        state.setdefault("revealed_for_question_id", None)
    return state


def _difficulty_for_round(r: int) -> str:
    if r <= 2:
        return "easy"
    if r <= 5:
        return "medium"
    return "hard"


def _narration_url(question_id: int) -> str:
    """Canonical narration MP3 path for a question. The file may not
    exist on disk (TTS generation is a separate content task); the TV
    treats a 404 as 'no narration', shows the question silently, and
    falls back to procedural SFX for the lock/reveal beats."""
    return f"/static/games/speed-pyramid/audio/questions/q_{question_id}.mp3"


@sp_bp.route("/load-question/<session_code>", methods=["POST"])
def sp_load_question(session_code: str):
    state = _sp_state_for(session_code)

    if state["round"] >= SP_TOTAL_ROUNDS:
        state["complete"] = True
        if _socketio is not None:
            _socketio.emit(
                "match_ended",
                {"session_code": session_code, "rounds": SP_TOTAL_ROUNDS},
                room=session_code,
            )
        # Also clear the active lobby so a new match can be started.
        global _LOBBY
        if _LOBBY is not None and _LOBBY.get("session_code") == session_code:
            _clear_lobby()
        return jsonify(
            {"error": "match_complete", "rounds": SP_TOTAL_ROUNDS}
        ), 409

    # Idempotency: if a question is already active for this round (set
    # but not yet revealed), return that question instead of advancing.
    # Two concurrent callers (e.g. the TV's mount-time load + a polling
    # client) would otherwise double-increment the round counter and
    # cause the match to appear to start on round 2 with answers landing
    # on stale question IDs (=> server returns 409 => puck registers as
    # TIMEOUT). See docs/adr/0002 + Virtual Puck Hub prototype notes.
    cur_qid = state.get("current_question_id")
    revealed_qid = state.get("revealed_for_question_id")
    if cur_qid is not None and cur_qid != revealed_qid:
        ph = get_placeholder()
        existing_q = execute_query(
            f"SELECT * FROM trivia_questions WHERE id = {ph}",
            (cur_qid,),
            fetch_one=True,
        )
        if existing_q:
            cat = execute_query(
                f"SELECT name, emoji FROM trivia_categories WHERE id = {ph}",
                (existing_q["category_id"],),
                fetch_one=True,
            )
            return jsonify({
                "round": state["round"],
                "total_rounds": SP_TOTAL_ROUNDS,
                "question": {
                    "id": existing_q["id"],
                    "setup": existing_q["setup_text"],
                    "question": existing_q["question_text"],
                    "answers": {
                        "A": existing_q["answer_a"],
                        "B": existing_q["answer_b"],
                        "C": existing_q["answer_c"],
                        "D": existing_q["answer_d"],
                    },
                    "difficulty": existing_q["difficulty"],
                    "time_limit": existing_q["time_limit"] or 10,
                    "category": cat["name"] if cat else "",
                    "category_emoji": cat["emoji"] if cat else "",
                },
                "audio_url": _narration_url(existing_q["id"]),
                "started_at": state.get("current_round_started_at"),
                "expected_pucks": list(state.get("expected_pucks") or []),
                "is_final": state["round"] >= SP_TOTAL_ROUNDS,
            })

    next_round = state["round"] + 1
    difficulty = _difficulty_for_round(next_round)
    exclude = list(state["asked_ids"]) or None
    q = get_random_question(difficulty=difficulty, exclude_ids=exclude)
    if not q:
        q = get_random_question(exclude_ids=exclude)
    if not q:
        return jsonify({"error": "no questions available"}), 404

    state["round"] = next_round
    state["asked_ids"].add(q["id"])
    state["current_question_id"] = q["id"]
    state["current_round_answers"] = {}
    state["revealed_for_question_id"] = None
    # If expected_pucks wasn't set yet (e.g. first load before any
    # players registered, or DB lookup race), retry it now.
    if not state["expected_pucks"]:
        state["expected_pucks"] = _load_expected_pucks_for_session(session_code)

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
    state["current_round_started_at"] = started_at
    if _socketio is not None:
        _socketio.emit(
            "question_show",
            {
                "session_code": session_code,
                "question": payload_question,
                "audio_url": _narration_url(q["id"]),
                "round": next_round,
                "total_rounds": SP_TOTAL_ROUNDS,
                "started_at": started_at,
                "expected_pucks": sorted(state["expected_pucks"]),
            },
            room=session_code,
        )

    _QUESTION_TRACKER[session_code] = {
        "question_id": q["id"],
        "started_at": started_at,
    }
    try:
        import trivia_routes
        trivia_routes._question_start_times[session_code] = {
            "question_id": q["id"],
            "started_at": started_at,
        }
    except Exception:
        pass
    print(f"[sp] loaded Q{q['id']} for session={session_code} difficulty={q['difficulty']}")

    return jsonify(
        {
            "question": payload_question,
            "audio_url": _narration_url(q["id"]),
            "round": next_round,
            "total_rounds": SP_TOTAL_ROUNDS,
            "started_at": started_at,
            "expected_pucks": sorted(state["expected_pucks"]),
        }
    )


@sp_bp.route("/match-state/<session_code>", methods=["GET"])
def sp_match_state(session_code: str):
    state = _SP_STATE.get(session_code)
    if not state:
        # `exists: false` distinguishes "admin wiped this session" from
        # "session exists but match is over" — both return complete=false
        # if you only look at that field after sp_reset. Polling pucks
        # need the difference: missing session => drop to IDLE; existing
        # session with complete=false => Play again happened, drop to
        # IN_GAME_IDLE and wait for the new question.
        return jsonify(
            {
                "exists": False,
                "round": 0,
                "total_rounds": SP_TOTAL_ROUNDS,
                "complete": False,
            }
        )
    return jsonify(
        {
            "exists": True,
            "round": state["round"],
            "total_rounds": SP_TOTAL_ROUNDS,
            "questions_asked": len(state["asked_ids"]),
            "complete": bool(state.get("complete", False)),
        }
    )


@sp_bp.route("/final-results/<session_code>", methods=["GET"])
def sp_final_results(session_code: str):
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
                    "color": _color_for(int(r["puck_id"]))[0],
                    "color_name": _color_for(int(r["puck_id"]))[1],
                }
                for r in rows
            ],
        }
    )


@sp_bp.route("/reset/<session_code>", methods=["POST"])
def sp_reset(session_code: str):
    _SP_STATE[session_code] = {
        "round": 0,
        "asked_ids": set(),
        "complete": False,
        "expected_pucks": _load_expected_pucks_for_session(session_code),
        "current_question_id": None,
        "current_round_started_at": None,
        "current_round_answers": {},
        "cumulative_scores": {},
        "revealed_for_question_id": None,
    }
    # Drop the cached "currently active question" too. Otherwise polling
    # /api/sp/current-question after reset returns the LAST question of
    # the previous match and pucks transition into IN_GAME_ANSWERING for
    # a stale qid that /api/sp/answer rightly rejects with 409.
    _QUESTION_TRACKER.pop(session_code, None)
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


def _maybe_emit_reveal(session_code: str, force: bool = False) -> bool:
    """If every expected puck has locked an answer for the current
    round (or if explicitly force-revealed), emit the aggregate reveal
    event and update cumulative scores. Returns True if reveal was
    emitted now, False if still waiting.

    When `force=True` (called from the force-reveal endpoint on timer
    expiry), skip the wait-for-all gate and proceed straight to filling
    TIMEOUT entries for any silent puck."""
    state = _sp_state_for(session_code)
    qid = state["current_question_id"]
    if qid is None:
        return False
    if state["revealed_for_question_id"] == qid:
        return False  # already revealed this round

    expected = state["expected_pucks"] or set()
    answers = state["current_round_answers"]
    if not force and expected and not all(pid in answers for pid in expected):
        return False  # still waiting on someone

    # Determine the correct answer + host commentary for this question.
    ph = get_placeholder()
    q = execute_query(
        f"SELECT correct_answer, host_commentary_correct, host_commentary_wrong "
        f"FROM trivia_questions WHERE id = {ph}",
        (qid,),
        fetch_one=True,
    )
    correct_answer = q["correct_answer"] if q else None
    commentary_correct = (q["host_commentary_correct"] if q else None) or ""
    commentary_wrong = (q["host_commentary_wrong"] if q else None) or ""

    # Fill TIMEOUT entries for any expected puck that didn't answer.
    for pid in expected:
        if pid not in answers:
            color_hex, color_name = _color_for(pid)
            answers[pid] = {
                "answer": None,
                "is_correct": False,
                "points": 0,
                "tier": "TIMEOUT",
                "response_time_ms": None,
                "color": color_hex,
                "color_name": color_name,
            }

    # Update cumulative scores.
    for pid, a in answers.items():
        state["cumulative_scores"][pid] = state["cumulative_scores"].get(pid, 0) + int(a["points"])

    results = [
        {
            "puck_id": pid,
            "answer": answers[pid]["answer"],
            "is_correct": answers[pid]["is_correct"],
            "points": answers[pid]["points"],
            "tier": answers[pid]["tier"],
            "response_time_ms": answers[pid]["response_time_ms"],
            "color": answers[pid]["color"],
            "color_name": answers[pid]["color_name"],
            "cumulative_total": state["cumulative_scores"][pid],
        }
        for pid in sorted(answers.keys())
    ]

    state["revealed_for_question_id"] = qid

    if _socketio is not None:
        _socketio.emit(
            "reveal",
            {
                "session_code": session_code,
                "question_id": qid,
                "correct_answer": correct_answer,
                "commentary_correct": commentary_correct,
                "commentary_wrong": commentary_wrong,
                "results": results,
            },
            room=session_code,
        )
    return True


@sp_bp.route("/start-timer/<session_code>", methods=["POST"])
def sp_start_timer(session_code: str):
    """Mark the question countdown as starting NOW. Decouples the timer
    from question-load so the TV can pause the countdown during the
    narration MP3 and call this when narration ends (or errors). Without
    this handoff the 15s clock starts ticking while the host is still
    reading the setup.

    Idempotent: calling repeatedly just refreshes started_at. Returns
    400 if no current question.
    """
    state = _SP_STATE.get(session_code)
    if state is None or state.get("current_question_id") is None:
        return jsonify({"ok": False, "reason": "no current question"}), 400
    now = _now()
    state["current_round_started_at"] = now
    tracker = _QUESTION_TRACKER.get(session_code)
    if tracker is not None:
        tracker["started_at"] = now
    if _socketio is not None:
        _socketio.emit(
            "timer_started",
            {
                "session_code": session_code,
                "question_id": state["current_question_id"],
                "started_at": now,
            },
            room=session_code,
        )
    return jsonify({"ok": True, "started_at": now})


@sp_bp.route("/force-reveal/<session_code>", methods=["POST"])
def sp_force_reveal(session_code: str):
    """Called by the TV when the question timer expires. Forces the
    aggregate reveal, marking unanswered pucks as TIMEOUT."""
    state = _sp_state_for(session_code)
    if state["current_question_id"] is None:
        return jsonify({"ok": False, "reason": "no current question"}), 400
    emitted = _maybe_emit_reveal(session_code, force=True)
    return jsonify({"ok": True, "emitted": emitted})


@sp_bp.route("/answer", methods=["POST"])
def sp_answer():
    """Speed-Pyramid-specific answer endpoint. Records the per-puck
    answer in _SP_STATE.current_round_answers. Emits answer_locked for
    THIS puck. If all expected pucks have answered, emits the aggregate
    reveal."""
    data = request.get_json(silent=True) or {}
    session_code = data.get("session_code")
    puck_id_raw = data.get("puck_id")
    question_id = data.get("question_id")
    answer = data.get("answer")
    response_time_ms = int(data.get("response_time_ms") or 0)

    if not session_code or puck_id_raw is None or question_id is None or answer is None:
        return jsonify({"error": "session_code, puck_id, question_id, answer required"}), 400

    puck_id = int(puck_id_raw)
    state = _sp_state_for(session_code)
    if state["current_question_id"] != int(question_id):
        return jsonify({"error": "question_id does not match active round"}), 409
    if puck_id in state["current_round_answers"]:
        return jsonify({"error": "already answered"}), 409

    # Score this answer using SpeedPyramidGame's tier logic.
    ph = get_placeholder()
    q = execute_query(
        f"SELECT correct_answer FROM trivia_questions WHERE id = {ph}",
        (int(question_id),),
        fetch_one=True,
    )
    if not q:
        return jsonify({"error": "question not found"}), 404
    correct_answer = q["correct_answer"]
    is_correct = (answer == correct_answer)

    # Authoritative response_time from the server side.
    started = state.get("current_round_started_at") or _now()
    server_response_time_ms = int((_now() - started) * 1000)
    # Prefer the puck-reported time if it's reasonable (within ±2s of
    # server's measurement). Otherwise use server's.
    if abs(server_response_time_ms - response_time_ms) > 2000:
        response_time_ms = server_response_time_ms

    from trivia_game_engines import SpeedPyramidGame
    engine = SpeedPyramidGame(None, [{"puck_id": puck_id, "multiplier": 1.0}])
    points = engine.calculate_points(puck_id, is_correct, response_time_ms)
    tier = engine.tier_for(response_time_ms) if is_correct else "WRONG"
    color_hex, color_name = _color_for(puck_id)

    state["current_round_answers"][puck_id] = {
        "answer": answer,
        "is_correct": is_correct,
        "points": int(points),
        "tier": tier,
        "response_time_ms": int(response_time_ms),
        "color": color_hex,
        "color_name": color_name,
    }

    # Record in DB for the final-results endpoint.
    try:
        from trivia_database import record_answer
        sess = execute_query(
            f"SELECT id FROM trivia_sessions WHERE session_code = {ph}",
            (session_code,),
            fetch_one=True,
        )
        if sess:
            record_answer(
                sess["id"],
                int(question_id),
                puck_id,
                answer,
                is_correct,
                int(response_time_ms),
                int(points),
            )
    except Exception as e:
        print(f"[sp/answer] record_answer failed: {e}")

    # Emit answer_locked so the TV's sidebar can highlight this row as
    # "locked" even before the reveal fires (other players may still be
    # thinking).
    if _socketio is not None:
        _socketio.emit(
            "answer_locked",
            {
                "session_code": session_code,
                "puck_id": puck_id,
                "answer": answer,
                "question_id": int(question_id),
                "color": color_hex,
            },
            room=session_code,
        )

    # Try to emit reveal if all expected pucks have now answered.
    emitted_reveal = _maybe_emit_reveal(session_code)

    return jsonify({
        "ok": True,
        "is_correct": is_correct,
        "points": int(points),
        "tier": tier,
        "response_time_ms": int(response_time_ms),
        "reveal_emitted": emitted_reveal,
    })


@sp_bp.route("/current-question/<session_code>", methods=["GET"])
def sp_current_question(session_code: str):
    # When the match is complete, callers must see active=false so
    # polling pucks/clients can exit IN_GAME_ANSWERING. _QUESTION_TRACKER
    # holds the LAST question forever otherwise, and ANSWERING-state
    # polling has no other signal that the match ended.
    state = _SP_STATE.get(session_code)
    if state is not None and state.get("complete"):
        return jsonify({"active": False, "complete": True})

    sst = _QUESTION_TRACKER.get(session_code)
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
