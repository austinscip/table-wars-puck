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
            # Slice E1 — category picker state.
            "pending_category_pick": None,    # {picker_puck_id, offer, deadline_at, started_at}
            "next_category_id": None,         # set when picker locks an offer; consumed by next load-question
            "last_round_winner_puck_id": None,# tracked at reveal; drives subsequent picks
            # Slice E2 — minigame state.
            "pending_minigame": None,         # {flavor, duration_s, target_quadrant?, started_at, deadline_at, fires}
            "minigame_resolved_round": None,  # last round we already played a minigame for (gates re-entry)
            # Slice E3 — power-ups + sabotage.
            "power_up_inventories": {},       # puck_id -> [{id: uuid, type}]
            "power_up_arms": {},              # puck_id -> {double, reveal, shield, incoming_steals: [firer_puck_id]}
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
    # Slice E1 fields can be missing on pre-E1 in-memory sessions.
    state.setdefault("pending_category_pick", None)
    state.setdefault("next_category_id", None)
    state.setdefault("last_round_winner_puck_id", None)
    # Slice E2 fields.
    state.setdefault("pending_minigame", None)
    state.setdefault("minigame_resolved_round", None)
    # Slice E3 fields.
    state.setdefault("power_up_inventories", {})
    state.setdefault("power_up_arms", {})
    return state


# Slice E3 — power-up catalog.
SP_POWER_UP_TYPES = ("DOUBLE", "SHIELD", "REVEAL", "STEAL")


def _empty_arms() -> dict:
    return {"double": False, "reveal": False, "shield": False, "incoming_steals": []}


def _grant_power_up(state: dict, session_code: str, puck_id: int) -> dict | None:
    """Grant a random power-up to the given puck. Returns the granted
    item dict for inclusion in socket payloads, or None if grant
    failed (shouldn't happen). Emits inventory_updated so the TV HUD
    refreshes."""
    import random as _random
    import uuid as _uuid
    item = {"id": _uuid.uuid4().hex[:12], "type": _random.choice(SP_POWER_UP_TYPES)}
    inv = state["power_up_inventories"].setdefault(int(puck_id), [])
    inv.append(item)
    if _socketio is not None:
        _socketio.emit(
            "inventory_updated",
            {"session_code": session_code, "puck_id": int(puck_id),
             "items": list(inv)},
            room=session_code,
        )
    return item


def _persist_reveal_correct(session_code: str, qid: int, puck_id: int, ans: dict) -> None:
    """Write a REVEAL-forced result back to trivia_answers so
    final-results (which derives `correct` from the DB) reflects what
    the reveal feed showed. The in-memory ans["is_correct"]=True set by
    a REVEAL arm is otherwise never persisted: a wrong answer leaves a
    stale is_correct=False row, and a timed-out puck has no row at all,
    so SUM(is_correct) under-counts the corrects players actually saw.

    There is no UNIQUE constraint on (session_id, question_id, puck_id),
    so UPDATE the existing row if present, else INSERT one. A timed-out
    puck (answer=None) stores the question's correct_answer letter so
    the row satisfies the A/B/C/D CHECK and shows as a correct answer."""
    ph = get_placeholder()
    sess = execute_query(
        f"SELECT id FROM trivia_sessions WHERE session_code = {ph}",
        (session_code,),
        fetch_one=True,
    )
    if not sess:
        return
    sid = sess["id"]
    answer_letter = ans.get("answer")
    if answer_letter is None:
        q = execute_query(
            f"SELECT correct_answer FROM trivia_questions WHERE id = {ph}",
            (qid,),
            fetch_one=True,
        )
        answer_letter = q["correct_answer"] if q else "A"
    points = int(ans.get("points", 0))
    rt = ans.get("response_time_ms")
    existing = execute_query(
        f"SELECT id, points_earned FROM trivia_answers "
        f"WHERE session_id = {ph} AND question_id = {ph} AND puck_id = {ph}",
        (sid, qid, puck_id),
        fetch_one=True,
    )
    if existing:
        # Correct the stale row and reconcile the cached player score by
        # the points delta so totals stay consistent.
        delta = points - int(existing["points_earned"] or 0)
        execute_query(
            f"UPDATE trivia_answers SET is_correct = {ph}, points_earned = {ph}, "
            f"answer_given = {ph} WHERE id = {ph}",
            (True, points, answer_letter, existing["id"]),
        )
        if delta:
            execute_query(
                f"UPDATE trivia_session_players SET total_score = total_score + {ph} "
                f"WHERE session_id = {ph} AND puck_id = {ph}",
                (delta, sid, puck_id),
            )
    else:
        from trivia_database import record_answer
        record_answer(
            sid, qid, puck_id, answer_letter, True,
            int(rt) if rt is not None else 0, points,
        )


