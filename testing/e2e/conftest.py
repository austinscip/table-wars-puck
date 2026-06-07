"""Browser-e2e fixtures: boot the REAL Flask+SocketIO app on a free port so a
headless browser (Playwright) can drive the actual TV bundle against it.

Kept OUT of the main `server/tests` suite (it needs a browser); run explicitly:
    cd server && . venv/bin/activate
    python -m playwright install chromium            # one time
    python -m pytest ../testing/e2e -q
"""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
import urllib.request

import pytest

_SERVER_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "server")
)


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture(scope="session")
def live_server() -> str:
    """Start `python app.py` on a free port and yield its base URL. Torn down
    at session end. mDNS + state-persistence disabled; sqlite dev DB (already
    seeded) is fine for an e2e."""
    port = _free_port()
    env = {
        **os.environ,
        "PORT": str(port),
        "HOST": "127.0.0.1",
        "DEBUG": "False",
        "SP_MDNS_DISABLE": "1",
        "SP_PERSIST_DISABLE": "1",
        "DATABASE_URL": "",  # force the local sqlite path
    }
    proc = subprocess.Popen(
        [sys.executable, "app.py"],
        cwd=_SERVER_DIR,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    base = f"http://127.0.0.1:{port}"
    # Wait for readiness.
    deadline = time.time() + 40
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError("app.py exited before becoming ready")
        try:
            with urllib.request.urlopen(base + "/", timeout=1) as r:
                if r.status == 200:
                    break
        except Exception:
            time.sleep(0.4)
    else:
        proc.terminate()
        raise RuntimeError("server did not become ready in time")
    try:
        yield base
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
