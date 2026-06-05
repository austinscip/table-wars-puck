"""
GameRegistry — a single source of truth for which games exist in this
runtime, looked up by slug.

A global singleton `registry` is exported. Game modules register
themselves at import time:

    from server.runtime import registry, Game

    class SpeedPyramid(Game):
        slug = "speed_pyramid"
        ...

    registry.register(SpeedPyramid)

The Flask app imports all game modules once at startup so they self-
register before any request hits the runtime.
"""

from __future__ import annotations

from typing import Type

from .game import Game


class GameRegistry:
    def __init__(self) -> None:
        self._games: dict[str, Type[Game]] = {}

    def register(self, game_class: Type[Game]) -> None:
        if not game_class.slug:
            raise ValueError(
                f"{game_class.__name__} has empty slug; set a class attribute"
            )
        if game_class.slug in self._games:
            raise ValueError(
                f"Game slug {game_class.slug!r} already registered "
                f"({self._games[game_class.slug].__name__})"
            )
        self._games[game_class.slug] = game_class

    def get(self, slug: str) -> Type[Game]:
        if slug not in self._games:
            raise KeyError(f"No game registered with slug {slug!r}")
        return self._games[slug]

    def list_slugs(self) -> list[str]:
        return sorted(self._games.keys())


# Module-level singleton.
registry = GameRegistry()
