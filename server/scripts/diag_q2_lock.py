"""Diagnostic: drive the Virtual Puck Hub through 2+ questions and
record every /api/sp/answer POST (status + response body).

Purpose: reproduce "can't lock answers past Q1 in the Hub". Server-side
sp_load_question is now idempotent (commit ec32224); this script
verifies end-to-end whether the Hub's Q2 lock works through a real
browser, or whether a second cause exists.

Throwaway. Not part of the e2e gate.

Run with sandbox Flask up on :5002 and dist/ built with VITE_DEV_TOOLS=1:

    cd ~/table-wars-puck-sandbox/server
    venv/bin/python scripts/diag_q2_lock.py
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


def reset_state() -> None:
    requests.post(f"{BASE}/api/pair/clear", json={}, timeout=5)


def attach_network_log(page: Page, label: str, sink: list[dict]) -> None:
    def on_request(req: Request) -> None:
        if "/api/sp/answer" in req.url or "/api/sp/load-question" in req.url:
            sink.append({
                "label": label, "phase": "request", "url": req.url,
                "body": req.post_data, "ts": time.time(),
            })
            log(f"{label} -> POST {req.url.split(BASE)[-1]} body={req.post_data}")

    def on_response(resp: Response) -> None:
        if "/api/sp/answer" in resp.url or "/api/sp/load-question" in resp.url:
            try:
                body = resp.text()
            except Exception as e:
                body = f"<text err: {e}>"
            sink.append({
                "label": label, "phase": "response", "url": resp.url,
                "status": resp.status, "body": body[:600], "ts": time.time(),
            })
            log(f"{label} <- {resp.status} {resp.url.split(BASE)[-1]} body={body[:240]}")

    page.on("request", on_request)
    page.on("response", on_response)


def puck_row(page: Page, idx: int):
    """Return locator for puck N's row (VariantA layout)."""
    return page.locator("main > div").nth(idx)


def puck_state_text(page: Page, idx: int) -> str:
    """Read the cyan state badge text for puck N. Empty string on miss."""
    try:
        return puck_row(page, idx).locator("span.text-cyan-300").first.inner_text(timeout=1000)
    except Exception:
        return ""


def wait_for_state(page: Page, idx: int, substr: str, timeout_s: float = 8) -> str:
    deadline = time.time() + timeout_s
    last = ""
    while time.time() < deadline:
        last = puck_state_text(page, idx)
        if substr in last:
            return last
        time.sleep(0.2)
    return last  # timeout — return last seen


def run() -> int:
    reset_state()
    log("state cleared. opening Hub + TV")

    network: list[dict] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context()

        hub = ctx.new_page()
        tv = ctx.new_page()
        attach_network_log(hub, "HUB", network)
        attach_network_log(tv, "TV ", network)

        hub.goto(HUB, wait_until="domcontentloaded")
        tv.goto(TV + "/", wait_until="domcontentloaded")
        time.sleep(1.5)  # React mount + first poll

        log(f"puck1 state on mount: {puck_state_text(hub, 0)!r}")
        log(f"puck2 state on mount: {puck_state_text(hub, 1)!r}")

        # --- Pair: puck1 hold1s -> DIALING -> Confirm ---
        log("click puck1 'Hold 1s'")
        puck_row(hub, 0).get_by_role("button", name="Hold 1s").click()
        time.sleep(0.6)
        s = puck_state_text(hub, 0)
        log(f"puck1 after Hold 1s: {s!r}")

        # Confirm button label is "Confirm <code>"
        log("click puck1 Confirm-code button")
        puck_row(hub, 0).locator("button", has_text="Confirm").click()
        time.sleep(0.8)
        log(f"puck1 after confirm: {puck_state_text(hub, 0)!r}")

        # --- Puck2 joiner ---
        log("click puck2 'Hold 1s' (auto-joiner)")
        puck_row(hub, 1).get_by_role("button", name="Hold 1s").click()
        time.sleep(0.8)
        log(f"puck2 after hold: {puck_state_text(hub, 1)!r}")

        # --- Host starts match ---
        log("click puck1 'Start match'")
        puck_row(hub, 0).get_by_role("button", name="Start match").click()
        time.sleep(1.2)
        log(f"puck1 post-start: {puck_state_text(hub, 0)!r}")

        # The TV is the canonical caller of load-question. Give it 6s, then REST-load if it doesn't.
        s = wait_for_state(hub, 0, "ANSWERING", timeout_s=6)
        if "ANSWERING" not in s:
            ls = requests.get(f"{BASE}/api/pair/lobby-state", timeout=5).json()
            sc = ls.get("session_code")
            log(f"no ANSWERING in 6s — REST-load Q1 on sc={sc}")
            if sc:
                requests.post(f"{BASE}/api/sp/load-question/{sc}", timeout=5)
            s = wait_for_state(hub, 0, "ANSWERING", timeout_s=6)
        log(f"Q1 puck1 state: {s!r}")
        log(f"Q1 puck2 state: {puck_state_text(hub, 1)!r}")

        # --- Q1 lock both answers ---
        log("Q1: puck1 click 'A', puck2 click 'B'")
        try:
            puck_row(hub, 0).get_by_role("button", name="A", exact=True).click()
        except Exception as e:
            log(f"puck1 A click err: {e!r}")
        time.sleep(0.5)
        try:
            puck_row(hub, 1).get_by_role("button", name="B", exact=True).click()
        except Exception as e:
            log(f"puck2 B click err: {e!r}")
        time.sleep(2.5)
        log(f"Q1 post-lock puck1: {puck_state_text(hub, 0)!r}")
        log(f"Q1 post-lock puck2: {puck_state_text(hub, 1)!r}")

        # --- Q2 load + answer ---
        ls = requests.get(f"{BASE}/api/pair/lobby-state", timeout=5).json()
        sc = ls.get("session_code")
        log(f"Q2: REST load-question on sc={sc}")
        if sc:
            r = requests.post(f"{BASE}/api/sp/load-question/{sc}", timeout=5)
            log(f"Q2 load resp status={r.status_code} body={r.text[:300]}")
        time.sleep(1.5)
        s2 = wait_for_state(hub, 0, "ANSWERING Q", timeout_s=6)
        log(f"Q2 puck1 state: {s2!r}")
        log(f"Q2 puck2 state: {puck_state_text(hub, 1)!r}")

        # THIS is the regression site.
        log("Q2: puck1 click 'A', puck2 click 'C' — THE BUG SITE")
        try:
            puck_row(hub, 0).get_by_role("button", name="A", exact=True).click(timeout=3000)
            log("puck1 Q2 A click: dispatched")
        except Exception as e:
            log(f"puck1 Q2 A click err: {e!r}")
        time.sleep(0.5)
        try:
            puck_row(hub, 1).get_by_role("button", name="C", exact=True).click(timeout=3000)
            log("puck2 Q2 C click: dispatched")
        except Exception as e:
            log(f"puck2 Q2 C click err: {e!r}")

        time.sleep(2.5)
        log(f"Q2 post-lock puck1: {puck_state_text(hub, 0)!r}")
        log(f"Q2 post-lock puck2: {puck_state_text(hub, 1)!r}")

        log("===== /api/sp/{answer,load-question} traffic =====")
        for entry in network:
            print(json.dumps(entry, indent=2))
        log(f"===== total events: {len(network)} =====")

        hub.screenshot(path="/tmp/diag_hub_final.png", full_page=True)
        tv.screenshot(path="/tmp/diag_tv_final.png", full_page=True)
        log("screenshots: /tmp/diag_hub_final.png /tmp/diag_tv_final.png")

        browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(run())
