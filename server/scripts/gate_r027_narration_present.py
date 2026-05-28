"""Gate for R027 — every Speed Pyramid question has narration (no 404).

Drives a full match and HEAD-checks every served question's MP3.
sp_load_question prefers narrated questions (R027 fix); this gate
verifies the served-narration coverage is 100% in real play.

Gate assertion name: every-served-question-has-narration
"""
from __future__ import annotations

import sys
import time

import requests

from verify_lib import (
    BASE, log, session, pair_and_start, drive_match_to_scoreboard, Verifier,
)


def mp3_present(audio_url: str) -> bool:
    url = audio_url if audio_url.startswith("http") else f"{BASE}{audio_url}"
    try:
        return requests.head(url, timeout=4).status_code == 200
    except Exception:
        return False


def run() -> int:
    v = Verifier()
    questions: dict[int, str] = {}  # qid -> audio_url

    with session() as (hub, tv):
        def on_resp(resp):
            if "/api/sp/load-question" in resp.url:
                try:
                    b = resp.json()
                except Exception:
                    return
                qid = (b.get("question") or {}).get("id")
                if qid and b.get("audio_url"):
                    questions[qid] = b["audio_url"]
        tv.on("response", on_resp)

        if not pair_and_start(hub, tv):
            v.inconclusive("setup", "no session_code"); return v.report()
        drive_match_to_scoreboard(hub, tv)

    log(f"distinct questions served: {len(questions)}")
    missing = {qid: u for qid, u in questions.items() if not mp3_present(u)}
    for qid, u in questions.items():
        log(f"   q_{qid}: {'404' if qid in missing else '200'}  "
            f"{u.split('/')[-1]}")

    if len(questions) < 6:
        v.inconclusive("ran the match",
                       f"only {len(questions)} questions served")
    else:
        v.check("every-served-question-has-narration",
                not missing,
                f"missing={list(missing)}" if missing
                else f"all {len(questions)} served narrations are 200")
    return v.report()


if __name__ == "__main__":
    sys.exit(run())
