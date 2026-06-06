"""
Regression tests for the narration (VO) asset cache in pair_routes
(audit polish-2026-06-06):

  - the narrated-question set auto-invalidates when the questions directory
    changes, so regenerating narration on a running server is picked up
    without a restart (it used to cache once and require a restart, which also
    mis-drove the R027 question-substitution logic).
  - a 0-byte / truncated MP3 is NOT counted as narration.

Exercises the real pair_routes helpers against the real questions dir, using
clearly-fake high question ids and cleaning them up in a finally.
"""

from __future__ import annotations

import os

import pytest

pytest.importorskip("flask")

try:
    import pair_routes
except Exception as exc:  # pragma: no cover - env-dependent
    pytest.skip(f"pair_routes not importable here: {exc}", allow_module_level=True)


_QDIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "static", "games", "speed-pyramid", "audio", "questions",
)

_BIG = 99990017   # a real-sized fake narration file
_SMALL = 99990018  # a truncated/0-byte fake file


def _path(qid: int) -> str:
    return os.path.join(_QDIR, f"q_{qid}.mp3")


def test_narration_cache_invalidates_and_ignores_tiny_files():
    big, small = _path(_BIG), _path(_SMALL)
    try:
        # Prime the cache; neither fake id exists yet.
        pair_routes._narrated_qids()
        assert not pair_routes._has_narration(_BIG)
        assert not pair_routes._has_narration(_SMALL)

        # Drop a real-sized file and a truncated one into the dir.
        with open(big, "wb") as f:
            f.write(b"\x00" * (pair_routes._MIN_NARRATION_BYTES + 64))
        with open(small, "wb") as f:
            f.write(b"\x00" * 8)

        # The dir mtime changed -> the cache re-scans on the next call.
        assert pair_routes._has_narration(_BIG) is True
        # ...but the truncated file is below the size floor and is ignored.
        assert pair_routes._has_narration(_SMALL) is False
    finally:
        for p in (big, small):
            try:
                os.remove(p)
            except OSError:
                pass

    # After removal, another dir change -> re-scan -> no longer present.
    assert not pair_routes._has_narration(_BIG)
