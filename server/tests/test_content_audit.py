"""Smoke test for the content-audit operator tool — it must run cleanly on a
real-shaped question DB and not crash on an empty one."""
from __future__ import annotations

import os
import sqlite3
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))

import content_audit  # noqa: E402


def _make_db(path, rows):
    con = sqlite3.connect(path)
    con.execute(
        "CREATE TABLE trivia_questions (id INTEGER PRIMARY KEY, category_id INT, "
        "question_text TEXT, setup_text TEXT, answer_a TEXT, answer_b TEXT, "
        "answer_c TEXT, answer_d TEXT, correct_answer TEXT, difficulty TEXT, "
        "host_commentary_correct TEXT, host_commentary_wrong TEXT)")
    con.executemany(
        "INSERT INTO trivia_questions (category_id, question_text, setup_text, "
        "answer_a, answer_b, answer_c, answer_d, correct_answer, difficulty, "
        "host_commentary_correct, host_commentary_wrong) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?)", rows)
    con.commit()
    con.close()


def test_audit_runs_on_populated_db(tmp_path, capsys):
    db = str(tmp_path / "t.db")
    _make_db(db, [
        (1, "What happened?", "setup", "a", "b", "c", "d", "A", "easy", "yes", "no"),
        (1, "What happened?", "setup", "a", "b", "c", "d", "A", "easy", "yes", "no"),
        (2, "Why?", "setup", "a", "b", "c", "d", "B", "hard", "yes", "no"),
    ])
    assert content_audit.audit(db) == 0
    out = capsys.readouterr().out
    assert "total questions: 3" in out
    assert "duplicate question texts: 1" in out  # the two identical "What happened?"
    assert "SKEWED" in out  # correct-letter heavily skewed to A


def test_audit_handles_empty_db(tmp_path, capsys):
    db = str(tmp_path / "empty.db")
    _make_db(db, [])
    assert content_audit.audit(db) == 0
    assert "total questions: 0" in capsys.readouterr().out