def _apply_power_up_arms(state: dict, session_code: str, qid: int, answers: dict) -> None:
    """Apply armed power-up effects to this question's answers BEFORE
    cumulative scoring. Called from _maybe_emit_reveal once all pucks
    have answered (or timed out). Mutates the answers dict in place:
    REVEAL forces is_correct/tier/points to LEGENDARY-equivalent.
    DOUBLE multiplies the puck's points by 2. STEAL queues a transfer
    of half the target's points to the firer (applied after the
    target's own scoring). SHIELD nullifies one incoming STEAL.

    Arms are one-shot per question — cleared after application."""
    arms_table = state.get("power_up_arms", {})
    if not arms_table:
        return
    # Apply REVEAL + DOUBLE first (affects each puck's own score).
    revealed_pucks: list[int] = []
    for pid, ans in answers.items():
        arms = arms_table.get(pid)
        if not arms:
            continue
        # A puck that never answered (TIMEOUT fill: answer is None) must
        # NOT be rewarded a correct LEGENDARY result by an armed REVEAL —
        # REVEAL auto-corrects an attempted answer, not a no-show. (R031)
        timed_out = ans.get("answer") is None or ans.get("tier") == "TIMEOUT"
        if arms.get("reveal") and not timed_out:
            # Auto-correct: LEGENDARY tier (0-3s correct = 1000pt).
            ans["is_correct"] = True
            ans["points"] = 1000
            ans["tier"] = "LEGENDARY"
            revealed_pucks.append(pid)
        if arms.get("double"):
            ans["points"] = int(ans.get("points", 0)) * 2
    # STEAL: process AFTER reveal/double so the stolen amount reflects
    # any reveal/double on the target. For each target with incoming
    # steals that aren't shielded, transfer half their points to the
    # firers. Two correctness guarantees (R035):
    #   1. Snapshot every target's points BEFORE any transfer mutates the
    #      dict, so a mutual steal (p1<->p2) is order-independent — the
    #      amount stolen from a target never depends on whether that
    #      target was already drained as a firer this pass.
    #   2. The total taken from a target == target_points // 2 exactly:
    #      distribute the remainder of an uneven split so floor-division
    #      across N firers never under-transfers (100/3 -> 17+17+16=50,
    #      not 16+16+16=48).
    # A firer that did not answer this round (no entry, or a TIMEOUT fill
    # whose answer is None) must NOT profit — it steals 0.
    points_snapshot = {pid: int(a.get("points", 0)) for pid, a in answers.items()}
    for target_pid, ans in answers.items():
        arms = arms_table.get(target_pid)
        if not arms:
            continue
        incoming = arms.get("incoming_steals") or []
        if not incoming:
            continue
        if arms.get("shield"):
            # Single shield blocks ALL incoming steals this round.
            # (Simpler than per-source; matches the catalog blurb.)
            incoming = []
        # Only firers that actually answered this round may steal.
        eligible = [
            f for f in incoming
            if (answers.get(f) is not None
                and answers[f].get("answer") is not None
                and answers[f].get("tier") != "TIMEOUT")
        ]
        if not eligible:
            continue
        target_points = points_snapshot.get(target_pid, int(ans.get("points", 0)))
        if target_points <= 0:
            continue
        total_steal = target_points // 2
        if total_steal <= 0:
            continue
        n = len(eligible)
        base = total_steal // n
        remainder = total_steal - base * n
        for idx, firer_pid in enumerate(eligible):
            # Hand the remainder to the leading firers so the per-target
            # total comes out to exactly total_steal.
            stolen_each = base + (1 if idx < remainder else 0)
            if stolen_each <= 0:
                continue
            firer_ans = answers.get(firer_pid)
            firer_ans["points"] = int(firer_ans.get("points", 0)) + stolen_each
            ans["points"] = int(ans.get("points", 0)) - stolen_each
            if _socketio is not None:
                _socketio.emit(
                    "power_up_resolved",
                    {
                        "session_code": session_code,
                        "type": "STEAL",
                        "firer_puck_id": int(firer_pid),
                        "target_puck_id": int(target_pid),
                        "points_transferred": stolen_each,
                    },
                    room=session_code,
                )
    # Persist REVEAL-forced corrects to the DB so final-results (which
    # derives `correct` from trivia_answers) matches the reveal feed.
    # Done after DOUBLE/STEAL so the persisted points reflect the final
    # per-round value the players saw.
    for pid in revealed_pucks:
        try:
            _persist_reveal_correct(session_code, qid, pid, answers[pid])
        except Exception as e:  # noqa: BLE001
            print(f"[sp/reveal] persist REVEAL correct failed: {e}")

    # Clear all arms (one-shot per round).
    state["power_up_arms"] = {}


# Slice E1 — category picker policy.
# Picks fire BEFORE these question rounds (where state["round"] is the
# round about to start, i.e. next_round after increment).
SP_PICK_ROUNDS = {1, 3, 5, 7}
SP_PICK_OFFER_SIZE = 3
SP_PICK_TIMEOUT_SEC = 10.0


def _eligible_categories_for_pick(difficulty: str, asked_ids: set) -> list[dict]:
    """Return categories that still have at least one unused question at
    the requested difficulty. Caller picks SP_PICK_OFFER_SIZE at random."""
    ph = get_placeholder()
    placeholders = ",".join(["?"] * (len(asked_ids) or 1))
    exclude = list(asked_ids) if asked_ids else [-1]
    rows = execute_query(
        f"SELECT c.id, c.name, c.emoji, COUNT(q.id) AS remaining "
        f"FROM trivia_categories c "
        f"JOIN trivia_questions q ON q.category_id = c.id "
        f"WHERE q.difficulty = {ph} AND q.id NOT IN ({placeholders}) "
        f"GROUP BY c.id "
        f"HAVING remaining > 0 "
        f"ORDER BY c.id",
        tuple([difficulty] + exclude),
        fetch_all=True,
    ) or []
    return [
        {"id": r["id"], "name": r["name"], "emoji": r["emoji"] or "",
         "question_count": int(r["remaining"])}
        for r in rows
    ]


def _build_pick_offer(state: dict, next_round: int) -> dict:
    """Compose the {picker_puck_id, offer, deadline_at, started_at}
    record for an upcoming pick. Picker rules: round-1 has no prior
    winner, so the lowest expected puck_id picks; otherwise the round-N
    winner picks for the next pick round (per user decision)."""
    import random as _random
    expected = sorted(state.get("expected_pucks") or {1})
    if next_round == 1 or not state.get("last_round_winner_puck_id"):
        picker = expected[0] if expected else 1
    else:
        picker = int(state["last_round_winner_puck_id"])
        # Fall back to lowest expected if the prior winner is gone.
        if picker not in expected and expected:
            picker = expected[0]
    difficulty = _difficulty_for_round(next_round)
    pool = _eligible_categories_for_pick(difficulty, state.get("asked_ids") or set())
    if not pool:
        # Fallback: any category with any question left.
        pool = _eligible_categories_for_pick("medium", state.get("asked_ids") or set())
    _random.shuffle(pool)
    offer = pool[:SP_PICK_OFFER_SIZE]
    now = _now()
    return {
        "picker_puck_id": int(picker),
        "offer": offer,
        "started_at": now,
        "deadline_at": now + SP_PICK_TIMEOUT_SEC,
    }


