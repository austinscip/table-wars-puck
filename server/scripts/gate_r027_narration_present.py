"""Gate for R027 — every Speed Pyramid question has narration (no 404).

116 of 1296 questions lack a narration MP3 and 404, leaving the host
silent on ~9% of questions. R027 makes sp_load_question prefer a question
that actually has an MP3. This gate drives a full match and asserts every
question served has a present MP3 (HTTP 200) — zero 404s.

Gate assertion name: every-served-question-has-narration
Run with sandbox Flask up on :5002.
"""
from __future__ import annotations

import sys
import time

import requests
from playwright.sync_api import sync_playwright, Page


BASE = "http://localhost:5002"
TV = f"{BASE}/tv/speed-pyramid"
HUB = f"{TV}/dev/hub"


def log(m: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def puck_row(page: Page, idx: int):
    return page.locator("main > div").nth(idx)


def puck_state(page: Page, idx: int) -> str:
    try:
        return puck_row(page, idx).locator("span.text-cyan-300").first.inner_text(timeout=1500)
    except Exception:
        return ""


def mp3_present(audio_url: str) -> bool:
    url = audio_url if audio_url.startswith("http") else f"{BASE}{audio_url}"
    try:
        return requests.head(url, timeout=4).status_code == 200
    except Exception:
        return False


def run() -> int:
    requests.post(f"{BASE}/api/pair/clear", json={}, timeout=5)
    questions: dict[int, str] = {}  # qid -> audio_url

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--autoplay-policy=no-user-gesture-required"])
        ctx = browser.new_context(viewport={"width": 1600, "height": 900})
        hub = ctx.new_page()
        tv = ctx.new_page()

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
        hub.goto(HUB, wait_until="domcontentloaded")
        tv.goto(TV + "/", wait_until="domcontentloaded")
        time.sleep(0.8)

        puck_row(hub, 0).get_by_role("button", name="Hold 1s").click(); time.sleep(0.5)
        puck_row(hub, 0).locator("button", has_text="Confirm").click(); time.sleep(0.6)
        puck_row(hub, 1).get_by_role("button", name="Hold 1s").click(); time.sleep(0.8)
        puck_row(hub, 0).get_by_role("button", name="Start match", exact=True).click(); time.sleep(1.2)
        sc = requests.get(f"{BASE}/api/pair/lobby-state", timeout=5).json().get("session_code")
        if not sc:
            log("INCONCLUSIVE: no session_code"); browser.close(); return 2
        tv.goto(f"{TV}/question/{sc}", wait_until="domcontentloaded")

        answered: set[int] = set()
        deadline = time.time() + 200
        while time.time() < deadline:
            if "/scoreboard/" in tv.evaluate("() => location.pathname"):
                break
            s1, s2 = puck_state(hub, 0), puck_state(hub, 1)
            if "MATCH ENDED" in s1 and "MATCH ENDED" in s2:
                break
            if "PICK CATEGORY" in s1 or "PICK CATEGORY" in s2:
                pd = time.time() + 13
                while time.time() < pd:
                    if ("PICK CATEGORY" not in puck_state(hub, 0)
                            and "PICK CATEGORY" not in puck_state(hub, 1)):
                        break
                    for pidx in (0, 1):
                        btns = puck_row(hub, pidx).locator("button[title]")
                        if btns.count() > 0:
                            try: btns.first.click(force=True, timeout=1200)
                            except Exception: pass
                    time.sleep(0.5)
                time.sleep(1.0); continue
            if "MINIGAME" in s1 or "MINIGAME" in s2:
                for idx in (0, 1):
                    for label in ("Fire", "Tap", "TAP"):
                        try:
                            puck_row(hub, idx).get_by_role("button", name=label, exact=False).first.click(timeout=1000); break
                        except Exception: continue
                time.sleep(2.0); continue
            if "ANSWERING" in s1 and "ANSWERING" in s2:
                for idx, L in ((0, "A"), (1, "B")):
                    try: puck_row(hub, idx).get_by_role("button", name=L, exact=True).click(force=True, timeout=2500)
                    except Exception: pass
                time.sleep(2.5); continue
            time.sleep(0.4)
        browser.close()

    log(f"distinct questions served: {len(questions)}")
    missing = {qid: u for qid, u in questions.items() if not mp3_present(u)}
    for qid, u in questions.items():
        mark = "404" if qid in missing else "200"
        log(f"   q_{qid}: {mark}  {u.split('/')[-1]}")

    log("")
    if len(questions) < 6:
        log(f"INCONCLUSIVE: only {len(questions)} questions served (match didn't run)")
        return 2
    if missing:
        log(f"RESULT: FAIL — {len(missing)} served question(s) have NO narration MP3 (404): {list(missing)}")
        return 1
    log(f"RESULT: PASS — all {len(questions)} served questions have a present narration MP3.")
    log("        gate: every-served-question-has-narration")
    return 0


if __name__ == "__main__":
    sys.exit(run())
