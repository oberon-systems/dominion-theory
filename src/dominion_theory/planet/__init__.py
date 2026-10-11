"""
Dominion Theory: Planet Generation Module

    Provides:
        * generate: the biome codes of a map, the same for the same arguments.
        * atlas: a callable map object that return
                 a generated map data.
        * settings: module settings object.
"""

from dataclasses import fields

import numpy as np
from numpy.typing import NDArray

from ..core import logger
from .generator import generator as map_generator
from .layers import generator as layer_generator
from .rivers import apply, create
from .settings import settings

logger.name = 'planet'

BIOMES: tuple[str, ...] = tuple(field.name for field in fields(settings.biomes))


def generate(seed: int, width: int, height: int, rivers: np.random.Generator) -> NDArray[np.uint8]:
    """
    A map as positions in BIOMES. Nothing is drawn but from the seed and the stream given.
    """
    logger.info('generate elevation layer: seed: %d', seed)
    _elevation = layer_generator(
        width=width,
        height=height,
        lacunarity=settings.lacunarity,
        seed=seed,
        **settings.elevation,
    )

    logger.info('generate moisture layer: seed: %d', seed + 1)
    _moisture = layer_generator(
        width=width,
        height=height,
        lacunarity=settings.lacunarity,
        seed=seed + 1,
        **settings.moisture,
    )

    logger.info('generate world atlas')
    _atlas = map_generator(
        biomes=settings.biomes,
        elevation=_elevation,
        moisture=_moisture,
    )

    logger.info('generate rivers')
    _rivers = create(
        height=height,
        width=width,
        num=settings.rivers,
        elevation=_elevation,
        rng=rivers,
    )

    logger.info('apply rivers')
    return apply(biomes=_atlas, rivers=_rivers, water=BIOMES.index('water'))


class Maps:
    """
    Main maps generation class.
    """

    def __call__(self, seed: int, width: int, height: int, rivers: np.random.Generator) -> NDArray[np.object_]:
        table = np.empty(len(BIOMES), dtype=object)
        for code, name in enumerate(BIOMES):
            table[code] = getattr(settings.biomes, name)
        world: NDArray[np.object_] = table[generate(seed=seed, width=width, height=height, rivers=rivers)]
        return world


atlas = Maps()


__all__ = ['BIOMES', 'atlas', 'generate', 'settings']
