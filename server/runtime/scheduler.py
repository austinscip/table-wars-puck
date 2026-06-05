"""
TickScheduler — runs game.tick() at a fixed cadence per active match.

Flask is sync, so we can't sprinkle await inside route handlers. Instead
a single daemon thread runs the tick loop. Per match it calls
MatchManager.tick(match_id) at TICK_HZ; the manager handles state
update + score persistence + snapshot write.

Inactive matches (status != 'active') are skipped without unregistering
so a match coming back to active gets ticks again. Finalised matches
unregister themselves through the manager's lifecycle.
"""

from __future__ import annotations

import threading
import time
from typing import Optional, Set

from .log import get_logger
from .match import MatchManager

logger = get_logger("scheduler")


class TickScheduler:
    TICK_HZ = 10  # ticks per second per match
    TICK_INTERVAL = 1.0 / TICK_HZ

    def __init__(self, match_manager: MatchManager) -> None:
        self.match_manager = match_manager
        self._active: Set[str] = set()
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    # === Registration ===

    def register(self, match_id: str) -> None:
        with self._lock:
            self._active.add(match_id)

    def unregister(self, match_id: str) -> None:
        with self._lock:
            self._active.discard(match_id)

    # === Loop ===

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run, daemon=True, name="runtime-tick"
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None

    def _run(self) -> None:
        while not self._stop.is_set():
            tick_start = time.perf_counter()
            with self._lock:
                snapshot = list(self._active)

            for match_id in snapshot:
                match = self.match_manager.matches.get(match_id)
                if match is None:
                    # Manager has finalised + removed it; clean up.
                    with self._lock:
                        self._active.discard(match_id)
                    continue
                if match.status != "active":
                    continue
                try:
                    self.match_manager.tick(match_id)
                except Exception:  # noqa: BLE001
                    # A buggy game must not crash the scheduler thread —
                    # the whole table would freeze. Log with traceback
                    # (and ship to Sentry if configured) and keep ticking
                    # the other matches.
                    logger.exception(
                        "tick(%s) raised; continuing", match_id
                    )

            # Sleep the remaining slice of this tick. If a tick took
            # longer than TICK_INTERVAL (heavy game tick), don't sleep —
            # let the next iteration run immediately.
            elapsed = time.perf_counter() - tick_start
            remaining = self.TICK_INTERVAL - elapsed
            if remaining > 0:
                self._stop.wait(remaining)
