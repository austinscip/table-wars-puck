"""Slice I — crash-recovery state persistence.

The Speed Pyramid in-memory state (`_LOBBY`, `_SP_STATE`,
`_QUESTION_TRACKER` in `pair_routes.py`) is volatile: Flask restart =
total loss. A bar deployment cannot tolerate that — a mid-match crash
strands the pucks on a dead session and the bar staff has to power-cycle
everything. This module gives the routes a `snapshot(...)` they can call
on every mutation and a `rehydrate(...)` Flask calls on boot.

Design choices (kept deliberately small):
- JSON dump at `server/state_snapshot.json`. SQLite would let us
  capture history but Slice I only needs LAST-WRITE-WINS, and JSON is
  trivially debug-readable. If multi-snapshot history is ever wanted
  rotate via `snapshot_<ts>.json` (out of scope).
- Debounced background writer: each `snapshot()` call just bumps a
  dirty flag + condition variable; a daemon thread coalesces writes
  to <= 1 per `DEBOUNCE_MS`. Without debounce a single user action can
  fire 8+ mutations (lobby join + state init + first load-question +
  round advance + ...) and we'd hit the disk on each.
- Atomic write via tmp-file + rename. Half-written JSON on `kill -9`
  must NOT corrupt the next boot.
- `set` fields (`asked_ids`) round-trip through `list` in JSON; the
  rehydrate side coerces back. Same for int-keyed dicts (JSON forces
  string keys).
- Optional: set `SP_PERSIST_DISABLE=1` to skip all persistence (CI,
  test runs that don't want disk artifacts).
"""
from __future__ import annotations

import json
import os
import sys
import threading
import time
from pathlib import Path
from typing import Any, Callable

DEBOUNCE_MS = 250
_SERVER_DIR = Path(__file__).resolve().parent
DEFAULT_PATH = _SERVER_DIR / "state_snapshot.json"

# These will be filled by `bind(...)` so the writer thread can read live
# state without circular imports.
_get_lobby: Callable[[], dict | None] | None = None
_get_sp_state: Callable[[], dict[str, dict]] | None = None
_get_question_tracker: Callable[[], dict[str, dict]] | None = None

_lock = threading.Lock()
_cv = threading.Condition(_lock)
_dirty = False
_running = False
_path: Path = DEFAULT_PATH