def _maybe_auto_resolve_pick(state: dict) -> bool:
    """If pending_category_pick has expired with no selection, lock in
    the first offer. Returns True if auto-resolved."""
    pp = state.get("pending_category_pick")
    if not pp:
        return False
    if _now() < pp.get("deadline_at", 0):
        return False
    offer = pp.get("offer") or []
    if not offer:
        # No offers to default to — clear and let next load-question
        # produce a question without a category filter.
        state["pending_category_pick"] = None
        return True
    state["next_category_id"] = int(offer[0]["id"])
    state["pending_category_pick"] = None
    return True


# Slice E2 — minigame policy.
# Minigames fire BEFORE these question rounds (next_round in 2/4/6).
SP_MINIGAME_ROUNDS = {2, 4, 6}
# BULLSEYE: 8s aim window. Quadrant match × speed bonus.
SP_BULLSEYE_DURATION_S = 8.0
# SHOT_CLOCK: 3s sweep cycle, 30% green zone in the middle.
SP_SHOTCLOCK_DURATION_S = 8.0
SP_SHOTCLOCK_CYCLE_MS = 3000
SP_SHOTCLOCK_GREEN_FRAC = 0.30
# Reward: bonus points added directly to cumulative_scores.
SP_MINIGAME_WIN_BONUS = 500
SP_MINIGAME_SECOND_BONUS = 200


def _build_minigame_phase(state: dict, next_round: int) -> dict:
    """Compose the {flavor, duration_s, target_quadrant?, started_at,
    deadline_at, fires} record for an upcoming minigame. Flavor
    alternates by round (2=BULLSEYE, 4=SHOT_CLOCK, 6=BULLSEYE).
    BULLSEYE picks a target quadrant on the server so all pucks aim
    at the same target."""
    import random as _random
    flavor = "BULLSEYE" if next_round in (2, 6) else "SHOT_CLOCK"
    now = _now()
    if flavor == "BULLSEYE":
        duration_s = SP_BULLSEYE_DURATION_S
        target_quadrant = _random.choice(["A", "B", "C", "D"])
    else:
        duration_s = SP_SHOTCLOCK_DURATION_S
        target_quadrant = None
    return {
        "flavor": flavor,
        "duration_s": duration_s,
        "target_quadrant": target_quadrant,
        "cycle_ms": SP_SHOTCLOCK_CYCLE_MS if flavor == "SHOT_CLOCK" else None,
        "green_frac": SP_SHOTCLOCK_GREEN_FRAC if flavor == "SHOT_CLOCK" else None,
        "started_at": now,
        "deadline_at": now + duration_s,
        "fires": {},  # puck_id -> {t_ms, quadrant, points}
    }


def _score_minigame_fire(mg: dict, t_ms: int, quadrant: str | None) -> int:
    """Compute points for a single puck's fire. BULLSEYE: quadrant
    match × speed bonus. SHOT_CLOCK: closeness to green-zone center
    on a sweep cycle. Both top out at 1000 to slot into the existing
    LEGENDARY-equivalent scale; final bonus to cumulative scores is
    SP_MINIGAME_WIN_BONUS / SECOND_BONUS regardless of these per-fire
    points, which only drive the ranking."""
    if mg["flavor"] == "BULLSEYE":
        if not quadrant or quadrant not in ("A", "B", "C", "D"):
            return 0
        duration_ms = mg["duration_s"] * 1000.0
        if t_ms < 0 or t_ms > duration_ms:
            return 0
        if quadrant != mg["target_quadrant"]:
            return 0
        # Faster fires score higher: 1000 at t=0, linear decay to 100
        # at t=duration. Sub-100 floor so even slow correct fires beat
        # any wrong-quadrant fire.
        return int(max(100, 1000 - (t_ms / duration_ms) * 900))
    # SHOT_CLOCK: sweep modulo cycle. Green zone is centered.
    cycle_ms = mg["cycle_ms"] or SP_SHOTCLOCK_CYCLE_MS
    pos = (t_ms % cycle_ms) / cycle_ms  # 0..1
    # Green band centered on 0.5 with width green_frac.
    half_width = (mg["green_frac"] or SP_SHOTCLOCK_GREEN_FRAC) / 2.0
    distance = abs(pos - 0.5)
    if distance > half_width:
        return 0
    # 1000 at center, linear decay to ~50 at edge.
    return int(max(50, 1000 - (distance / half_width) * 950))


def _resolve_minigame(state: dict, session_code: str, *, force: bool = False) -> bool:
    """If every expected puck has fired (or `force=True` for deadline
    expiry), award bonuses and emit minigame_winner. Returns True if
    resolved now."""
    mg = state.get("pending_minigame")
    if not mg:
        return False
    expected = state.get("expected_pucks") or set()
    fires = mg.get("fires") or {}
    if not force and expected and not all(pid in fires for pid in expected):
        return False
    # Fill non-firing pucks as zero-point fires.
    for pid in expected:
        if pid not in fires:
            fires[pid] = {"t_ms": None, "quadrant": None, "points": 0}
    # Rank by points descending, ties broken by lowest puck_id (same
    # policy as _maybe_emit_reveal — see comment near line 942).
    ranked = sorted(
        fires.items(),
        key=lambda kv: (-int(kv[1]["points"]), int(kv[0])),
    )
    # Bonus to cumulative_scores: 500 to #1 (if they scored > 0), 200
    # to #2 (if they scored > 0).
    awarded = {}
    if ranked and ranked[0][1]["points"] > 0:
        winner_pid = ranked[0][0]
        state["cumulative_scores"][winner_pid] = (
            state["cumulative_scores"].get(winner_pid, 0) + SP_MINIGAME_WIN_BONUS
        )
        awarded[winner_pid] = SP_MINIGAME_WIN_BONUS
        # Slice E3 — grant a random power-up to the minigame winner.
        # 3 minigames per match = up to 3 power-ups granted.
        _grant_power_up(state, session_code, winner_pid)
    if len(ranked) > 1 and ranked[1][1]["points"] > 0:
        second_pid = ranked[1][0]
        state["cumulative_scores"][second_pid] = (
            state["cumulative_scores"].get(second_pid, 0) + SP_MINIGAME_SECOND_BONUS
        )
        awarded[second_pid] = SP_MINIGAME_SECOND_BONUS
    # Build results payload for the TV.
    results = [
        {
            "puck_id": pid,
            "t_ms": f.get("t_ms"),
            "quadrant": f.get("quadrant"),
            "points": int(f.get("points", 0)),
            "bonus": int(awarded.get(pid, 0)),
            "cumulative_total": state["cumulative_scores"].get(pid, 0),
        }
        for pid, f in ranked
    ]
    if _socketio is not None:
        _socketio.emit(
            "minigame_winner",
            {
                "session_code": session_code,
                "flavor": mg["flavor"],
                "target_quadrant": mg.get("target_quadrant"),
                "results": results,
            },
            room=session_code,
        )
    state["minigame_resolved_round"] = state["round"] + 1
    state["pending_minigame"] = None
    return True


