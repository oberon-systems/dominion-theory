"""
Dominion Theory: Maps: Generator

    The maps data generator it-self.
"""

from dataclasses import fields

import numpy as np
from numpy.typing import NDArray

from .settings.biomes import Biomes


def generator(
    height: int,
    width: int,
    elevation: NDArray[np.float64],
    moisture: NDArray[np.float64],
    biomes: Biomes,
) -> NDArray[np.object_]:
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

                if hasattr(biome, 'elevation') and biome.elevation.min <= elev <= biome.elevation.max:
                    _biomes[i, j] = biome
                    break

                if hasattr(biome, 'moisture') and biome.moisture.min <= moist <= biome.moisture.max:
                    _biomes[i, j] = biome
                    break
            else:
                _biomes[i, j] = biomes.grass

    return _biomes
