"""
Dominion Theory: Maps: Generator

    The maps data generator it-self.
"""

from dataclasses import fields

import numpy as np
from numpy.typing import NDArray

from .settings.biomes import Biomes


def generator(
    elevation: NDArray[np.float64],
    moisture: NDArray[np.float64],
    biomes: Biomes,
) -> NDArray[np.uint8]:
    """
    Generate map data: for every cell the position of its biome among the fields of biomes.
    """
    names = [f.name for f in fields(biomes)]
    _biomes = np.full(elevation.shape, names.index('grass'), dtype=np.uint8)

    # The first biome that matches wins, so they are laid from the last to the first.
    for code in reversed(range(len(names))):
        biome = getattr(biomes, names[code])
        match = np.zeros(elevation.shape, dtype=bool)

        if hasattr(biome, 'elevation'):
            match |= (biome.elevation.min <= elevation) & (elevation <= biome.elevation.max)

        if hasattr(biome, 'moisture'):
            match |= (biome.moisture.min <= moisture) & (moisture <= biome.moisture.max)

        _biomes[match] = code

    return _biomes
