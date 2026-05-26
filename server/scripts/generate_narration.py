"""Generate narration MP3s for every trivia_questions row.

Uses Piper TTS (local neural model) to synthesize the question text,
then ffmpeg to convert WAV -> MP3. Output:
server/static/games/speed-pyramid/audio/questions/q_{id}.mp3.

Skips files that already exist unless --overwrite is passed. Run with
sandbox venv:

    cd ~/table-wars-puck-sandbox/server
    DATABASE_URL= venv/bin/python scripts/generate_narration.py --overwrite

Switching to a different Piper voice = swap the .onnx in voices/piper/
and update PIPER_MODEL below. Voices: rhasspy/piper-voices on HF.

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
PIPER_VOICES_DIR = HERE.parent / "voices" / "piper"
PIPER_MODEL = PIPER_VOICES_DIR / "en_US-ryan-high.onnx"
# Piper lives inside the sandbox venv; shutil.which won't find it
# unless venv/bin is on PATH. Use the absolute path.
PIPER_BIN = HERE.parent / "venv" / "bin" / "piper"
# Piper synthesis knobs. length_scale > 1.0 slows speech (more theatrical);
# < 1.0 speeds it up. noise_scale controls vocal variation. The defaults
# (1.0 / 0.667) read flat — we nudge length down slightly for energy.
PIPER_LENGTH_SCALE = 0.95
PIPER_NOISE_SCALE = 0.7
PIPER_NOISE_W = 0.85
PIPER_SENTENCE_SILENCE = 0.35  # seconds of pause between sentences


def have(bin_name: str) -> bool:
    return shutil.which(bin_name) is not None


def generate(qid: int, text: str, out_path: Path) -> None:
    """piper -> WAV temp -> ffmpeg -> MP3 out."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        wav = Path(f.name)
    try:
        # Piper reads text from stdin and writes WAV to -f path.
        subprocess.run(
            [
                str(PIPER_BIN),
                "-m", str(PIPER_MODEL),
                "-f", str(wav),
                "--length-scale", str(PIPER_LENGTH_SCALE),
                "--noise-scale", str(PIPER_NOISE_SCALE),
                "--noise-w-scale", str(PIPER_NOISE_W),
                "--sentence-silence", str(PIPER_SENTENCE_SILENCE),
            ],
            input=text.encode("utf-8"),
            check=True,
            capture_output=True,
        )
        subprocess.run(
            [
                "ffmpeg", "-y", "-loglevel", "error",
                "-i", str(wav),
                "-codec:a", "libmp3lame",
                "-b:a", "64k",
                "-ar", "22050",
                str(out_path),
            ],
            check=True,
            capture_output=True,
        )
    finally:
        if wav.exists():
            wav.unlink()


def main() -> int:
    if not PIPER_BIN.exists():
        print(f"missing piper binary at {PIPER_BIN}")
        print("  install: venv/bin/pip install piper-tts")
        return 1
    if not have("ffmpeg"):
        print("missing ffmpeg")
        print("  install: brew install ffmpeg")
        return 1
    if not PIPER_MODEL.exists():
        print(f"missing Piper model: {PIPER_MODEL}")
        print("  download from https://huggingface.co/rhasspy/piper-voices")
        print(f"  drop the .onnx + .onnx.json into {PIPER_VOICES_DIR}")
        return 1

    overwrite = "--overwrite" in sys.argv
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB))
    rows = conn.execute(
        "SELECT id, setup_text, question_text, answer_a, answer_b, answer_c, "
        "answer_d FROM trivia_questions WHERE setup_text IS NOT NULL "
        "AND length(trim(setup_text)) > 0"
    ).fetchall()
    conn.close()
    print(f"generating narration for {len(rows)} questions -> {OUT_DIR}"
          + (" (--overwrite)" if overwrite else ""))

    new = skipped = failed = 0
    for qid, setup, q, a, b, c, d in rows:
        out = OUT_DIR / f"q_{qid}.mp3"
        if not overwrite and out.exists() and out.stat().st_size > 0:
            skipped += 1
            continue
        # Read: setup, then the question, then each labelled choice.
        # A bare "A." gets read as the indefinite article ("uh") by
        # espeak-ng's heuristic. Putting the letter and the answer in
        # the same sentence with a colon ("A: text.") forces it into
        # list-item prosody, which espeak-ng renders as the letter
        # name. Same trick for B and C. D alone reads correctly even
        # bare (no English word collision), but we keep the format
        # consistent across all four.
        parts = [(setup or "").strip()]
        if q: parts.append(q.strip())
        if a: parts.append(f"A: {a.strip()}.")
        if b: parts.append(f"B: {b.strip()}.")
        if c: parts.append(f"C: {c.strip()}.")
        if d: parts.append(f"Or D: {d.strip()}.")
        script = "  ".join(p for p in parts if p)
        try:
            generate(qid, script, out)
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
