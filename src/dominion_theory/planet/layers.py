"""
The four layers of the planet as functions of places in kilometres.
"""

from dataclasses import dataclass

import numpy as np

from ..content import Elevation, Layer, Moisture, Temperature
from .noise import Floats, Noise, stream

STREAM = 'continents'
SHIFT = 0.25
STRETCH = (0.75, 1.35)


@dataclass(frozen=True)
class Land:
    """
    The height of the planet before it is shaped: noise, a finer noise that raises islands, and the continents,
    each a plateau around its centre that falls off at its radius.
    """

    circumference_km: int
    noise: Noise
    isles: Noise
    centres: Floats
    radii: Floats
    weight: float
    islands: float
    edge: int

    def __call__(self, x: Floats, y: Floats) -> Floats:
        raw: Floats = self.noise(x, y) + self.islands * self.isles(x, y)
        if len(self.centres):
            east = np.asarray(x)[..., None] - self.centres[:, 0]
            east -= self.circumference_km * np.round(east / self.circumference_km)
            south = np.asarray(y)[..., None] - self.centres[:, 1]
            out = np.sqrt((east / self.radii[:, 0]) ** 2 + (south / self.radii[:, 1]) ** 2)
            raw = raw + self.weight * (1.0 / (1.0 + out**self.edge)).max(axis=-1)
        return raw


def _land(seed: int, circumference_km: int, elevation: Elevation, noise: Noise, isles: Noise) -> Land:
    """
    The centres stand around the planet at even steps, each moved a little, north or south of the equator
    by no more than spread; a continent is stretched one way or the other.
    """
    held = elevation.continents
    rng = stream(seed, STREAM)
    turn = rng.uniform(0.0, 1.0)
    moved = rng.uniform(-SHIFT, SHIFT, held.count)
    north = rng.uniform(-1.0, 1.0, held.count)
    stretch = rng.uniform(*STRETCH, held.count)
    east = (np.arange(held.count) + turn + moved) / max(held.count, 1) % 1.0 * circumference_km
    south = circumference_km / 4 * (1.0 + held.spread * north)
    return Land(
        circumference_km=circumference_km,
        noise=noise,
        isles=isles,
        centres=np.column_stack((east, south)),
        radii=np.column_stack((held.radius_km * stretch, held.radius_km / stretch)),
        weight=held.weight,
        islands=elevation.islands.weight,
        edge=held.edge,
    )


@dataclass(frozen=True)
class Layers:
    """
    Every layer draws from its own fresh stream of the seed, named as the layer.
    """

    circumference_km: int
    elevation: Land
    ridges: Noise
    basins: Noise
    relief: Noise
    moisture: Noise
    belts: Noise
    weight: float
    sharpness: int
    depth: float
    lapse: float
    noise: float
    latitudes: Floats
    wets: Floats
    belt: float
    inland: float
    inland_km: float

    def damp(self, x: Floats, y: Floats, away: Floats) -> Floats:
        """
        How wet a place is before it is restated as a share: the noise, the belt of its latitude laid over it,
        and the drying of land that lies away from the sea, half of it reached at inland_km.
        """
        equator = self.circumference_km / 4
        zone = np.interp(np.abs(y - equator) / equator, self.latitudes, self.wets)
        dried = 1.0 - 0.5 ** (away / self.inland_km)
        wet: Floats = self.moisture(x, y) + self.belt * (2.0 * zone - 1.0) - self.inland * dried
        return wet

    def height(self, x: Floats, y: Floats, sea: float, brim: float, span: float) -> Floats:
        """
        How high a place stands over the sea level. Land is lifted along the lines where the ridge noise turns
        and sunk where the basin noise rises over the brim; neither moves a shore.
        """
        above = self.elevation(x, y) - sea
        crest = (1.0 - np.abs(self.ridges(x, y))) ** self.sharpness
        dip = np.clip((self.basins(x, y) - brim) / span, 0.0, 1.0)
        shaped = above * (1.0 + self.weight * crest) * (1.0 - self.depth * dip)
        height: Floats = np.where(above > 0, shaped, above)
        return height

    def temperature(self, x: Floats, y: Floats, land: Floats) -> Floats:
        """
        1 at the equator and 0 at the poles, lowered by the share of land lying below the place.
        """
        equator = self.circumference_km / 4
        latitude = np.abs(y - equator) / equator
        raw = 1.0 - latitude - self.lapse * np.clip(land, 0.0, 1.0) + self.noise * self.belts(x, y)
        held: Floats = np.clip(raw, 0.0, 1.0)
        return held


def layers(
    seed: int,
    circumference_km: int,
    elevation: Elevation,
    relief: Layer,
    moisture: Moisture,
    temperature: Temperature,
) -> Layers:
    ridges, basins, islands = elevation.ridges, elevation.basins, elevation.islands

    def noise(name: str, scale_km: int, octaves: int, persistence: float) -> Noise:
        return Noise(stream(seed, name), circumference_km, scale_km, octaves, persistence)

    return Layers(
        circumference_km=circumference_km,
        elevation=_land(
            seed,
            circumference_km,
            elevation,
            noise('elevation', elevation.scale_km, elevation.octaves, elevation.persistence),
            noise('islands', islands.scale_km, islands.octaves, islands.persistence),
        ),
        ridges=noise('ridges', ridges.scale_km, ridges.octaves, ridges.persistence),
        basins=noise('basins', basins.scale_km, basins.octaves, basins.persistence),
        relief=noise('relief', relief.scale_km, relief.octaves, relief.persistence),
        moisture=noise('moisture', moisture.scale_km, moisture.octaves, moisture.persistence),
        belts=noise('temperature', temperature.scale_km, 1, 1.0),
        weight=ridges.weight,
        sharpness=ridges.sharpness,
        depth=basins.depth,
        lapse=temperature.lapse,
        noise=temperature.noise,
        latitudes=np.array([held.latitude for held in moisture.belts]),
        wets=np.array([held.wet for held in moisture.belts]),
        belt=moisture.belt,
        inland=moisture.inland,
        inland_km=float(moisture.inland_km),
    )
