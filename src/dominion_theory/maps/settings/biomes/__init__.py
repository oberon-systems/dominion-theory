"""
Dominion Theory: Maps: Settings: Biomes
"""

from dataclasses import dataclass

from .forest import Forest
from .grass import Grass
from .mountain import Mountain
from .water import Water


@dataclass(frozen=True)
class Biomes:
    """
    Biomes Settings Keeper
    """

    forest: Forest = Forest()
    grass: Grass = Grass()
    mountain: Mountain = Mountain()
    water: Water = Water()


__all__ = [
    'Biomes',
]
