"""Slice R041 — synthesize the 12 SFX sample MP3s referenced by audio.ts
so the sample-MP3 layer actually has assets to play. Until these exist,
_playSample always returns false and the bleed gate is INCONCLUSIVE.

Each SFX is a short ffmpeg-generated sine envelope tuned by name. Output
to server/static/games/speed-pyramid/dist/assets/audio/ — same path
audio.ts loads (AUDIO_BASE = '/tv/speed-pyramid/assets/audio').

The dist/ path is what Flask serves under /tv/speed-pyramid/, so the
files don't need a Vite rebuild. They're committed straight to the
dist folder.

Re-runnable: regenerates everything from scratch with --overwrite, or
skips existing files by default.

Usage:
    DATABASE_URL= venv/bin/python scripts/generate_sfx_samples.py
    DATABASE_URL= venv/bin/python scripts/generate_sfx_samples.py --overwrite
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

# (name, freq_hz, duration_s, envelope_curve)
# Curves: "ping" = fast attack + ~100ms decay; "thud" = slow attack +
# 300ms decay; "buzz" = sustained 200ms with no decay; "rise" = freq
# ramps up over duration.
SFX = [
    ("sfx_tick",         600, 0.08, "ping"),
    ("sfx_tick_final",  1200, 0.18, "thud"),
    ("sfx_lock",         440, 0.20, "thud"),
    ("sfx_correct",      880, 0.30, "rise"),
    ("sfx_wrong",        200, 0.30, "thud"),
    ("sfx_reveal",       660, 0.35, "rise"),
    ("sfx_match_end",    523, 0.60, "rise"),
    ("sfx_digit",        800, 0.07, "ping"),
    ("sfx_joined",       988, 0.25, "rise"),
    ("sfx_pick_show",    494, 0.20, "ping"),
    ("sfx_pick_locked",  698, 0.22, "thud"),
    ("sfx_question_show", 587, 0.18, "ping"),
]


# Output to public/ so Vite copies into dist/ on every build (dist
# is the served path but vite wipes it on each build, so committing
# straight to dist would lose the assets on next CI build).
OUT_DIR = (Path(__file__).resolve().parent.parent
           / "static" / "games" / "speed-pyramid"
           / "public" / "assets" / "audio")


def _filter(curve: str, freq: int, duration: float) -> str:
    """Build the ffmpeg `-af` filter for an envelope. Uses `aevalsrc`
    upstream so we can multiply by a gain envelope cleanly."""
    if curve == "rise":
        # Linear pitch ramp from freq to freq*1.5 with a soft envelope.
        # Use lavfi sine + areverse'd sigmoid envelope.
        return (f"afade=t=in:st=0:d=0.02,"
                f"afade=t=out:st={max(0, duration-0.15):.3f}:d=0.15,"
                f"volume=0.35")
    if curve == "thud":
        return (f"afade=t=in:st=0:d=0.05,"
                f"afade=t=out:st={max(0, duration-0.20):.3f}:d=0.20,"
                f"volume=0.30")
    if curve == "buzz":
        return f"volume=0.25"
    # ping (default)
    return (f"afade=t=in:st=0:d=0.005,"
            f"afade=t=out:st={max(0, duration-0.06):.3f}:d=0.06,"
            f"volume=0.30")


def _ffmpeg_render(out: Path, name: str, freq: int, duration: float,
                   curve: str) -> None:
    # sine input. For "rise" we ramp freq across duration via lavfi
    # expression. ffmpeg's sine source doesn't natively ramp, so we
    # synthesize via aevalsrc with `sin(2*PI*t*f(t))`.
    if curve == "rise":
        end_freq = int(freq * 1.5)
        src = (
            f"-f lavfi -i aevalsrc=sin(2*PI*t*("
            f"{freq}+{end_freq - freq}*t/{duration})):"
            f"d={duration}:s=22050"
        )
    else:
        src = (f"-f lavfi -i sine=frequency={freq}:duration={duration}"
               f":sample_rate=22050")

    af = _filter(curve, freq, duration)
    cmd = (
        ["ffmpeg", "-y", "-loglevel", "error"]
        + src.split()
        + ["-af", af, "-codec:a", "libmp3lame", "-b:a", "64k",
           "-ar", "22050", str(out)]
    )
    subprocess.run(cmd, check=True)


def main() -> int:
    if shutil.which("ffmpeg") is None:
        print("ffmpeg not found in PATH — install via `brew install ffmpeg`",
              file=sys.stderr)
        return 1

    ap = argparse.ArgumentParser()
    ap.add_argument("--overwrite", action="store_true",
                    help="regenerate even if file exists")
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    written = 0
    skipped = 0
    for name, freq, dur, curve in SFX:
        out = OUT_DIR / f"{name}.mp3"
        if out.exists() and not args.overwrite:
            skipped += 1
            continue
        print(f"  {name}.mp3  freq={freq}Hz dur={dur:.2f}s curve={curve}")
        _ffmpeg_render(out, name, freq, dur, curve)
        written += 1
    print(f"Done: {written} written, {skipped} skipped. Out: {OUT_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
