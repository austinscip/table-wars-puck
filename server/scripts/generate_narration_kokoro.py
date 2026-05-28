"""Generate narration MP3s for every trivia_questions row using Kokoro.

Mirror of generate_narration.py (Piper) but using kokoro-onnx. The user
picked Kokoro's `am_michael` (American male, host energy) over Piper for
better letter pronunciation ("A: ... B: ... C: ... D: ..." reads
cleanly instead of "A: -> uh ..." espeak-ng confusion).

Output:
    server/static/games/speed-pyramid/audio/questions/q_{id}.mp3

Usage:
    cd ~/table-wars-puck-sandbox/server
    # Generate a small test batch first (10 questions)
    DATABASE_URL= venv/bin/python scripts/generate_narration_kokoro.py --limit 10 --overwrite
    # Then the full ~1180 row regen
    DATABASE_URL= venv/bin/python scripts/generate_narration_kokoro.py --overwrite

The pair_routes.py `_NARRATED_QIDS_CACHE` is built from file existence so
overwriting MP3s in place does NOT require a Flask restart. The TV uses
`?v=<mtime>` cache-busting so browsers pick up the new content on next
question_show.
"""
from __future__ import annotations

import argparse
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import soundfile as sf
from kokoro_onnx import Kokoro


HERE = Path(__file__).resolve().parent
SERVER = HERE.parent
DB = SERVER / "tablewars.db"
OUT_DIR = SERVER / "static" / "games" / "speed-pyramid" / "audio" / "questions"
VOICES_DIR = SERVER / "voices" / "kokoro"
KOKORO_MODEL = VOICES_DIR / "kokoro-v1.0.onnx"
KOKORO_VOICES = VOICES_DIR / "voices-v1.0.bin"

DEFAULT_VOICE = "am_michael"  # user-selected from samples
DEFAULT_SPEED = 1.0           # natural pace; bump to 1.1 for snappier host


def question_script(setup: str | None, q: str | None,
                    a: str | None, b: str | None,
                    c: str | None, d: str | None) -> str:
    """Build the host's spoken script for a question. Same labelled-choice
    format as Piper to preserve the prosody that makes letters read
    correctly ("A: text." not "A . text"). Kokoro pronounces letters
    cleanly anyway, but consistent formatting helps the host cadence."""
    parts = []
    if setup and setup.strip(): parts.append(setup.strip())
    if q and q.strip(): parts.append(q.strip())
    if a and a.strip(): parts.append(f"A: {a.strip()}.")
    if b and b.strip(): parts.append(f"B: {b.strip()}.")
    if c and c.strip(): parts.append(f"C: {c.strip()}.")
    if d and d.strip(): parts.append(f"Or D: {d.strip()}.")
    return "  ".join(parts)


def synth_to_mp3(kokoro: Kokoro, voice: str, speed: float,
                 text: str, out_path: Path) -> None:
    samples, sr = kokoro.create(text, voice=voice, speed=speed, lang="en-us")
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        wav = Path(f.name)
    try:
        sf.write(str(wav), samples, sr)
        subprocess.run(
            [
                "ffmpeg", "-y", "-loglevel", "error",
                "-i", str(wav),
                "-codec:a", "libmp3lame",
                "-b:a", "64k",
                "-ar", "22050",
                str(out_path),
            ],
            check=True, capture_output=True,
        )
    finally:
        wav.unlink(missing_ok=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--voice", default=DEFAULT_VOICE,
                    help=f"Kokoro voice (default: {DEFAULT_VOICE})")
    ap.add_argument("--speed", type=float, default=DEFAULT_SPEED,
                    help=f"Speech rate (default: {DEFAULT_SPEED})")
    ap.add_argument("--overwrite", action="store_true",
                    help="Re-generate even if the MP3 already exists")
    ap.add_argument("--limit", type=int, default=0,
                    help="Stop after N new files (0 = all)")
    ap.add_argument("--shard", default="0/1",
                    help="Process only IDs where id %% N == k. Format k/N "
                         "(e.g. 0/8, 1/8 ... 7/8). Used to run N parallel "
                         "workers each on a disjoint slice.")
    args = ap.parse_args()
    try:
        shard_k, shard_n = (int(x) for x in args.shard.split("/"))
        assert 0 <= shard_k < shard_n
    except (ValueError, AssertionError):
        print(f"bad --shard {args.shard!r}; expected k/N (e.g. 3/8)", file=sys.stderr)
        return 1

    if not KOKORO_MODEL.exists() or not KOKORO_VOICES.exists():
        print(f"missing Kokoro model files at {VOICES_DIR}", file=sys.stderr)
        return 1
    if not shutil.which("ffmpeg"):
        print("missing ffmpeg in PATH", file=sys.stderr)
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB))
    # Generate for ALL questions (no setup_text filter). The 116 questions
    # that previously had no Piper MP3 — R027's silence gap — are now
    # narrated too, using just `question + A/B/C/D` when setup is empty.
    rows = conn.execute(
        "SELECT id, setup_text, question_text, answer_a, answer_b, answer_c, "
        "answer_d FROM trivia_questions"
    ).fetchall()
    conn.close()

    print(f"voice={args.voice} speed={args.speed}")
    print(f"loading Kokoro model (one-time, ~310MB) ...", flush=True)
    t0 = time.time()
    kokoro = Kokoro(str(KOKORO_MODEL), str(KOKORO_VOICES))
    print(f"  loaded in {time.time() - t0:.1f}s", flush=True)
    print(f"generating narration for {len(rows)} questions -> {OUT_DIR}"
          + (" (--overwrite)" if args.overwrite else ""))

    # Shard filter — each parallel worker takes a disjoint slice.
    if shard_n > 1:
        rows = [r for r in rows if (r[0] % shard_n) == shard_k]
        print(f"shard {shard_k}/{shard_n}: {len(rows)} rows assigned")

    new = skipped = failed = 0
    batch_t0 = time.time()
    for qid, setup, q, a, b, c, d in rows:
        out = OUT_DIR / f"q_{qid}.mp3"
        if not args.overwrite and out.exists() and out.stat().st_size > 0:
            skipped += 1
            continue
        script = question_script(setup, q, a, b, c, d)
        if not script:
            failed += 1
            continue
        try:
            synth_to_mp3(kokoro, args.voice, args.speed, script, out)
            new += 1
            if new % 25 == 0:
                elapsed = time.time() - batch_t0
                rate = new / elapsed
                remaining = len(rows) - skipped - new - failed
                eta_s = remaining / rate if rate > 0 else 0
                print(f"  {new} done  ({rate:.1f}/s, ~{eta_s/60:.1f}min remaining)",
                      flush=True)
            if args.limit and new >= args.limit:
                print(f"  --limit {args.limit} reached, stopping early.")
                break
        except subprocess.CalledProcessError as e:
            failed += 1
            print(f"  q_{qid} failed: {e.stderr.decode(errors='replace')[:200]}")
        except Exception as e:
            failed += 1
            print(f"  q_{qid} failed: {e!r}")

    total_s = time.time() - batch_t0
    print(f"\ndone in {total_s:.1f}s ({total_s/60:.1f}min). "
          f"new={new} skipped={skipped} failed={failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
