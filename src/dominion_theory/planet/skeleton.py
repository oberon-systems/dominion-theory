"""
The skeleton: the layers sampled on a coarse grid over the whole planet, and the shares read from it.
"""

from dataclasses import dataclass
from functools import lru_cache

import numpy as np
from numpy.typing import NDArray

from ..content import Layer, Temperature
from .layers import Layers, layers
from .noise import Floats

KEPT = 4


@dataclass(frozen=True)
class Skeleton:
    """
    Raw layers at the nodes, the sea level, and the tables that restate a raw value as a share.
    """

    layers: Layers
    elevation: Floats
    relief: Floats
    moisture: Floats
    sea_level: float
    heights: tuple[Floats, Floats]
    reliefs: Floats
    moistures: Floats

    @property
    def land(self) -> NDArray[np.bool_]:
        above: NDArray[np.bool_] = self.elevation > self.sea_level
        return above

    def restate(self, x: Floats, y: Floats) -> dict[str, Floats]:
        """
        The four layers at places in kilometres, as the rules of biomes read them.
        """
        elevation = np.interp(self.layers.elevation(x, y), *self.heights)
        return {
            'elevation': elevation,
            'relief': _share(self.layers.relief(x, y), self.reliefs),
            'moisture': _share(self.layers.moisture(x, y), self.moistures),
            'temperature': self.layers.temperature(x, y, elevation),
        }


def _share(values: Floats, ordered: Floats) -> Floats:
    shares: Floats = np.interp(values, ordered, np.linspace(0.0, 1.0, ordered.size))
    return shares


def _heights(ordered: Floats, under: int) -> tuple[float, tuple[Floats, Floats]]:
    """
    The sea level between the last node under water and the first above, and elevation as shares around it.
    """
    bounds = np.concatenate(([ordered[0] - 1.0], ordered, [ordered[-1] + 1.0]))
    level = float((bounds[under] + bounds[under + 1]) / 2)
    raw = np.concatenate((ordered[:under], [level], ordered[under:]))
    above = ordered.size - under
    shares = np.concatenate((np.linspace(-1.0, 0.0, under + 1), np.linspace(0.0, 1.0, above + 1)[1:]))
    return level, (raw, shares)


@lru_cache(maxsize=KEPT)
def skeleton(
    seed: int,
    circumference_km: int,
    skeleton_km: int,
    sea: float,
    elevation: Layer,
    relief: Layer,
    moisture: Layer,
    temperature: Temperature,
) -> Skeleton:
    """
    Worked out once for a seed and the parameters of the planet, then kept in the process.
    """
    made = layers(seed, circumference_km, elevation, relief, moisture, temperature)
    around = circumference_km // skeleton_km
    x, y = np.meshgrid((np.arange(around) + 0.5) * skeleton_km, (np.arange(around // 2) + 0.5) * skeleton_km)
    heights = made.elevation(x, y)
    reliefs = made.relief(x, y)
    moistures = made.moisture(x, y)

    level, table = _heights(np.sort(heights, axis=None), round(sea * heights.size))
    land = heights > level
    # A planet with no land has no land to take shares of, so the whole of it stands in.
    measured = land if land.any() else np.ones_like(land)
    return Skeleton(
        layers=made,
        elevation=heights,
        relief=reliefs,
        moisture=moistures,
        sea_level=level,
        heights=table,
        reliefs=np.sort(reliefs[measured]),
        moistures=np.sort(moistures[measured]),
    )
