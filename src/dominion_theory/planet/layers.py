"""
The four layers of the planet as functions of places in kilometres.
"""

from dataclasses import dataclass

import numpy as np

from ..content import Layer, Temperature
from .noise import Floats, Noise, stream


@dataclass(frozen=True)
class Layers:
    """
    Every layer draws from its own fresh stream of the seed, named as the layer.
    """

    circumference_km: int
    elevation: Noise
    relief: Noise
    moisture: Noise
    belts: Noise
    lapse: float
    noise: float

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
    elevation: Layer,
    relief: Layer,
    moisture: Layer,
    temperature: Temperature,
) -> Layers:
    def noise(name: str, scale_km: int, octaves: int, persistence: float) -> Noise:
        return Noise(stream(seed, name), circumference_km, scale_km, octaves, persistence)

    return Layers(
        circumference_km=circumference_km,
        elevation=noise('elevation', elevation.scale_km, elevation.octaves, elevation.persistence),
        relief=noise('relief', relief.scale_km, relief.octaves, relief.persistence),
        moisture=noise('moisture', moisture.scale_km, moisture.octaves, moisture.persistence),
        belts=noise('temperature', temperature.scale_km, 1, 1.0),
        lapse=temperature.lapse,
        noise=temperature.noise,
    )
