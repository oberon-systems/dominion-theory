"""
Biome Definition
"""

from dataclasses import dataclass

from .base import Biome, BiomeProperties


@dataclass(frozen=True, repr=False)
class Grass(Biome):
    """
    Grass Biome Settings Keeper
    """
    # visualization settings
    color: str = '#228B22'

    # no any special landscape settings

    # biome properties
    properties: BiomeProperties = BiomeProperties(
        water=0.4,
        food=0.8,
        threat=0.1,
        passability=1.0,
    )
