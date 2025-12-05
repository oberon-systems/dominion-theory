"""
Dominion Theory: Maps Generation Module

    Provides:
        * atlas: a callable map object that return
                 a generated map data.
        * settings: module settings object.
"""

from .generator import generator as map_generator
from .layers import generator as layer_generator
from .rivers import apply, create
from .settings import settings


# pylint: disable-next=too-few-public-methods
class Maps:
    """
    Main maps generation class.
    """

    def __call__(self, *args, **kwargs):
        _elevation = layer_generator(
            width=settings.width,
            height=settings.height,
            lacunarity=settings.lacunarity,
            **settings.elevation,
        )
        _moisture = layer_generator(
            width=settings.width,
            height=settings.height,
            lacunarity=settings.lacunarity,
            **settings.moisture,
        )

        _atlas = map_generator(
            height=settings.height,
            width=settings.width,
            biomes=settings.biomes,
            elevation=_elevation,
            moisture=_moisture,
            seed=settings.seed,
        )

        _rivers = create(
            height=settings.height,
            width=settings.width,
            num=settings.rivers,
            elevation=_elevation,
        )

        return apply(biomes=_atlas, rivers=_rivers)


atlas = Maps()


__all__ = ['atlas', 'settings']
