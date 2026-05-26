"""Generate narration MP3s for every trivia_questions row.

Uses macOS `say` (TTS) to synthesize the setup_text, then ffmpeg to
convert AIFF -> MP3 at a low bitrate (narration doesn't need fidelity).
Output: server/static/games/speed-pyramid/audio/questions/q_{id}.mp3.

Skips files that already exist. Run with sandbox venv:
    cd ~/table-wars-puck-sandbox/server
    DATABASE_URL= venv/bin/python scripts/generate_narration.py

The TV's QuestionScreen plays this on question_show, then POSTs
/api/sp/start-timer when the audio ends so the countdown begins after
the host finishes reading.
"""
from __future__ import annotations

import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path


HERE = Path(__file__).resolve().parent
DB = HERE.parent / "tablewars.db"
OUT_DIR = HERE.parent / "static" / "games" / "speed-pyramid" / "audio" / "questions"
VOICE = "Samantha"  # macOS default — clear, neutral US english
RATE = 200  # words per minute; 180-220 reads naturally without being slow


def have(bin_name: str) -> bool:
    return shutil.which(bin_name) is not None


def generate(qid: int, text: str, out_path: Path) -> None:
    """say -> AIFF temp -> ffmpeg -> MP3 out."""
    with tempfile.NamedTemporaryFile(suffix=".aiff", delete=False) as f:
        aiff = Path(f.name)
    try:
        subprocess.run(
            ["say", "-v", VOICE, "-r", str(RATE), "-o", str(aiff), text],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            [
                "ffmpeg", "-y", "-loglevel", "error",
                "-i", str(aiff),
                "-codec:a", "libmp3lame",
                "-b:a", "48k",   # narration-grade bitrate
                "-ar", "22050",
                str(out_path),
            ],
            check=True,
            capture_output=True,
        )
    finally:
        if aiff.exists():
            aiff.unlink()


def main() -> int:
    if not have("say") or not have("ffmpeg"):
        print("missing `say` or `ffmpeg` — this script requires macOS + ffmpeg")
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB))
    rows = conn.execute(
        "SELECT id, setup_text FROM trivia_questions WHERE setup_text IS NOT NULL "
        "AND length(trim(setup_text)) > 0"
    ).fetchall()
    conn.close()
    print(f"generating narration for {len(rows)} questions -> {OUT_DIR}")

    new = skipped = failed = 0
    for qid, setup in rows:
        out = OUT_DIR / f"q_{qid}.mp3"
        if out.exists() and out.stat().st_size > 0:
            skipped += 1
            continue
        try:
            generate(qid, setup, out)
            new += 1
            if new % 10 == 0:
                print(f"  ... {new} done")
        except subprocess.CalledProcessError as e:
            failed += 1
            print(f"  q_{qid} failed: {e.stderr.decode(errors='replace')[:200]}")

    print(f"done. new={new} skipped={skipped} failed={failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
