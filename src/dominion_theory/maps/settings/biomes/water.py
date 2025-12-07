"""
Biome Definition
"""

from dataclasses import dataclass

from .base import Biome, BiomeProperties, Elevation


@dataclass(frozen=True, repr=False)
class Water(Biome):
    """
    Water Biome Settings Keeper
    """
    # visualization settings
    color: str = '#0077BE'

    # landscape settings
    elevation: Elevation = Elevation(min=-1.0, max=-0.2)

    # biome properties
    properties: BiomeProperties = BiomeProperties(
        water=1.0,
        food=0.3,
        threat=0.2,
        passability=0.1,
    )
