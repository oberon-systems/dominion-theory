"""
From layers to a biome: the first biome, by order of generation, whose ranges all hold.
"""

from collections.abc import Mapping

import numpy as np
from numpy.typing import NDArray

from ..content import Biome
from .noise import Floats


def ordered(biomes: Mapping[str, Biome]) -> tuple[str, ...]:
    """
    The identifiers by order of generation; a biome code is a position here.
    """
    return tuple(sorted(biomes, key=lambda name: biomes[name].generation.order))


def classify(biomes: Mapping[str, Biome], layers: Mapping[str, Floats]) -> NDArray[np.uint8]:
    names = ordered(biomes)
    shape = next(iter(layers.values())).shape
    codes = np.zeros(shape, dtype=np.uint8)

    # The first biome that matches wins, so they are laid from the last to the first.
    for code in reversed(range(len(names))):
        match = np.ones(shape, dtype=bool)
        for layer, held in biomes[names[code]].generation.ranges.items():
            if held.min is not None:
                match &= layers[layer] >= held.min
            if held.max is not None:
                match &= layers[layer] <= held.max
        codes[match] = code

    return codes
