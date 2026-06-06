"""Real-flow test harness for the LIVE Speed Pyramid engine.

The deployed product runs on `pair_routes.py` + `trivia_game_engines.py` +
`trivia_session_manager.py` against a SQLite (dev) / Postgres (prod) DB. Before
the live-engine audit (live-speed-pyramid-2026-06-06) this whole path had ZERO
endpoint tests — `test_pairing.py` exercises the *next-gen runtime*
PairingManager, not these Flask blueprints.

This harness spins the real blueprints against a throwaway SQLite file so a test
can drive the actual request flow (request -> start -> load-question -> answer ->
reveal -> final-results), not a re-implementation. It:

- points `database.get_db_connection` at a temp DB,
- creates the trivia tables with SQLite-correct `INTEGER PRIMARY KEY` (the
  shipped `init_trivia_database` uses `SERIAL PRIMARY KEY`, which under SQLite
  leaves `id` NULL — fine on Postgres in prod, unusable for a deterministic
  local test), and seeds a speed_pyramid game type, a category, and a pool of
  easy/medium/hard questions,
- registers `pair_bp` + `sp_bp` on a throwaway Flask app with a recording fake
  socketio and persistence disabled,
- resets the module-global lobby/state between tests.

Skips nothing — SQLite ships with Python, so this runs everywhere the suite does.
"""
from __future__ import annotations

import contextlib
import sqlite3
from typing import Any


# Trivia schema, SQLite-correct (INTEGER PRIMARY KEY autoincrements the rowid;
# only the *exact* phrase does, which the shipped SERIAL schema misses).
_SCHEMA = """
CREATE TABLE trivia_game_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE, display_name TEXT, min_players INTEGER DEFAULT 1,
    max_players INTEGER DEFAULT 8, is_active INTEGER DEFAULT 1
);
CREATE TABLE trivia_categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE, emoji TEXT, difficulty TEXT, is_active INTEGER DEFAULT 1
);
CREATE TABLE trivia_questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id INTEGER, question_text TEXT, setup_text TEXT,
    answer_a TEXT, answer_b TEXT, answer_c TEXT, answer_d TEXT,
    correct_answer TEXT, explanation TEXT,
    host_commentary_correct TEXT, host_commentary_wrong TEXT,
    difficulty TEXT, time_limit INTEGER DEFAULT 15, is_active INTEGER DEFAULT 1,
    times_played INTEGER DEFAULT 0, times_correct INTEGER DEFAULT 0
);
CREATE TABLE trivia_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bar_id INTEGER, table_number INTEGER, game_type_id INTEGER,
    session_code TEXT UNIQUE, status TEXT DEFAULT 'waiting',
    current_round INTEGER DEFAULT 1, total_rounds INTEGER DEFAULT 7
);
CREATE TABLE trivia_session_players (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER, puck_id INTEGER, player_name TEXT,
    total_score INTEGER DEFAULT 0, multiplier REAL DEFAULT 1.0
);
CREATE TABLE trivia_answers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER, question_id INTEGER, puck_id INTEGER,
    answer_given TEXT, is_correct INTEGER, response_time_ms INTEGER,
    points_earned INTEGER DEFAULT 0, multiplier_used REAL DEFAULT 1.0
);
"""


class FakeSio:
    """Records every emit so a test can assert which sockets fired."""

    def __init__(self) -> None:
        self.emits: list[tuple[str, dict, Any]] = []

    def emit(self, event: str, data: dict | None = None, room: Any = None, **_kw) -> None:
        self.emits.append((event, data or {}, room))

    def events(self, name: str) -> list[dict]:
        return [d for e, d, _ in self.emits if e == name]