def _maybe_auto_resolve_minigame(state: dict, session_code: str) -> bool:
    """Force-resolve a minigame if past its deadline."""
    mg = state.get("pending_minigame")
    if not mg:
        return False
    if _now() < mg.get("deadline_at", 0):
        return False
    return _resolve_minigame(state, session_code, force=True)


def _difficulty_for_round(r: int) -> str:
    if r <= 2:
        return "easy"
    if r <= 5:
        return "medium"
    return "hard"


def _narration_url(question_id: int) -> str:
    """Canonical narration MP3 path for a question. Appends ?v=<mtime>
    when the file exists so the browser cache invalidates immediately
    after a regen (otherwise the TV keeps playing the previous voice).
    The file may not exist on disk (TTS generation is a separate
    content task); the TV treats a 404 as 'no narration', shows the
    question silently, and falls back to procedural SFX."""
    import os
    rel = f"/static/games/speed-pyramid/audio/questions/q_{question_id}.mp3"
    abs_path = os.path.join(
        os.path.dirname(__file__),
        "static",
        "games",
        "speed-pyramid",
        "audio",
        "questions",
        f"q_{question_id}.mp3",
    )
    try:
        return f"{rel}?v={int(os.path.getmtime(abs_path))}"
    except OSError:
        return rel


_NARRATED_QIDS_CACHE: set | None = None


def _narrated_qids() -> set:
    """Set of question ids that have a narration MP3 on disk. Cached at
    first use (narration files are static content; a server restart picks
    up newly generated ones)."""
    global _NARRATED_QIDS_CACHE
    if _NARRATED_QIDS_CACHE is None:
        import os
        import glob
        d = os.path.join(
            os.path.dirname(__file__),
            "static", "games", "speed-pyramid", "audio", "questions",
        )
        ids = set()
        for p in glob.glob(os.path.join(d, "q_*.mp3")):
            try:
                ids.add(int(os.path.basename(p)[2:-4]))
            except ValueError:
                pass
        _NARRATED_QIDS_CACHE = ids
    return _NARRATED_QIDS_CACHE


def _has_narration(question_id: int) -> bool:
    try:
        return int(question_id) in _narrated_qids()
    except (TypeError, ValueError):
        return False


