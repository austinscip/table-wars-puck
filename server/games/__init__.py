"""
Game implementations on the multi-game runtime. Importing this package
imports every game module so their registry.register() calls fire and
runtime/registry.get(slug) sees them all.

To add a new game:
  1. Create server/games/<slug>.py with a class deriving from Game.
  2. Call registry.register(YourGame) at module load.
  3. Add the import below.
"""

from . import speed_pyramid  # noqa: F401

__all__ = ["speed_pyramid"]
