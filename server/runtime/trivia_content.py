"""
TriviaContentCache — Supabase-sourced trivia with a local cache (ADR 0008).

Content lives in Supabase (the source of truth), but the venue box must keep
serving trivia through an internet drop (local-first, ADR 0004). So the box
syncs the whole active question bank into memory + a JSON file, and selects
every match's questions from that cache — gameplay never waits on (or fails
because of) the cloud.

Sync model:
- refresh(): pull the bank + the content-version fingerprint from the reader,
  update memory + the JSON file. Best-effort: any failure leaves the existing
  cache intact (so an outage degrades to stale-but-working, never empty).
- load(): select `count` questions from the cached bank (filter by
  difficulty, drop exclude_ids, random sample). Returns None when the cache
  is empty AND no JSON file exists — the caller then falls back to the legacy
  SQLite bank / built-in defaults.

The reader is anything exposing get_active_trivia_questions() ->
list[dict] and trivia_content_version() -> str (the SupabaseWriter).
"""

from __future__ import annotations

import json
import os
import random
from typing import Optional, Protocol

from .log import get_logger

logger = get_logger("trivia_content")


class TriviaReader(Protocol):
    def get_active_trivia_questions(self) -> list[dict]: ...
    def trivia_content_version(self) -> str: ...


# Keys a cached question row must have to be usable (audit 2.8 — never trust
# the cache file blindly; a corrupt/poisoned row must be skipped, not crash
# match creation).
_REQUIRED_KEYS = (
    "id", "question_text",
    "answer_a", "answer_b", "answer_c", "answer_d", "correct_answer",
)


def _default_cache_path() -> str:
    """An app-private path (NOT world-writable /tmp, audit 2.8). Overridable
    via TRIVIA_CACHE_PATH."""
    env = os.environ.get("TRIVIA_CACHE_PATH")
    if env:
        return env
    base = os.path.join(os.path.expanduser("~"), ".tablewars")
    return os.path.join(base, "trivia_cache.json")


def _valid_row(row: object) -> bool:
    return isinstance(row, dict) and all(
        row.get(k) is not None for k in _REQUIRED_KEYS
    )


class TriviaContentCache:
    def __init__(
        self, reader: TriviaReader, cache_path: Optional[str] = None
    ) -> None:
        self._reader = reader
        self._cache_path = cache_path or _default_cache_path()
        self._bank: list[dict] = []
        self._version: str = ""
        self._load_cache_file()  # warm from disk so a cold boot offline works

    # === Sync ===

    def refresh(self, force: bool = False) -> bool:
        """Pull the bank from the cloud if the content version moved (or
        force). Returns True if the bank was updated. Best-effort: on any
        error the existing cache is kept and we return False."""
        try:
            remote_version = self._reader.trivia_content_version()
            if not force and self._bank and remote_version == self._version:
                return False  # already current
            bank = self._reader.get_active_trivia_questions()
            if not bank:
                return False  # never blow away a good cache with an empty pull
            self._bank = bank
            self._version = remote_version
            self._save_cache_file()
            logger.info(
                "trivia cache refreshed: %d questions (version %s)",
                len(bank),
                remote_version,
            )
            return True
        except Exception:  # noqa: BLE001
            logger.exception("trivia cache refresh failed; keeping cache")
            return False

    # === Selection ===

    def load(
        self,
        count: int,
        *,
        difficulty: Optional[str] = None,
        category_id: Optional[int] = None,  # accepted for signature parity
        exclude_ids: Optional[list[int]] = None,
    ) -> Optional[list[dict]]:
        """Select up to `count` questions from the cached bank. Returns None
        when the cache is empty/unusable so the caller can fall back. Never
        raises — bad cache data degrades to the fallback, it doesn't 500 a
        match (audit 2.8)."""
        try:
            if not self._bank:
                # Lazy first sync (e.g. the container didn't pre-warm).
                self.refresh()
            # Snapshot the bank reference once so a concurrent refresh() that
            # reassigns self._bank can't change what we iterate.
            bank = self._bank
            if not bank:
                return None
            excluded = set(exclude_ids or [])
            pool = [
                q
                for q in bank
                if _valid_row(q)
                and (difficulty is None or q.get("difficulty") == difficulty)
                and int(q["id"]) not in excluded
            ]
            if not pool:
                # Exclusions/filters emptied the pool — relax exclusions
                # before giving up, so a player who's seen everything still
                # gets a game.
                pool = [
                    q for q in bank
                    if _valid_row(q)
                    and (difficulty is None or q.get("difficulty") == difficulty)
                ]
            if not pool:
                return None
            k = min(count, len(pool))
            return random.sample(pool, k)
        except Exception:  # noqa: BLE001
            logger.exception("trivia load failed; falling back")
            return None

    @property
    def version(self) -> str:
        return self._version

    @property
    def size(self) -> int:
        return len(self._bank)

    # === Local cache file ===

    def _load_cache_file(self) -> None:
        try:
            with open(self._cache_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            raw = data.get("bank", [])
            # Validate every row (audit 2.8): a corrupt/poisoned cache file
            # must not inject bad rows that crash selection later.
            self._bank = [r for r in raw if _valid_row(r)]
            self._version = data.get("version", "")
            if self._bank:
                logger.info(
                    "trivia cache loaded from disk: %d questions", len(self._bank)
                )
        except FileNotFoundError:
            pass
        except Exception:  # noqa: BLE001
            logger.exception("failed to read trivia cache file")

    def _save_cache_file(self) -> None:
        try:
            os.makedirs(os.path.dirname(self._cache_path) or ".", exist_ok=True)
            tmp = f"{self._cache_path}.tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump({"version": self._version, "bank": self._bank}, fh)
            os.replace(tmp, self._cache_path)  # atomic
        except Exception:  # noqa: BLE001
            logger.exception("failed to write trivia cache file")
