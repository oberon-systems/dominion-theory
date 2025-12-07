"""
Dominion Theory: Maps: Generator

    The maps data generator it-self.
"""

from dataclasses import fields

import numpy as np
from numpy import ndarray

from .settings.biomes import Biomes


# pylint: disable-next=too-many-arguments,too-many-positional-arguments
def generator(
    height: int,
    width: int,
    elevation: ndarray,
    moisture: ndarray,
    biomes: Biomes,
) -> ndarray:
    """
    Generate map data.
    """

    _biomes = np.zeros((height, width), dtype=object)

    for i in range(height):
        for j in range(width):
            elev = elevation[i, j]
            moist = moisture[i, j]

            for f in fields(biomes):
                biome = getattr(biomes, f.name)

                if hasattr(biome, 'elevation'):
                    if biome.elevation.min <= elev <= biome.elevation.max:
                        _biomes[i, j] = biome
                        break

                if hasattr(biome, 'moisture'):
                    if biome.moisture.min <= moist <= biome.moisture.max:
                        _biomes[i, j] = biome
                        break
            else:
                _biomes[i, j] = biomes.grass

    return _biomes
