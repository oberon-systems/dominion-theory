"""
Dominion Theory: Planet Generation Module

    Provides:
        * Planet: the planet of a seed and its parameters, read by place and cell size.
        * Region: what the planet answers for a rectangle of cells.
        * biome_names: the biome identifiers of a tree, by order of generation.
        * place: the north-west cell of the first window of a seed.
"""

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from ..content import Params
from .noise import Floats
from .rivers import Rivers, rivers
from .rules import classify, ordered
from .skeleton import Skeleton, skeleton
from .window import choose, misses

WATER = 'water'


def biome_names(params: Params) -> tuple[str, ...]:
    return ordered(params.biomes)


@dataclass(frozen=True)
class Region:
    """
    A rectangle of cells: the restated layers, the biomes as positions in biome_names, the river marks.
    """

    elevation: Floats
    relief: Floats
    moisture: Floats
    temperature: Floats
    biomes: NDArray[np.uint8]
    rivers: NDArray[np.bool_]


class Planet:
    """
    A function of the seed, a place and a cell size. Nothing is kept for land nobody looks at.
    """

    def __init__(self, seed: int, params: Params) -> None:
        self.seed = seed
        self.params = params
        self.circumference_km = params.planet.circumference_km
        self.biomes = biome_names(params)

    @property
    def skeleton(self) -> Skeleton:
        planet = self.params.planet
        return skeleton(
            self.seed,
            planet.circumference_km,
            planet.skeleton_km,
            planet.sea,
            planet.elevation,
            planet.relief,
            planet.moisture,
            planet.temperature,
        )

    @property
    def rivers(self) -> Rivers:
        planet = self.params.planet
        return rivers(
            self.seed,
            planet.circumference_km,
            planet.skeleton_km,
            planet.sea,
            planet.elevation,
            planet.relief,
            planet.moisture,
            planet.temperature,
            planet.rivers.share,
            planet.rivers.meander_km,
        )

    def read(self, x: int, y: int, width: int, height: int, cell_km: int) -> Region:
        """
        Cells of cell_km to a side from the north-west one at x, y. A cell reads the planet at its centre.
        """
        across = self.circumference_km // cell_km
        if y < 0 or y + height > across // 2:
            raise ValueError(f'rows {y} to {y + height} do not lie between the poles')
        columns = (x + np.arange(width)) % across
        east, south = np.meshgrid((columns + 0.5) * cell_km, (y + np.arange(height) + 0.5) * cell_km)
        layers = self.skeleton.restate(east, south)
        biomes = classify(self.params.biomes, layers)
        marks = self.rivers.marks(x, y, width, height, cell_km)
        if WATER in self.biomes:
            marks &= biomes != self.biomes.index(WATER)
        return Region(
            elevation=layers['elevation'],
            relief=layers['relief'],
            moisture=layers['moisture'],
            temperature=layers['temperature'],
            biomes=biomes,
            rivers=marks,
        )


def place(seed: int, params: Params) -> tuple[int, int]:
    """
    The north-west cell of the first window, in cells of the band era: given by hand or tried from the seed.
    """
    planet = Planet(seed, params)
    return choose(seed, params, lambda x, y: misses(planet.skeleton, planet.rivers, params, x, y))


__all__ = ['Planet', 'Region', 'biome_names', 'place']
