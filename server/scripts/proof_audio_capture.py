"""PROOF primitive — can we capture the browser's ACTUAL audio output?

Everything in the verification plan rests on this: if we cannot record
the real sound a browser emits and analyze it, then "verify audio in the
browser" is impossible on this machine and we need a different approach.

Headless Chromium has no audio device, so we can't record at the OS
layer. Instead we capture INSIDE the page: route an <audio> element
through a Web Audio MediaElementSource into a MediaStreamDestination
feeding a MediaRecorder. That records the real decoded PCM regardless of
any output device. We then pull the recording to disk and let ffmpeg
prove it is non-silent and the right duration.

If this passes, ground-truth audio verification is feasible and the rest
of the harness can be built on it. If it fails, say so loudly — do NOT
pretend audio was verified.

Run with sandbox Flask up on :5002.
"""
from __future__ import annotations

import base64
import glob
import os
import subprocess
import sys
import tempfile
import time

import requests
from playwright.sync_api import sync_playwright


BASE = "http://localhost:5002"
TITLE = f"{BASE}/tv/speed-pyramid/"
MP3_DIR = os.path.join(
    os.path.dirname(__file__), "..",
    "static", "games", "speed-pyramid", "audio", "questions",
)

CAPTURE_RIG = r"""
(() => {
  window.__cap = null;
  const AC = window.AudioContext || window.webkitAudioContext;
  const ctx = new AC();
  const dest = ctx.createMediaStreamDestination();
  const chunks = [];
  const rec = new MediaRecorder(dest.stream, { mimeType: 'audio/webm' });
  rec.ondataavailable = (e) => { if (e.data && e.data.size) chunks.push(e.data); };
  rec.start(200);
  const seen = new WeakSet();
  const _play = HTMLAudioElement.prototype.play;
  HTMLAudioElement.prototype.play = function () {
    if (!seen.has(this)) {
      seen.add(this);
      try {
        const s = ctx.createMediaElementSource(this);
        s.connect(dest);             // -> recorder
        s.connect(ctx.destination);  // -> (silent) speaker, keeps graph pulling
      } catch (e) { /* already connected or cross-origin */ }
    }
    if (ctx.state === 'suspended') ctx.resume();
    return _play.apply(this, arguments);
  };
  window.__capStopAndDump = async () => {
    rec.requestData();
    await new Promise((r) => setTimeout(r, 250));
    rec.stop();
    await new Promise((r) => setTimeout(r, 250));
    const blob = new Blob(chunks, { type: 'audio/webm' });
    const buf = await blob.arrayBuffer();
    let bin = '';
    const bytes = new Uint8Array(buf);
    for (let i = 0; i < bytes.length; i++) bin += String.fromCharCode(bytes[i]);
    return { b64: btoa(bin), bytes: bytes.length };
  };
})();
"""


def ffprobe_duration(path: str) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True,
    )
    try:
        return float(out.stdout.strip())
    except ValueError:
        return 0.0


def ffmpeg_mean_volume(path: str) -> float:
    out = subprocess.run(
        ["ffmpeg", "-i", path, "-af", "volumedetect", "-f", "null", "-"],
        capture_output=True, text=True,
    )
    # volumedetect prints to stderr: "mean_volume: -23.4 dB"
    for line in out.stderr.splitlines():
        if "mean_volume:" in line:
            try:
                return float(line.split("mean_volume:")[1].split("dB")[0].strip())
            except Exception:
                pass
    return float("-inf")


def find_present_mp3() -> tuple[str, str, float] | None:
    """Return (url, disk_path, duration_s) for a real, non-trivial MP3
    that Flask actually serves (HTTP 200)."""
    candidates = sorted(glob.glob(os.path.join(MP3_DIR, "q_*.mp3")))
    for path in candidates:
        if os.path.getsize(path) < 2000:
            continue
        name = os.path.basename(path)
        url = f"{BASE}/static/games/speed-pyramid/audio/questions/{name}"
        try:
            r = requests.head(url, timeout=4)
            if r.status_code != 200:
                continue
        except Exception:
            continue
        dur = ffprobe_duration(path)
        if dur >= 1.0:
            return url, path, dur
    return None


def run() -> int:
    print("=== PROOF: can we capture real browser audio output? ===", flush=True)
    found = find_present_mp3()
    if not found:
        print("INCONCLUSIVE: no served, >=1s narration MP3 found — cannot run proof")
        return 2
    url, disk_path, src_dur = found
    print(f"using narration: {os.path.basename(disk_path)}  (duration {src_dur:.2f}s)")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--autoplay-policy=no-user-gesture-required",
                  "--use-fake-ui-for-media-stream"],
        )
        ctx = browser.new_context()
        page = ctx.new_page()
        page.add_init_script(CAPTURE_RIG)
        page.goto(TITLE, wait_until="domcontentloaded")
        page.mouse.click(400, 300)  # user gesture to unlock audio
        time.sleep(0.4)

        # Play the real narration MP3 inside the page and let it run.
        page.evaluate(
            """(u) => { const a = new Audio(u); a.id='__probe'; document.body.appendChild(a); window.__probe=a; return a.play().then(()=>true).catch(e=>String(e)); }""",
            url,
        )
        # Record for the clip's duration + a margin.
        record_s = min(src_dur, 6.0) + 0.8
        print(f"recording for {record_s:.1f}s ...", flush=True)
        time.sleep(record_s)

        dump = page.evaluate("() => window.__capStopAndDump()")
        browser.close()

    if not dump or not dump.get("b64"):
        print("FAIL: capture rig returned no data (MediaRecorder produced nothing)")
        return 1
    print(f"captured {dump['bytes']} bytes of webm/opus")

    tmp = tempfile.mkdtemp(prefix="audiocap_")
    webm = os.path.join(tmp, "cap.webm")
    with open(webm, "wb") as f:
        f.write(base64.b64decode(dump["b64"]))

    # MediaRecorder's live webm has no duration in its header, so ffprobe
    # reads 0.00 directly. Remux to wav to recover the true duration and
    # measure volume off a clean PCM file.
    wav = os.path.join(tmp, "cap.wav")
    subprocess.run(["ffmpeg", "-y", "-i", webm, wav],
                   capture_output=True, text=True)
    cap_dur = ffprobe_duration(wav)
    cap_vol = ffmpeg_mean_volume(wav)
    print(f"captured duration: {cap_dur:.2f}s   (source clip {src_dur:.2f}s)")
    print(f"captured mean volume: {cap_vol:.1f} dB   (-inf = pure silence)")
    print(f"artifact: {webm}")

    # Ground-truth assertions: real, non-silent audio of a sane length.
    nonsilent = cap_vol > -60.0
    enough_dur = cap_dur >= min(src_dur, 6.0) * 0.6
    print("")
    if nonsilent and enough_dur:
        print("RESULT: PASS — real audio captured & measured. Ground-truth audio")
        print("        verification is FEASIBLE on this machine.")
        return 0
    print("RESULT: FAIL — capture was silent or too short. Need a different")
    print(f"        audio-capture approach.  nonsilent={nonsilent} enough_dur={enough_dur}")
    return 1


if __name__ == "__main__":
    sys.exit(run())