class SPHarness:
    """Bundle of the Flask test client + fake socketio + DB path, plus thin
    helpers for the common request shapes."""

    def __init__(self, client, sio: FakeSio, db_path: str) -> None:
        self.client = client
        self.sio = sio
        self.db_path = db_path
        # Per-puck capability tokens captured from pair/request + pair/confirm,
        # replayed on every state-mutating write (the server now requires them).
        self.tokens: dict[int, str] = {}

    def _capture_token(self, puck_id: int, resp):
        try:
            tok = (resp.get_json() or {}).get("token")
        except Exception:
            tok = None
        if tok:
            self.tokens[puck_id] = tok
        return resp

    # --- pairing ---
    def request_code(self, puck_id: int):
        return self._capture_token(
            puck_id,
            self.client.post("/api/pair/request", json={"puck_id": puck_id}),
        )

    def confirm(self, puck_id: int, code: str):
        return self._capture_token(
            puck_id,
            self.client.post(
                "/api/pair/confirm", json={"puck_id": puck_id, "code": code}
            ),
        )

    def start(self, puck_id: int):
        return self.client.post(
            "/api/pair/start",
            json={"puck_id": puck_id, "token": self.tokens.get(puck_id)},
        )

    def pair_full(self, puck_ids: list[int]) -> str:
        """request(host) -> request(joiners) -> confirm(host) -> start.
        Returns the session_code."""
        host = puck_ids[0]
        r = self.request_code(host)
        code = r.get_json()["pair_code"]
        for pid in puck_ids[1:]:
            self.request_code(pid)
        # Host must confirm to be added to players (joiners auto-add on request).
        self.confirm(host, code)
        sc = self.start(host).get_json()["session_code"]
        return sc

    # --- speed pyramid ---
    def load_question(self, sc: str):
        return self.client.post(f"/api/sp/load-question/{sc}")

    def answer(self, sc: str, puck_id: int, qid: int, ans: str, rt_ms: int = 1000):
        return self.client.post(
            "/api/sp/answer",
            json={
                "session_code": sc,
                "puck_id": puck_id,
                "question_id": qid,
                "answer": ans,
                "response_time_ms": rt_ms,
                "token": self.tokens.get(puck_id),
            },
        )

    def select_category(self, sc: str, puck_id: int, category_id: int):
        return self.client.post(
            f"/api/sp/select-category/{sc}",
            json={"puck_id": puck_id, "category_id": category_id,
                  "token": self.tokens.get(puck_id)},
        )

    def minigame_fire(self, sc: str, puck_id: int, t_ms: int, quadrant: str | None):
        return self.client.post(
            "/api/sp/minigame/fire",
            json={"session_code": sc, "puck_id": puck_id,
                  "t_ms": t_ms, "quadrant": quadrant,
                  "token": self.tokens.get(puck_id)},
        )

    def leave_match(self, sc: str, puck_id: int):
        return self.client.post(
            "/api/sp/leave-match",
            json={"session_code": sc, "puck_id": puck_id,
                  "token": self.tokens.get(puck_id)},
        )

    def advance_to_question(self, sc: str) -> dict:
        """Drive load-question through any pending category-pick / minigame
        phase until a real question is returned. Returns the question body.

        Resolves a pick by having the designated picker lock offer[0] (after
        backdating the offer past the 800ms stray-click guard), and a minigame
        by firing for every expected puck.
        """
        import pair_routes

        for _ in range(12):
            body = self.load_question(sc).get_json()
            phase = body.get("phase")
            if phase == "category_pick":
                st = pair_routes._SP_STATE[sc]["pending_category_pick"]
                st["started_at"] -= 5.0  # clear the 800ms anti-stray-click gate
                self.select_category(sc, body["picker_puck_id"],
                                     body["offer"][0]["id"])
                continue
            if phase == "minigame":
                expected = sorted(pair_routes._SP_STATE[sc]["expected_pucks"])
                quad = body.get("target_quadrant") or "A"
                for pid in expected:
                    self.minigame_fire(sc, pid, 0, quad)
                continue
            return body
        raise AssertionError("advance_to_question did not reach a question")

    def force_reveal(self, sc: str):
        return self.client.post(f"/api/sp/force-reveal/{sc}")

    def match_state(self, sc: str, puck_id: int | None = None):
        url = f"/api/sp/match-state/{sc}"
        if puck_id is not None:
            url += f"?puck_id={puck_id}"
        return self.client.get(url)

    def final_results(self, sc: str):
        return self.client.get(f"/api/sp/final-results/{sc}")


@contextlib.contextmanager
def sp_harness(monkeypatch, tmp_path, *, n_each_difficulty: int = 10):
    """Context manager yielding an :class:`SPHarness`.

    Resets the pair_routes module globals on entry and exit so tests don't leak
    lobby/state into each other.
    """
    import os

    os.environ["SP_PERSIST_DISABLE"] = "1"

    import database
    import pair_routes

    db_file = str(tmp_path / "tw_test.db")

    @contextlib.contextmanager
    def _get_conn():
        conn = sqlite3.connect(db_file)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    monkeypatch.setattr(database, "get_db_connection", _get_conn)
    monkeypatch.setattr(database, "USE_POSTGRES", False, raising=False)
    # Questions have no narration MP3s on disk in tests; force "narrated" so the
    # R027 re-draw loop doesn't churn 12 redundant draws per load.
    monkeypatch.setattr(pair_routes, "_has_narration", lambda _qid: True)

    # Build schema + seed.
    with _get_conn() as conn:
        conn.executescript(_SCHEMA)
        conn.execute(
            "INSERT INTO trivia_game_types (name, display_name) VALUES "
            "('speed_pyramid', 'Speed Pyramid')"
        )
        conn.execute(
            "INSERT INTO trivia_categories (name, emoji, difficulty) VALUES "
            "('TestCat', '🎯', 'medium')"
        )
        cat_id = conn.execute(
            "SELECT id FROM trivia_categories WHERE name = 'TestCat'"
        ).fetchone()["id"]
        for diff in ("easy", "medium", "hard"):
            for i in range(n_each_difficulty):
                conn.execute(
                    "INSERT INTO trivia_questions (category_id, question_text, "
                    "setup_text, answer_a, answer_b, answer_c, answer_d, "
                    "correct_answer, host_commentary_correct, "
                    "host_commentary_wrong, difficulty, time_limit) VALUES "
                    "(?,?,?,?,?,?,?,?,?,?,?,?)",
                    (cat_id, f"{diff} Q{i}?", "setup", "a", "b", "c", "d",
                     "A", "yes", "no", diff, 15),
                )
        conn.commit()

    # Reset module globals so a prior test's lobby/state doesn't bleed in.
    pair_routes._LOBBY = None
    pair_routes._SP_STATE = {}
    pair_routes._QUESTION_TRACKER = {}

    from flask import Flask

    app = Flask(__name__)
    sio = FakeSio()
    pair_routes.init_pair_routes(app, sio)
    client = app.test_client()

    try:
        yield SPHarness(client, sio, db_file)
    finally:
        pair_routes._LOBBY = None
        pair_routes._SP_STATE = {}
        pair_routes._QUESTION_TRACKER = {}
        pair_routes._socketio = None
