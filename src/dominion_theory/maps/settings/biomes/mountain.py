"""
Biome Definition
"""

from dataclasses import dataclass

from .base import Biome, BiomeProperties, Elevation


@dataclass(frozen=True)
class Mountain(Biome):
    """
    Mountain Biome Settings Keeper
    """
    # visualization settings
    color: str = '#8B8989'

    elevation: Elevation = Elevation(min=0.0, max=0.15)

    # biome properties
    properties: BiomeProperties = BiomeProperties(
        water=0.2,
        food=0.2,
        threat=0.7,
        passability=0.3,
    )
