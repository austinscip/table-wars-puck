"""Sample Kokoro TTS voices to compare against the current Piper narration.

Usage examples:

    # Sample the standard voices on a fixed test sentence + letter pronunciation
    venv/bin/python scripts/sample_kokoro.py

    # Sample a specific trivia question by id (uses question_text)
    venv/bin/python scripts/sample_kokoro.py --qid 100

    # Sample arbitrary text in a specific voice
    venv/bin/python scripts/sample_kokoro.py --text "What was Logan Paul's 2018 video? A: Filming a body. B: His brother." --voice af_sarah

Outputs land in server/voices/kokoro/samples/<voice>__<slug>.mp3. Side
audio dir kept separate from the production narration MP3s so a sampling
session doesn't trample the served files.

Picks the best Kokoro voice by listening: each voice's full pronunciation
of "A: ... B: ... C: ... D: ..." is the killer test — that's where Piper
sounds bad.
"""
from __future__ import annotations

import argparse
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

import soundfile as sf  # comes with kokoro-onnx deps
from kokoro_onnx import Kokoro


HERE = Path(__file__).resolve().parent
SERVER = HERE.parent
DB = SERVER / "tablewars.db"
VOICES_DIR = SERVER / "voices" / "kokoro"
MODEL = VOICES_DIR / "kokoro-v1.0.onnx"
VOICES = VOICES_DIR / "voices-v1.0.bin"
OUT_DIR = VOICES_DIR / "samples"

# A short curated list of the strongest Kokoro voices for a bar-trivia
# host (English, expressive, clear on letters). The user can run the
# script multiple times to listen and pick.
CANDIDATE_VOICES = [
    "af_sarah",     # American female, warm
    "af_heart",     # American female, more expressive
    "af_bella",     # American female, brighter
    "am_michael",   # American male, host energy
    "am_adam",      # American male, deeper
    "bf_isabella",  # British female
    "bm_george",    # British male
]

DEFAULT_TEST_TEXT = (
    "What was Logan Paul's 2018 video controversy about? "
    "A: Filming a body in Aokigahara forest. "
    "B: His brother Jake. "
    "C: A movie scene. "
    "D: Both A and triggering massive YouTube cleanup."
)


def slug(s: str, maxlen: int = 40) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "_", s).strip("_").lower()
    return s[:maxlen] or "sample"


def question_text(qid: int) -> str:
    con = sqlite3.connect(DB)
    cur = con.cursor()
    row = cur.execute(
        "SELECT setup_text, question_text, answer_a, answer_b, answer_c, answer_d "
        "FROM trivia_questions WHERE id = ?", (qid,)
    ).fetchone()
    con.close()
    if not row:
        raise SystemExit(f"no question with id={qid}")
    setup, q, a, b, c, d = row
    parts = []
    if setup: parts.append(setup)
    parts.append(q)
    parts.append(f"A: {a}.")
    parts.append(f"B: {b}.")
    parts.append(f"C: {c}.")
    parts.append(f"D: {d}.")
    return " ".join(parts)


def synth(kokoro: Kokoro, voice: str, text: str, out_path: Path) -> float:
    samples, sr = kokoro.create(text, voice=voice, speed=1.0, lang="en-us")
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        wav_path = Path(f.name)
    try:
        sf.write(str(wav_path), samples, sr)
        # WAV -> MP3 via ffmpeg, modest 64kbps mono (matches Piper output).
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(wav_path), "-ac", "1", "-b:a", "64k", str(out_path)],
            check=True, capture_output=True,
        )
        duration = len(samples) / sr
        return duration
    finally:
        wav_path.unlink(missing_ok=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", help="Arbitrary text to synthesize")
    ap.add_argument("--qid", type=int, help="Trivia question id to read from DB")
    ap.add_argument("--voice", help="Single voice (e.g. af_sarah); default samples ALL candidates")
    args = ap.parse_args()

    if not MODEL.exists() or not VOICES.exists():
        print(f"FAIL: missing model files at {MODEL} or {VOICES}", file=sys.stderr)
        return 1
    if not shutil.which("ffmpeg"):
        print("FAIL: ffmpeg not in PATH", file=sys.stderr)
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    if args.qid is not None:
        text = question_text(args.qid)
        label = f"q{args.qid}"
    elif args.text:
        text = args.text
        label = slug(args.text)
    else:
        text = DEFAULT_TEST_TEXT
        label = "abcd_test"

    print(f"text: {text!r}")
    voices = [args.voice] if args.voice else CANDIDATE_VOICES
    print(f"loading Kokoro model (one-time) ...", flush=True)
    kokoro = Kokoro(str(MODEL), str(VOICES))
    print(f"")

    print(f"{'voice':<14s} {'dur':>5s}  output")
    for v in voices:
        out = OUT_DIR / f"{v}__{label}.mp3"
        try:
            dur = synth(kokoro, v, text, out)
            print(f"{v:<14s} {dur:>4.1f}s  {out}")
        except Exception as e:
            print(f"{v:<14s}  ERR  {e!r}")

    print(f"\nsamples in: {OUT_DIR}/")
    print(f"play in browser or `afplay {OUT_DIR}/<file>.mp3` to compare.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
