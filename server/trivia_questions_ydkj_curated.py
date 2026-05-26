"""3A — Owner-curated YDKJ-style questions loaded from a CSV next to this file.

Why a CSV: easier to bulk-add hand-written questions without re-running a
Python script for every entry. Owner edits the CSV directly.

CSV columns (in order):
    category,difficulty,setup,question,a,b,c,d,correct,explanation,
    commentary_correct,commentary_wrong

`correct` must be one of A/B/C/D. `category` must match a name in
trivia_categories (auto-created at startup by seed_trivia_data). Missing or
mistyped categories cause the row to be skipped with a warning, not a crash.

Idempotent: INSERT OR IGNORE relies on the question_text unique index added
in trivia_database.init_trivia_database (3A change).
"""

import csv
from pathlib import Path

from trivia_database import execute_query, get_placeholder, get_category_by_name


CSV_PATH = Path(__file__).resolve().parent / "trivia_questions_ydkj_curated.csv"
VALID_DIFFICULTIES = {"easy", "medium", "hard"}


def _load_rows() -> list[dict]:
    if not CSV_PATH.exists():
        return []
    rows: list[dict] = []
    with CSV_PATH.open() as f:
        reader = csv.DictReader(f)
        for raw in reader:
            try:
                diff = (raw.get("difficulty") or "medium").strip().lower()
                if diff not in VALID_DIFFICULTIES:
                    diff = "medium"
                correct = (raw.get("correct") or "").strip().upper()
                if correct not in {"A", "B", "C", "D"}:
                    print(f"[ydkj_curated] skip row, bad correct={correct!r}: {raw.get('question', '')[:60]}")
                    continue
                rows.append({
                    "category": (raw.get("category") or "").strip(),
                    "setup": (raw.get("setup") or "").strip(),
                    "question": (raw.get("question") or "").strip(),
                    "answers": {
                        "A": (raw.get("a") or "").strip(),
                        "B": (raw.get("b") or "").strip(),
                        "C": (raw.get("c") or "").strip(),
                        "D": (raw.get("d") or "").strip(),
                    },
                    "correct": correct,
                    "explanation": (raw.get("explanation") or "").strip(),
                    "commentary_correct": (raw.get("commentary_correct") or "").strip(),
                    "commentary_wrong": (raw.get("commentary_wrong") or "").strip(),
                    "difficulty": diff,
                    "time_limit": 15,
                })
            except Exception as e:
                print(f"[ydkj_curated] skip malformed row: {e}")
    return rows


def seed_ydkj_curated() -> None:
    """Load owner-curated YDKJ-style questions from CSV. Additive + idempotent."""
    ph = get_placeholder()
    rows = _load_rows()
    if not rows:
        print("[ydkj_curated] no rows (CSV missing or empty)")
        return

    added = 0
    skipped_no_category = 0
    for q in rows:
        if not q["question"] or not all(q["answers"].values()):
            continue
        category = get_category_by_name(q["category"])
        if not category:
            skipped_no_category += 1
            print(f"[ydkj_curated] category '{q['category']}' not found; skipping {q['question'][:60]}")
            continue
        try:
            execute_query(f'''
                INSERT OR IGNORE INTO trivia_questions
                (category_id, question_text, setup_text, answer_a, answer_b, answer_c, answer_d,
                 correct_answer, difficulty, time_limit, explanation,
                 host_commentary_correct, host_commentary_wrong)
                VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
            ''', (
                category["id"],
                q["question"],
                q["setup"] or "",
                q["answers"]["A"],
                q["answers"]["B"],
                q["answers"]["C"],
                q["answers"]["D"],
                q["correct"],
                q["difficulty"],
                q["time_limit"],
                q["explanation"],
                q["commentary_correct"],
                q["commentary_wrong"],
            ))
            added += 1
        except Exception as e:
            print(f"[ydkj_curated] insert error: {e}")

    if skipped_no_category:
        print(f"[ydkj_curated] skipped {skipped_no_category} rows due to missing categories")
    print(f"✅ YDKJ curated seeder added {added} new questions (of {len(rows)} parsed)")


if __name__ == "__main__":
    seed_ydkj_curated()
