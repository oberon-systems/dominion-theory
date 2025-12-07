"""
Biome Definition
"""

from dataclasses import dataclass

from .base import Biome, BiomeProperties, Moisture


@dataclass(frozen=True, repr=False)
class Forest(Biome):
    """
    Forest Biome Settings Keeper
    """
    # visualization settings
    color: str = '#006400'

    # landscape settings
    moisture: Moisture = Moisture(min=0.0, max=1.0)

    # biome properties
    properties: BiomeProperties = BiomeProperties(
        water=0.6,
        food=0.9,
        threat=0.4,
        passability=0.6,
    )