def _coerce_for_json(o: Any) -> Any:
    """Recursively coerce sets -> sorted lists, int-keyed dicts kept
    (json's default coerces those to str keys which we re-coerce on
    load). Everything else stays."""
    if isinstance(o, set):
        return {"__set__": sorted(list(o))}
    if isinstance(o, dict):
        return {str(k): _coerce_for_json(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_coerce_for_json(x) for x in o]
    return o


def _restore_from_json(o: Any) -> Any:
    """Reverse of _coerce_for_json. set sentinels become sets again."""
    if isinstance(o, dict):
        if "__set__" in o and len(o) == 1:
            return set(o["__set__"])
        return {k: _restore_from_json(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_restore_from_json(x) for x in o]
    return o


def _int_keys(d: dict, target_keys: tuple[str, ...] = ()) -> dict:
    """JSON forces string keys; this re-coerces dict keys to int where
    the original code expects int (puck_id, etc.). Called on specific
    sub-dicts during rehydrate so we don't blindly int-coerce every
    string key in the tree."""
    out = {}
    for k, v in d.items():
        try:
            out[int(k)] = v
        except (TypeError, ValueError):
            out[k] = v
    return out


def bind(get_lobby: Callable[[], dict | None],
         get_sp_state: Callable[[], dict[str, dict]],
         get_question_tracker: Callable[[], dict[str, dict]],
         path: Path | str | None = None) -> None:
    """Called once by pair_routes after module load so the writer
    thread can read live state."""
    global _get_lobby, _get_sp_state, _get_question_tracker, _path
    _get_lobby = get_lobby
    _get_sp_state = get_sp_state
    _get_question_tracker = get_question_tracker
    if path is not None:
        _path = Path(path)


def snapshot() -> None:
    """Mark state dirty. The writer thread coalesces and flushes."""
    if os.environ.get("SP_PERSIST_DISABLE") == "1":
        return
    global _dirty
    with _cv:
        _dirty = True
        _cv.notify()


def _serialize() -> dict:
    """Build the JSON payload from current live state. Called inside
    the writer thread with the GIL guarding atomicity of dict reads."""
    if _get_lobby is None or _get_sp_state is None \
            or _get_question_tracker is None:
        return {"_unbound": True}
    return {
        "v": 1,
        "lobby": _coerce_for_json(_get_lobby()),
        "sp_state": _coerce_for_json(_get_sp_state()),
        "question_tracker": _coerce_for_json(_get_question_tracker()),
        "saved_at": time.time(),
    }


def _atomic_write(payload: dict) -> None:
    tmp = _path.with_suffix(".json.tmp")
    try:
        with open(tmp, "w") as f:
            json.dump(payload, f)
        os.replace(tmp, _path)
    except Exception as e:  # noqa: BLE001 — log and continue
        print(f"[state_persistence] write failed: {e}", file=sys.stderr)


def _writer_loop() -> None:
    global _dirty
    while _running:
        with _cv:
            while not _dirty and _running:
                _cv.wait(timeout=1.0)
            if not _running:
                return
            # Coalesce: clear the flag, debounce, then flush.
            _dirty = False
        time.sleep(DEBOUNCE_MS / 1000.0)
        # If new mutations arrived during debounce, they re-set the flag
        # — but we still want to flush the CURRENT view. Re-flush again
        # on next iteration if dirty again. Simple last-write-wins.
        try:
            payload = _serialize()
            _atomic_write(payload)
        except Exception as e:  # noqa: BLE001
            print(f"[state_persistence] serialize failed: {e}",
                  file=sys.stderr)


def start_writer() -> None:
    """Start the background writer thread once. Safe to call multiple
    times; only the first call actually starts the thread."""
    global _running
    if os.environ.get("SP_PERSIST_DISABLE") == "1":
        return
    if _running:
        return
    _running = True
    t = threading.Thread(target=_writer_loop, name="state-persist",
                         daemon=True)
    t.start()


def rehydrate() -> dict | None:
    """Read the snapshot file (if any) and return the parsed dict. The
    caller (pair_routes) is responsible for restoring the dicts into
    their module globals — we don't reach in, because import order +
    test isolation is easier when the caller owns the assignment."""
    if os.environ.get("SP_PERSIST_DISABLE") == "1":
        return None
    if not _path.exists():
        return None
    try:
        with open(_path) as f:
            raw = json.load(f)
    except Exception as e:  # noqa: BLE001
        print(f"[state_persistence] rehydrate read failed: {e}",
              file=sys.stderr)
        return None
    if not isinstance(raw, dict) or raw.get("v") != 1:
        return None
    return {
        "lobby": _restore_from_json(raw.get("lobby")),
        "sp_state": _restore_from_json(raw.get("sp_state") or {}),
        "question_tracker": _restore_from_json(
            raw.get("question_tracker") or {}),
        "saved_at": raw.get("saved_at"),
    }


def fix_int_keys_after_rehydrate(lobby: dict | None,
                                 sp_state: dict,
                                 question_tracker: dict) -> None:
    """Walk known int-keyed sub-dicts and re-coerce their keys to int.
    Modifies dicts in place. Touch only the specific places we know
    use int keys; blanket-int-coercion would corrupt session_codes
    (alphanumeric) used as top-level keys in _SP_STATE."""
    # _LOBBY.players: keyed by puck_id (int).
    if isinstance(lobby, dict):
        if isinstance(lobby.get("players"), dict):
            lobby["players"] = _int_keys(lobby["players"])
        if isinstance(lobby.get("dials_in_progress"), dict):
            lobby["dials_in_progress"] = _int_keys(lobby["dials_in_progress"])
        if isinstance(lobby.get("last_seen"), dict):
            lobby["last_seen"] = _int_keys(lobby["last_seen"])
    # _SP_STATE keys = session_code (strings, leave). Inner dicts have
    # int-keyed power_up_inventories / power_up_arms / cumulative_scores
    # / current_round_answers.
    for sc, st in (sp_state or {}).items():
        if not isinstance(st, dict):
            continue
        for k in ("power_up_inventories", "power_up_arms",
                  "cumulative_scores", "current_round_answers"):
            if isinstance(st.get(k), dict):
                st[k] = _int_keys(st[k])
        # expected_pucks was originally a set of int — round-tripped to
        # a set of int by _restore_from_json + the original sorted-list
        # branch. If it came back as a list (no __set__ sentinel for
        # whatever reason), coerce.
        if isinstance(st.get("expected_pucks"), list):
            st["expected_pucks"] = set(int(p) for p in st["expected_pucks"])
        # asked_ids same.
        if isinstance(st.get("asked_ids"), list):
            st["asked_ids"] = set(int(q) for q in st["asked_ids"])
