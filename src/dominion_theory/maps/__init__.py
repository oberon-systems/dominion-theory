"""
Dominion Theory: Maps Generation Module

    Provides:
        * atlas: a callable map object that return
                 a generated map data.
        * settings: module settings object.
"""

from ..core import logger
from .generator import generator as map_generator
from .layers import generator as layer_generator
from .rivers import apply, create
from .settings import settings

logger.name = 'maps'


# pylint: disable-next=too-few-public-methods
class Maps:
    """
    Main maps generation class.
    """

    def __call__(self, *args, **kwargs):
        logger.info('generate elevation layer: seed: %d', settings.seed)
        _elevation = layer_generator(
            width=settings.width,
            height=settings.height,
            lacunarity=settings.lacunarity,
            seed=settings.seed,
            **settings.elevation,
        )

        logger.info('generate moisture layer: seed: %d', settings.seed + 1)
        _moisture = layer_generator(
            width=settings.width,
            height=settings.height,
            lacunarity=settings.lacunarity,
            seed=settings.seed + 1,
            **settings.moisture,
        )

        logger.info('generate world atlas')
        _atlas = map_generator(
            height=settings.height,
            width=settings.width,
            biomes=settings.biomes,
            elevation=_elevation,
            moisture=_moisture,
        )

        logger.info('generate rivers')
        _rivers = create(
            height=settings.height,
            width=settings.width,
            num=settings.rivers,
            elevation=_elevation,
        )

        logger.info('apply rivers')
        return apply(biomes=_atlas, rivers=_rivers)


atlas = Maps()


__all__ = ['atlas', 'settings']
