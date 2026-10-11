"""
Dominion Theory: Maps: Settings

    Provides map generation settings.

"""

from dataclasses import dataclass

from .biomes import Biomes
from .noise import Elevation, Moisture


@dataclass
class Settings:
    """
    Maps Settings Keeper
    """

    # noise settings
    lacunarity: float = 2.0
    elevation: Elevation = Elevation()
    moisture: Moisture = Moisture()

    # biomes settings
    rivers: int = 8
    biomes: Biomes = Biomes()


settings = Settings()