@sp_bp.route("/load-question/<session_code>", methods=["POST"])
def sp_load_question(session_code: str):
    state = _sp_state_for(session_code)

    # R026: the match completes only once the FINAL round's question has
    # been revealed — not the instant round hits SP_TOTAL_ROUNDS. Q7 loads
    # with round==7 but is still unanswered; a second load-question call
    # while Q7 is active (e.g. the pick-timeout kick advances to Q7, then
    # QuestionScreen mounts and re-issues load-question) must return the
    # active Q7, not end the match. Otherwise the final question is skipped
    # and the scoreboard shows X/7 after only 6 questions were asked.
    _cur_qid_final = state.get("current_question_id")
    _final_revealed = (
        _cur_qid_final is None
        or state.get("revealed_for_question_id") == _cur_qid_final
    )
    if state["round"] >= SP_TOTAL_ROUNDS and _final_revealed:
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

    # Slice E2 — minigame phase. Fires BEFORE rounds 2/4/6. Runs
    # after the pick phase (rounds 1/3/5/7 get picks; 2/4/6 get
    # minigames) and is gated by minigame_resolved_round so it
    # doesn't re-fire on retries.
    next_round = state["round"] + 1
    mg_pending = state.get("pending_minigame")
    # Don't open a pick/minigame phase if there's an outstanding
    # unrevealed question — the previous round needs to finish first.
    # This guards against a TV reload mid-question accidentally
    # triggering the next-round phase early.
    cur_qid_local = state.get("current_question_id")
    ready_for_next_phase = (
        cur_qid_local is None
        or state.get("revealed_for_question_id") == cur_qid_local
    )
    if (ready_for_next_phase
            and next_round in SP_MINIGAME_ROUNDS
            and state.get("minigame_resolved_round") != next_round):
        if mg_pending:
            # Auto-resolve on deadline, then fall through to the
            # question advance.
            if _maybe_auto_resolve_minigame(state, session_code):
                mg_pending = None
            else:
                return jsonify({
                    "phase": "minigame",
                    "flavor": mg_pending["flavor"],
                    "duration_s": mg_pending["duration_s"],
                    "target_quadrant": mg_pending.get("target_quadrant"),
                    "cycle_ms": mg_pending.get("cycle_ms"),
                    "green_frac": mg_pending.get("green_frac"),
                    "started_at": mg_pending["started_at"],
                    "deadline_at": mg_pending["deadline_at"],
                    "round": next_round,
                    "total_rounds": SP_TOTAL_ROUNDS,
                })
        else:
            mg_pending = _build_minigame_phase(state, next_round)
            state["pending_minigame"] = mg_pending
            if _socketio is not None:
                _socketio.emit(
                    "minigame_start",
                    {
                        "session_code": session_code,
                        "flavor": mg_pending["flavor"],
                        "duration_s": mg_pending["duration_s"],
                        "target_quadrant": mg_pending.get("target_quadrant"),
                        "cycle_ms": mg_pending.get("cycle_ms"),
                        "green_frac": mg_pending.get("green_frac"),
                        "started_at": mg_pending["started_at"],
                        "deadline_at": mg_pending["deadline_at"],
                        "round": next_round,
                    },
                    room=session_code,
                )
            return jsonify({
                "phase": "minigame",
                "flavor": mg_pending["flavor"],
                "duration_s": mg_pending["duration_s"],
                "target_quadrant": mg_pending.get("target_quadrant"),
                "cycle_ms": mg_pending.get("cycle_ms"),
                "green_frac": mg_pending.get("green_frac"),
                "started_at": mg_pending["started_at"],
                "deadline_at": mg_pending["deadline_at"],
                "round": next_round,
                "total_rounds": SP_TOTAL_ROUNDS,
            })

    # Slice E1 — category pick phase.
    # Before each pick-round (state["round"]+1 in SP_PICK_ROUNDS), the
    # winner of the previous question round picks a category from a
    # random offer. The pick phase blocks the question advance until
    # /api/sp/select-category is called OR the 10-second deadline
    # expires (auto-default to the first offer).
    # next_round and ready_for_next_phase already computed above.
    pp = state.get("pending_category_pick")
    if (ready_for_next_phase
            and next_round in SP_PICK_ROUNDS
            and state.get("next_category_id") is None):
        if pp:
            # Auto-resolve if the picker missed the deadline. Then fall
            # through to the question advance using the defaulted
            # next_category_id.
            if _maybe_auto_resolve_pick(state):
                pp = None
            else:
                # Still pending — re-emit so reconnecting clients can
                # rejoin the pick screen, and return the phase payload.
                return jsonify({
                    "phase": "category_pick",
                    "picker_puck_id": pp["picker_puck_id"],
                    "offer": pp["offer"],
                    "deadline_at": pp["deadline_at"],
                    "started_at": pp["started_at"],
                    "round": next_round,
                    "total_rounds": SP_TOTAL_ROUNDS,
                })
        else:
            # Open a new pick phase.
            pp = _build_pick_offer(state, next_round)
            state["pending_category_pick"] = pp
            if _socketio is not None:
                _socketio.emit(
                    "category_offer",
                    {
                        "session_code": session_code,
                        "picker_puck_id": pp["picker_puck_id"],
                        "offer": pp["offer"],
                        "deadline_at": pp["deadline_at"],
                        "started_at": pp["started_at"],
                        "round": next_round,
                    },
                    room=session_code,
                )
            return jsonify({
                "phase": "category_pick",
                "picker_puck_id": pp["picker_puck_id"],
                "offer": pp["offer"],
                "deadline_at": pp["deadline_at"],
                "started_at": pp["started_at"],
                "round": next_round,
                "total_rounds": SP_TOTAL_ROUNDS,
            })

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
    # Slice E1: if a category was picked in the preceding pick phase,
    # filter the random draw to that category. Consume the field so
    # subsequent rounds don't keep using the same category until the
    # next pick fires.
    forced_category_id = state.get("next_category_id")
    state["next_category_id"] = None
    if forced_category_id is not None:
        q = get_random_question(
            difficulty=difficulty,
            exclude_ids=exclude,
            category_id=forced_category_id,
        )
        if not q:
            # Out of questions at this difficulty for that category —
            # try any difficulty.
            q = get_random_question(
                exclude_ids=exclude,
                category_id=forced_category_id,
            )
    else:
        q = get_random_question(difficulty=difficulty, exclude_ids=exclude)
    if not q:
        q = get_random_question(exclude_ids=exclude)
    if not q:
        return jsonify({"error": "no questions available"}), 404

    # R027: prefer a question that actually has a narration MP3. 116 of
    # 1296 questions lack one and 404, leaving the host silent. Re-draw a
    # few times (keeping the picked category, relaxing difficulty to widen
    # the pool) until we land on a narrated question. Falls back to the
    # original pick if a category is mostly un-narrated (TV handles 404).
    if q and not _has_narration(q["id"]):
        tried = set(exclude or [])
        tried.add(q["id"])
        for _ in range(12):
            alt = get_random_question(
                exclude_ids=list(tried),
                category_id=forced_category_id,
            )
            if not alt:
                break
            if _has_narration(alt["id"]):
                q = alt
                break
            tried.add(alt["id"])

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
    # Slice E1: surface the pending category pick so polling pucks
    # transition into CATEGORY_PICKING without needing to POST
    # load-question (load-question advances state; pucks must remain
    # read-only against round transitions per ADR-0002).
    pp = state.get("pending_category_pick")
    pick_payload = None
    if pp:
        pick_payload = {
            "picker_puck_id": pp["picker_puck_id"],
            "offer": pp["offer"],
            "deadline_at": pp["deadline_at"],
            "started_at": pp["started_at"],
        }
    # Slice E2: same idea for the minigame phase.
    mg = state.get("pending_minigame")
    mg_payload = None
    if mg:
        mg_payload = {
            "flavor": mg["flavor"],
            "duration_s": mg["duration_s"],
            "target_quadrant": mg.get("target_quadrant"),
            "cycle_ms": mg.get("cycle_ms"),
            "green_frac": mg.get("green_frac"),
            "started_at": mg["started_at"],
            "deadline_at": mg["deadline_at"],
        }
    return jsonify(
        {
            "exists": True,
            "round": state["round"],
            "total_rounds": SP_TOTAL_ROUNDS,
            "questions_asked": len(state["asked_ids"]),
            "complete": bool(state.get("complete", False)),
            "pending_category_pick": pick_payload,
            "pending_minigame": mg_payload,
            # Slice E3 — per-puck inventories so the Hub HUD + the
            # firmware can render available power-ups without a
            # separate /inventory call per puck per tick.
            "power_up_inventories": {
                str(pid): list(items)
                for pid, items in state.get("power_up_inventories", {}).items()
            },
            # R029: surface the authoritative running totals (minigame
            # bonuses + power-up effects applied) so the final scoreboard
            # can be reconciled against what the reveal sidebar shows.
            "cumulative_scores": {
                str(pid): int(score)
                for pid, score in state.get("cumulative_scores", {}).items()
            },
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
                   SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) AS correct,
                   COALESCE(SUM(response_time_ms), 0) AS sum_response_ms,
                   COALESCE(AVG(response_time_ms), 0) AS avg_response_ms
              FROM trivia_answers
             WHERE session_id = {ph}
             GROUP BY puck_id""",
        (session["id"],),
        fetch_all=True,
    ) or []

    def derive_tier(total: int, answered: int) -> str:
        # Average over ROUNDS PLAYED, not the count of answered DB rows.
        # A timed-out round writes no trivia_answers row while a wrong
        # answer does, so dividing by `answered` makes the tier depend on
        # HOW non-scoring rounds failed rather than on real performance.
        rounds_played = SP_TOTAL_ROUNDS
        if rounds_played == 0:
            return "NONE"
        avg = total / rounds_played
        if avg >= 700:
            return "LEGENDARY"
        if avg >= 400:
            return "EXPERT"
        if avg >= 150:
            return "AVERAGE"
        return "TIMEOUT"

    state = _SP_STATE.get(session_code, {})

    # R029: trivia_answers only ever holds RAW pre-power-up points written
    # at sp_answer time. Minigame bonuses (+500/+200) and the DOUBLE /
    # REVEAL / STEAL effects applied in _apply_power_up_arms mutate ONLY
    # state["cumulative_scores"] in memory and are never written back to
    # the DB. The in-match reveal sidebar renders cumulative_scores, so the
    # final scoreboard must use the SAME authoritative source — otherwise a
    # puck that won the minigames or doubled a round shows a lower total
    # (or even a different winner) than players watched accumulate. When
    # in-memory state exists, take `total` from cumulative_scores; the DB
    # sum still drives answered/correct counts and stays the fallback when
    # state was wiped. Pucks with cumulative score but zero DB rows (timed
    # out every question, won the minigame) must still appear.
    cumulative = state.get("cumulative_scores") or {}
    db_by_puck = {int(r["puck_id"]): r for r in rows}
    puck_ids = sorted(set(db_by_puck) | {int(p) for p in cumulative})

    def _total_for(pid: int) -> int:
        if pid in cumulative:
            return int(cumulative[pid])
        r = db_by_puck.get(pid)
        return int(r["total"] or 0) if r else 0

    players = []
    for pid in puck_ids:
        r = db_by_puck.get(pid)
        answered = int(r["answered"] or 0) if r else 0
        correct = int(r["correct"] or 0) if r else 0
        total = _total_for(pid)
        # R040: surface aggregate response times so the final scoreboard can
        # break a points tie deterministically instead of relying on V8 sort
        # order. trivia_answers carries response_time_ms per locked answer;
        # the SUM/AVG aggregate is the documented secondary key (faster wins).
        sum_response_ms = int(r["sum_response_ms"] or 0) if r else 0
        avg_response_ms = int(round(float(r["avg_response_ms"] or 0))) if r else 0
        players.append(
            {
                "puck_id": pid,
                "total": total,
                "answered": answered,
                "correct": correct,
                "tier": derive_tier(total, answered),
                "color": _color_for(pid)[0],
                "color_name": _color_for(pid)[1],
                "sum_response_time_ms": sum_response_ms,
                "avg_response_ms": avg_response_ms,
            }
        )

    # R040: compute the authoritative final standing server-side so every
    # client renders the SAME deterministic order. Documented tie-break:
    # higher total -> faster (smaller) aggregate response time -> lowest
    # puck_id. Rank is dense from 1; is_winner crowns ALL co-leaders that
    # share the top total (so a genuine total tie crowns both, never one
    # arbitrary puck), with the response-time tie-break still ordering rank.
    players.sort(
        key=lambda p: (
            -int(p["total"]),
            int(p["sum_response_time_ms"]),
            int(p["puck_id"]),
        )
    )
    top_total = int(players[0]["total"]) if players else 0
    for i, p in enumerate(players):
        p["rank"] = i + 1
        p["is_winner"] = int(p["total"]) == top_total and top_total > 0

    return jsonify(
        {
            "session_code": session_code,
            "round": state.get("round", SP_TOTAL_ROUNDS),
            "total_rounds": SP_TOTAL_ROUNDS,
            "players": players,
        }
    )


@sp_bp.route("/reset/<session_code>", methods=["POST"])
def sp_reset(session_code: str):
    # Play-Again reuses the SAME trivia_sessions row, so the prior match's
    # trivia_answers rows must be cleared. final-results aggregates
    # trivia_answers filtered only by session_id; leaving the old rows in
    # place SUMs match-1 + match-2 (answered can exceed total_rounds, totals
    # inflated, tiers wrong). Drop them — and zero the cached per-player
    # score — so the replay starts from a clean slate.
    ph = get_placeholder()
    session = execute_query(
        f"SELECT id FROM trivia_sessions WHERE session_code = {ph}",
        (session_code,),
        fetch_one=True,
    )
    if session:
        sid = session["id"]
        execute_query(
            f"DELETE FROM trivia_answers WHERE session_id = {ph}", (sid,)
        )
        execute_query(
            f"UPDATE trivia_session_players SET total_score = 0 "
            f"WHERE session_id = {ph}",
            (sid,),
        )
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

    # Slice E3 — apply armed power-up effects BEFORE cumulative
    # scoring so DOUBLE / REVEAL adjust the per-round points the
    # client sees in the reveal payload AND the running total. STEAL
    # transfers happen inside this call too. One-shot per round.
    _apply_power_up_arms(state, session_code, qid, answers)

    # Update cumulative scores.
    for pid, a in answers.items():
        state["cumulative_scores"][pid] = state["cumulative_scores"].get(pid, 0) + int(a["points"])

    # Slice E1: track this round's winner. Speed Pyramid scoring is
    # tier-based (LEGENDARY/EXPERT/AVERAGE in 3s bands), so two pucks
    # in the same band get IDENTICAL points. Without a secondary
    # sort, the next picker is picked by puck_id ascending, which
    # feels arbitrary. Real tie-break: faster response_time_ms wins.
    # Rounds where nobody earned points fall back to the lowest
    # expected puck_id (set in _build_pick_offer).
    best_pid, best_pts, best_rt = None, -1, 10**9
    for pid, a in answers.items():
        pts = int(a["points"])
        rt = a.get("response_time_ms")
        rt_val = int(rt) if rt is not None else 10**9
        better = (
            pts > best_pts
            or (pts == best_pts and rt_val < best_rt)
            or (pts == best_pts and rt_val == best_rt and (best_pid is None or pid < best_pid))
        )
        if better:
            best_pid, best_pts, best_rt = pid, pts, rt_val
    if best_pid is not None and best_pts > 0:
        state["last_round_winner_puck_id"] = best_pid
    else:
        # Wipeout round (everyone wrong/timed out, 0 pts): clear the
        # stale winner so the next pick falls back to the lowest
        # expected puck_id in _build_pick_offer, per the policy above.
        state["last_round_winner_puck_id"] = None

    # Reveal payload is sorted by puck_id ascending. This is the TIE-
    # BREAKER policy: when two pucks earn the same points in a round
    # (same tier, same answer correctness), the lower-numbered puck
    # appears first in the reveal feed and the scoreboard sidebar. The
    # ordering is deterministic but arbitrary; it's not based on
    # response_time_ms because Speed Pyramid's scoring already encodes
    # response time inside the tier bands (LEGENDARY 0-3s vs EXPERT
    # 3-6s etc.), so identical tier + identical correctness is treated
    # as a true tie at the per-round level. Final scoreboard sort by
    # cumulative `total` (ScoreboardScreen.tsx) is the authoritative
    # ranking; this only affects the per-question reveal order.
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


@sp_bp.route("/minigame/state/<session_code>", methods=["GET"])
def sp_minigame_state(session_code: str):
    """Slice E2 — return current minigame state for late-joiners.
    Returns 200 with {active: false} when no minigame is pending."""
    state = _SP_STATE.get(session_code)
    if not state:
        return jsonify({"active": False})
    mg = state.get("pending_minigame")
    if not mg:
        return jsonify({"active": False})
    return jsonify({
        "active": True,
        "flavor": mg["flavor"],
        "duration_s": mg["duration_s"],
        "target_quadrant": mg.get("target_quadrant"),
        "cycle_ms": mg.get("cycle_ms"),
        "green_frac": mg.get("green_frac"),
        "started_at": mg["started_at"],
        "deadline_at": mg["deadline_at"],
        "fires": mg.get("fires") or {},
    })


@sp_bp.route("/inventory/<session_code>", methods=["GET"])
def sp_inventory(session_code: str):
    """Slice E3 — return power-up inventory for a puck.
    Query param: puck_id. Empty list if no session."""
    try:
        puck_id = int(request.args.get("puck_id"))
    except (TypeError, ValueError):
        return jsonify({"items": []}), 400
    state = _SP_STATE.get(session_code)
    if state is None:
        return jsonify({"items": []})
    items = list(state.get("power_up_inventories", {}).get(puck_id, []))
    return jsonify({"items": items, "puck_id": puck_id})


@sp_bp.route("/power-up/activate", methods=["POST"])
def sp_power_up_activate():
    """Slice E3 — activate a power-up between rounds.

    Body: {session_code, puck_id, item_id, target_puck_id?}.
    Only valid during a pick or minigame phase (i.e., between
    rounds). Removes the item from inventory and arms its effect
    for the NEXT question's reveal. STEAL requires a target_puck_id.

    Returns 409 if not in a between-rounds phase, 404 if item not
    found in inventory, 400 if STEAL missing target.
    """
    data = request.get_json(silent=True) or {}
    try:
        sc = str(data["session_code"])
        puck_id = int(data["puck_id"])
        item_id = str(data["item_id"])
    except (KeyError, TypeError, ValueError):
        return jsonify({"ok": False, "reason": "bad payload"}), 400
    target_puck_id = data.get("target_puck_id")
    state = _SP_STATE.get(sc)
    if state is None:
        return jsonify({"ok": False, "reason": "no session"}), 404
    # Gate: must be between rounds (pick or minigame pending). This
    # keeps activation off the mid-question critical path.
    if not (state.get("pending_category_pick") or state.get("pending_minigame")):
        return jsonify({"ok": False, "reason": "not between rounds"}), 409
    inv = state["power_up_inventories"].setdefault(puck_id, [])
    item = next((it for it in inv if it["id"] == item_id), None)
    if item is None:
        return jsonify({"ok": False, "reason": "item not in inventory"}), 404
    item_type = item["type"]
    if item_type == "STEAL":
        if target_puck_id is None:
            return jsonify({"ok": False, "reason": "STEAL needs target_puck_id"}), 400
        try:
            target_puck_id = int(target_puck_id)
        except (TypeError, ValueError):
            return jsonify({"ok": False, "reason": "bad target_puck_id"}), 400
        # Target must be a real participant other than the firer. A
        # phantom id no-ops at reveal (item lost for zero effect) and a
        # self-steal emits a bogus firer==target resolution; reject both
        # WITHOUT consuming the one-shot item.
        expected = state.get("expected_pucks") or set()
        if target_puck_id == puck_id or target_puck_id not in expected:
            return jsonify({"ok": False, "reason": "invalid target"}), 400
        target_arms = state["power_up_arms"].setdefault(target_puck_id, _empty_arms())
        target_arms.setdefault("incoming_steals", []).append(puck_id)
    elif item_type == "DOUBLE":
        state["power_up_arms"].setdefault(puck_id, _empty_arms())["double"] = True
    elif item_type == "REVEAL":
        state["power_up_arms"].setdefault(puck_id, _empty_arms())["reveal"] = True
    elif item_type == "SHIELD":
        state["power_up_arms"].setdefault(puck_id, _empty_arms())["shield"] = True
    # Remove from inventory (one-shot).
    inv.remove(item)
    if _socketio is not None:
        _socketio.emit(
            "power_up_used",
            {
                "session_code": sc,
                "puck_id": puck_id,
                "item_id": item_id,
                "type": item_type,
                "target_puck_id": target_puck_id,
            },
            room=sc,
        )
        _socketio.emit(
            "inventory_updated",
            {"session_code": sc, "puck_id": puck_id, "items": list(inv)},
            room=sc,
        )
    return jsonify({"ok": True, "type": item_type,
                    "target_puck_id": target_puck_id})


@sp_bp.route("/minigame/preview", methods=["POST"])
def sp_minigame_preview():
    """Slice F — broadcast a puck's aim quadrant during BULLSEYE.
    Body: {session_code, puck_id, quadrant?}. No-ops if no minigame
    pending. The TV's MinigameScreen subscribes to
    minigame_aim_preview and renders a faint per-puck reticle on the
    target board so players see where they're aiming before they
    tap. Mirrors pair_dial_preview."""
    data = request.get_json(silent=True) or {}
    try:
        sc = str(data["session_code"])
        pid = int(data["puck_id"])
    except (KeyError, TypeError, ValueError):
        return jsonify({"ok": False}), 400
    quadrant = data.get("quadrant")
    state = _SP_STATE.get(sc)
    if state is None or not state.get("pending_minigame"):
        return jsonify({"ok": True, "noop": True})
    if _socketio is not None:
        _socketio.emit(
            "minigame_aim_preview",
            {"session_code": sc, "puck_id": pid, "quadrant": quadrant},
            room=sc,
        )
    return jsonify({"ok": True})


@sp_bp.route("/minigame/fire", methods=["POST"])
def sp_minigame_fire():
    """Slice E2 — record one puck's fire in the active minigame.
    Body: {session_code, puck_id, t_ms, quadrant?}. Resolves the
    minigame if every expected puck has now fired. Emits
    minigame_fire socket so the TV can render per-puck markers as
    they land."""
    data = request.get_json(silent=True) or {}
    try:
        sc = str(data["session_code"])
        pid = int(data["puck_id"])
        t_ms = int(data.get("t_ms") or 0)
    except (KeyError, TypeError, ValueError):
        return jsonify({"ok": False, "reason": "bad payload"}), 400
    quadrant = data.get("quadrant")
    state = _SP_STATE.get(sc)
    if state is None:
        return jsonify({"ok": False, "reason": "no session"}), 404
    mg = state.get("pending_minigame")
    if not mg:
        return jsonify({"ok": False, "reason": "no pending minigame"}), 409
    if pid in (mg.get("fires") or {}):
        # Idempotent: already fired. Return current points.
        return jsonify({"ok": True, "already": True,
                        "points": int(mg["fires"][pid]["points"])})
    points = _score_minigame_fire(mg, t_ms, quadrant)
    mg.setdefault("fires", {})[pid] = {
        "t_ms": t_ms,
        "quadrant": quadrant,
        "points": points,
    }
    if _socketio is not None:
        _socketio.emit(
            "minigame_fire",
            {
                "session_code": sc,
                "puck_id": pid,
                "t_ms": t_ms,
                "quadrant": quadrant,
                "points": points,
            },
            room=sc,
        )
    # Resolve immediately if every expected puck has now fired.
    emitted = _resolve_minigame(state, sc)
    return jsonify({"ok": True, "points": points, "resolved": emitted})


@sp_bp.route("/minigame/finish/<session_code>", methods=["POST"])
def sp_minigame_finish(session_code: str):
    """Slice E2 — TV-side belt-and-suspenders. Forces resolution at
    the deadline so a missed puck fire doesn't strand the match."""
    state = _SP_STATE.get(session_code)
    if state is None:
        return jsonify({"ok": False, "reason": "no session"}), 404
    if not state.get("pending_minigame"):
        return jsonify({"ok": True, "noop": True})
    emitted = _resolve_minigame(state, session_code, force=True)
    return jsonify({"ok": True, "emitted": emitted})


@sp_bp.route("/select-category/<session_code>", methods=["POST"])
def sp_select_category(session_code: str):
    """Slice E1 — picker locks a category from the pending offer.

    Body: {puck_id, category_id}. Validates that puck_id matches the
    designated picker and category_id is in the current offer. On
    success: stash next_category_id, clear pending_category_pick,
    emit category_picked socket. The next /api/sp/load-question call
    consumes next_category_id to filter the question draw."""
    data = request.get_json(silent=True) or {}
    try:
        puck_id = int(data.get("puck_id"))
        category_id = int(data.get("category_id"))
    except (TypeError, ValueError):
        return jsonify({"ok": False, "reason": "bad puck_id/category_id"}), 400
    state = _SP_STATE.get(session_code)
    if state is None:
        return jsonify({"ok": False, "reason": "no session"}), 404
    pp = state.get("pending_category_pick")
    if not pp:
        return jsonify({"ok": False, "reason": "no pending pick"}), 409
    if puck_id != pp["picker_puck_id"]:
        return jsonify({"ok": False, "reason": "not the picker"}), 403
    valid_ids = {int(o["id"]) for o in pp.get("offer") or []}
    if category_id not in valid_ids:
        return jsonify({"ok": False, "reason": "category not in offer"}), 400
    state["next_category_id"] = category_id
    state["pending_category_pick"] = None
    if _socketio is not None:
        _socketio.emit(
            "category_picked",
            {
                "session_code": session_code,
                "picker_puck_id": puck_id,
                "category_id": category_id,
            },
            room=session_code,
        )
    return jsonify({"ok": True, "category_id": category_id})


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
    # Slice E1/E2: same rationale for pending-pick / pending-minigame
    # phases. Until the phase resolves and the next question loads,
    # there is no active question to point pucks at — they must
    # transition through CATEGORY_PICKING / MINIGAME and back to IDLE,
    # not stay pinned on the prior round's revealed question.
    if state is not None and (
        state.get("pending_category_pick") or state.get("pending_minigame")
    ):
        return jsonify({"active": False})
    # Also: if the previous question has been revealed and we're
    # between rounds (no new question loaded yet), there's nothing
    # active. The cached _QUESTION_TRACKER entry is stale once
    # revealed_for_question_id matches; only the next sp_load_question
    # call advances state to the next question.
    if state is not None and state.get("current_question_id") is not None and (
        state.get("revealed_for_question_id") == state.get("current_question_id")
    ):
        return jsonify({"active": False})

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
