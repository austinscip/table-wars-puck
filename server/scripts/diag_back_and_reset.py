"""Diagnostic: reproduce bugs 17 (Back to start no-op) and 18 (re-pair
after Reset all fails) through the Hub UI.

Run with sandbox Flask up on :5002:
    cd ~/table-wars-puck-sandbox/server
    venv/bin/python scripts/diag_back_and_reset.py
"""
from __future__ import annotations

import json
import sys
import time

import requests
from playwright.sync_api import sync_playwright, Page, Request, Response


BASE = "http://localhost:5002"
TV = f"{BASE}/tv/speed-pyramid"
HUB = f"{TV}/dev/hub"


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def reset() -> None:
    requests.post(f"{BASE}/api/pair/clear", json={}, timeout=5)


def attach_log(page: Page, label: str, sink: list[dict]) -> None:
    def on_req(req: Request) -> None:
        if any(x in req.url for x in ("/api/sp/", "/api/pair/")):
            sink.append({"label": label, "phase": "req", "url": req.url,
                         "method": req.method, "body": req.post_data, "ts": time.time()})
            log(f"{label} -> {req.method} {req.url.split(BASE)[-1]} body={req.post_data}")
    def on_resp(resp: Response) -> None:
        if any(x in resp.url for x in ("/api/sp/", "/api/pair/")):
            try: body = resp.text()
            except Exception as e: body = f"<err {e}>"
            if resp.request.method != "GET":
                sink.append({"label": label, "phase": "resp", "url": resp.url,
                             "status": resp.status, "body": body[:400], "ts": time.time()})
                log(f"{label} <- {resp.status} {resp.url.split(BASE)[-1]} body={body[:180]}")
    page.on("request", on_req)
    page.on("response", on_resp)


def puck_row(page: Page, idx: int):
    return page.locator("main > div").nth(idx)


def puck_state(page: Page, idx: int) -> str:
    try:
        return puck_row(page, idx).locator("span.text-cyan-300").first.inner_text(timeout=1000)
    except Exception:
        return ""


def get_sc() -> str | None:
    return requests.get(f"{BASE}/api/pair/lobby-state", timeout=5).json().get("session_code")


def drive_full_match_rest(sc: str) -> None:
    requests.post(f"{BASE}/api/sp/reset/{sc}", timeout=5)
    for r in range(7):
        lq = requests.post(f"{BASE}/api/sp/load-question/{sc}", timeout=5).json()
        if "question" not in lq: return
        qid = lq["question"]["id"]
        requests.post(f"{BASE}/api/sp/answer", json={
            "session_code": sc, "puck_id": 1, "question_id": qid,
            "answer": "A", "response_time_ms": 1000}, timeout=5)
        requests.post(f"{BASE}/api/sp/answer", json={
            "session_code": sc, "puck_id": 2, "question_id": qid,
            "answer": "B", "response_time_ms": 1500}, timeout=5)
        time.sleep(0.2)
    requests.post(f"{BASE}/api/sp/load-question/{sc}", timeout=5)  # 409


def pair_via_hub(hub: Page) -> None:
    log("pair flow")
    puck_row(hub, 0).get_by_role("button", name="Hold 1s").click()
    time.sleep(0.6)
    puck_row(hub, 0).locator("button", has_text="Confirm").click()
    time.sleep(0.8)
    puck_row(hub, 1).get_by_role("button", name="Hold 1s").click()
    time.sleep(1.0)
    puck_row(hub, 0).get_by_role("button", name="Start match").click()
    time.sleep(1.2)


def run() -> int:
    reset()
    network: list[dict] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--autoplay-policy=no-user-gesture-required"],
        )
        ctx = browser.new_context()
        hub = ctx.new_page()
        attach_log(hub, "HUB", network)
        hub.goto(HUB, wait_until="domcontentloaded")
        time.sleep(1.0)

        # ===== Setup: run a match to MATCH_ENDED =====
        pair_via_hub(hub)
        sc = get_sc()
        log(f"match sc={sc}")
        drive_full_match_rest(sc)
        time.sleep(2.0)
        log(f"after match puck1={puck_state(hub, 0)!r} puck2={puck_state(hub, 1)!r}")

        # ===== BUG 17: Back to start =====
        log("--- BUG 17: click 'Back to start' on puck1 ---")
        s_before = puck_state(hub, 0)
        try:
            puck_row(hub, 0).get_by_role("button", name="Back to start").click(timeout=3000)
            log("Back to start click: dispatched")
        except Exception as e:
            log(f"Back to start click err: {e!r}")
        time.sleep(1.5)
        s_after = puck_state(hub, 0)
        log(f"BUG 17 puck1: before={s_before!r} after={s_after!r}")
        # also: did /api/sp/leave-match get called?
        leave_calls = [e for e in network if "/api/sp/leave-match" in e["url"] and e["phase"] == "req"]
        log(f"BUG 17 leave-match POSTs: {len(leave_calls)}")
        # Hub-level state dump
        all_state_html = hub.evaluate("() => document.body.innerText.substring(0, 800)")
        log(f"BUG 17 hub state snippet:\n{all_state_html[:400]}")

        # ===== BUG 18: Reset all + re-pair =====
        log("--- BUG 18: Reset all + re-pair ---")
        hub.get_by_role("button", name="Reset all").click()
        time.sleep(1.0)
        log(f"BUG 18 post-reset puck1={puck_state(hub, 0)!r} puck2={puck_state(hub, 1)!r}")
        # Now try to re-pair
        log("BUG 18 puck1 Hold 1s")
        before_pair = len(network)
        try:
            puck_row(hub, 0).get_by_role("button", name="Hold 1s").click(timeout=3000)
            log("BUG 18 Hold 1s click: dispatched")
        except Exception as e:
            log(f"BUG 18 Hold 1s err: {e!r}")
        time.sleep(1.0)
        log(f"BUG 18 after Hold 1s puck1={puck_state(hub, 0)!r}")
        try:
            puck_row(hub, 0).locator("button", has_text="Confirm").click(timeout=3000)
            log("BUG 18 Confirm click: dispatched")
        except Exception as e:
            log(f"BUG 18 Confirm err: {e!r}")
        time.sleep(1.0)
        log(f"BUG 18 after Confirm puck1={puck_state(hub, 0)!r}")
        try:
            puck_row(hub, 1).get_by_role("button", name="Hold 1s").click(timeout=3000)
            log("BUG 18 puck2 Hold 1s: dispatched")
        except Exception as e:
            log(f"BUG 18 puck2 Hold 1s err: {e!r}")
        time.sleep(1.5)
        log(f"BUG 18 after puck2 join puck1={puck_state(hub, 0)!r} puck2={puck_state(hub, 1)!r}")

        # Try to start match
        try:
            puck_row(hub, 0).get_by_role("button", name="Start match").click(timeout=3000)
            log("BUG 18 Start match: dispatched")
        except Exception as e:
            log(f"BUG 18 Start match err: {e!r}")
        time.sleep(1.5)
        log(f"BUG 18 post-start puck1={puck_state(hub, 0)!r} puck2={puck_state(hub, 1)!r}")

        # network after Reset all
        post_reset_traffic = [e for e in network[before_pair:] if e["phase"] == "req"]
        log(f"BUG 18 traffic after Reset all ({len(post_reset_traffic)} req):")
        for e in post_reset_traffic[:20]:
            print(f"  {e['method']} {e['url'].split(BASE)[-1]} body={e['body']}")

        browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(run())
