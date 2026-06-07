#!/usr/bin/env python3
"""Trivia content audit — objective quality smells in the question bank.

    python tools/content_audit.py [tablewars.db]

Reports the things a query CAN judge (volume, answer-position bias, duplicates,
missing comedy beats, category balance, structural junk). It can't judge whether
a joke lands or an answer is factually right — that's the human pass — but it
quantifies how thin/lazy a bank is and flags the rows worth a human look.
"""
from __future__ import annotations

import collections
import sqlite3
import sys


def audit(db_path: str) -> int:
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        "SELECT id, category_id, question_text, setup_text, "
        "answer_a, answer_b, answer_c, answer_d, correct_answer, difficulty, "
        "host_commentary_correct, host_commentary_wrong "
        "FROM trivia_questions"
    ).fetchall()
    n = len(rows)
    print(f"\n=== Trivia content audit ({db_path}) ===")
    print(f"total questions: {n}")
    if n == 0:
        return 0

    # Volume verdict (the Caxy plan wants ~50 handwritten per season pack).
    print(f"  pilot needs hundreds; this is "
          f"{'WAY too few' if n < 200 else 'okay-ish'} for 4 games × repeat play.")

    # Answer-position bias — the #1 lazy-authoring tell. If the correct letter
    # skews to one position, players learn 'always pick A'.
    letters = collections.Counter(r["correct_answer"] for r in rows)
    print("\ncorrect-answer position distribution (want ~25% each):")
    for L in "ABCD":
        pct = 100 * letters.get(L, 0) / n
        flag = "  <-- SKEWED" if pct > 40 or pct < 12 else ""
        print(f"  {L}: {letters.get(L,0):3d}  ({pct:4.1f}%){flag}")

    # Duplicates / near-empty.
    qtexts = collections.Counter(
        (r["question_text"] or "").strip().lower() for r in rows)
    dupes = {q: c for q, c in qtexts.items() if c > 1 and q}
    print(f"\nduplicate question texts: {len(dupes)}")
    for q, c in list(dupes.items())[:5]:
        print(f"  x{c}: {q[:70]}")

    short = [r["id"] for r in rows if len((r["question_text"] or "").strip()) < 12]
    no_setup = [r["id"] for r in rows if not (r["setup_text"] or "").strip()]
    print(f"too-short question text: {len(short)} {short[:10]}")
    print(f"missing setup (no comedy lead-in): {len(no_setup)}")

    # Comedy beats — YDKJ-style needs host commentary on reveal. Missing = flat.
    no_correct_vo = sum(1 for r in rows if not (r["host_commentary_correct"] or "").strip())
    no_wrong_vo = sum(1 for r in rows if not (r["host_commentary_wrong"] or "").strip())
    print(f"\nmissing host commentary (the jokes on reveal):")
    print(f"  no 'correct' line: {no_correct_vo}/{n}")
    print(f"  no 'wrong' line:   {no_wrong_vo}/{n}")

    # Category balance.
    cats = collections.Counter(r["category_id"] for r in rows)
    print(f"\ncategories used: {len(cats)}  "
          f"(min {min(cats.values())} / max {max(cats.values())} questions)")

    # Difficulty spread.
    diff = collections.Counter((r["difficulty"] or "?") for r in rows)
    print(f"difficulty spread: {dict(diff)}")

    print("\nverdict: objective smells above. The qualitative call (are the "
          "jokes funny / answers right) is the human pass this tool can't do.")
    return 0


if __name__ == "__main__":
    db = sys.argv[1] if len(sys.argv) > 1 else "tablewars.db"
    raise SystemExit(audit(db))
