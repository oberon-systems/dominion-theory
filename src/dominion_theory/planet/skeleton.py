"""
The skeleton: the layers sampled on a coarse grid over the whole planet, and the shares read from it.
"""

from dataclasses import dataclass
from functools import lru_cache

import numpy as np
from numpy.typing import NDArray

from ..content import Elevation, Layer, Temperature
from .layers import Layers, layers
from .noise import Floats

KEPT = 4
SMALLEST = 1e-12


@dataclass(frozen=True)
class Skeleton:
    """
    Raw layers at the nodes, heights counted from the sea level, and the tables that restate a value as a share.
    """

    layers: Layers
    elevation: Floats
    relief: Floats
    moisture: Floats
    sea_level: float
    brim: float
    span: float
    heights: tuple[Floats, Floats]
    reliefs: Floats
    moistures: Floats

    @property
    def land(self) -> NDArray[np.bool_]:
        above: NDArray[np.bool_] = self.elevation > 0
        return above

    @property
    def rain(self) -> Floats:
        """
        What falls on a node: its moisture as a share of land, and nothing on the sea.
        """
        fallen: Floats = np.where(self.land, _share(self.moisture, self.moistures), 0.0)
        return fallen

    def restate(self, x: Floats, y: Floats, lakes: Floats | None = None) -> dict[str, Floats]:
        """
        The layers of the noise at places in kilometres, as the rules of biomes read them.
        A place that stands below the level of the lake around it is restated as water.
        """
        height = self.layers.height(x, y, self.sea_level, self.brim, self.span)
        elevation = np.interp(height, *self.heights)
        if lakes is not None:
            elevation = np.where(height < lakes, np.minimum(elevation, 0.0), elevation)
        return {
            'elevation': elevation,
            'relief': _share(self.layers.relief(x, y), self.reliefs),
            'moisture': _share(self.layers.moisture(x, y), self.moistures),
            'temperature': self.layers.temperature(x, y, elevation),
        }


def _share(values: Floats, ordered: Floats) -> Floats:
    shares: Floats = np.interp(values, ordered, np.linspace(0.0, 1.0, ordered.size))
    return shares


def _level(ordered: Floats, under: int) -> float:
    """
    The sea level between the last node under water and the first above, so that no node lies on it.
    """
    bounds = np.concatenate(([ordered[0] - 1.0], ordered, [ordered[-1] + 1.0]))
    return float((bounds[under] + bounds[under + 1]) / 2)


def _heights(ordered: Floats, under: int) -> tuple[Floats, Floats]:
    """
    Heights over the sea level as shares: of the sea below it from -1 to 0, of land above it from 0 to 1.
    """
    raw = np.concatenate((ordered[:under], [0.0], ordered[under:]))
    above = ordered.size - under
    shares = np.concatenate((np.linspace(-1.0, 0.0, under + 1), np.linspace(0.0, 1.0, above + 1)[1:]))
    return raw, shares


@lru_cache(maxsize=KEPT)
def skeleton(
    seed: int,
    circumference_km: int,
    skeleton_km: int,
    sea: float,
    elevation: Elevation,
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
    reliefs = made.relief(x, y)
    moistures = made.moisture(x, y)

    # The sea is measured before land is shaped: ridges and basins change land only and move no shore.
    under = round(sea * x.size)
    level = _level(np.sort(made.elevation(x, y), axis=None), under)
    hollows = np.sort(made.basins(x, y), axis=None)
    brim = float(hollows[min(round((1.0 - elevation.basins.share) * x.size), x.size - 1)])
    span = max(float(hollows[-1]) - brim, SMALLEST)
    heights = made.height(x, y, level, brim, span)
    table = _heights(np.sort(heights, axis=None), under)
    land = heights > 0
    # A planet with no land has no land to take shares of, so the whole of it stands in.
    measured = land if land.any() else np.ones_like(land)
    return Skeleton(
        layers=made,
        elevation=heights,
        relief=reliefs,
        moisture=moistures,
        sea_level=level,
        brim=brim,
        span=span,
        heights=table,
        reliefs=np.sort(reliefs[measured]),
        moistures=np.sort(moistures[measured]),
    )
