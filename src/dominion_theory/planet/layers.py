"""
The four layers of the planet as functions of places in kilometres.
"""

from dataclasses import dataclass

import numpy as np

from ..content import Elevation, Layer, Moisture, Temperature
from .noise import Floats, Noise, stream


@dataclass(frozen=True)
class Layers:
    """
    Every layer draws from its own fresh stream of the seed, named as the layer.
    """

    circumference_km: int
    elevation: Noise
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
    ridges, basins = elevation.ridges, elevation.basins

    def noise(name: str, scale_km: int, octaves: int, persistence: float) -> Noise:
        return Noise(stream(seed, name), circumference_km, scale_km, octaves, persistence)

    return Layers(
        circumference_km=circumference_km,
        elevation=noise('elevation', elevation.scale_km, elevation.octaves, elevation.persistence),
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
