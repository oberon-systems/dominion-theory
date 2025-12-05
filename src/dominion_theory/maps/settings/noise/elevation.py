"""
Elevation Noise Settings
"""

from dataclasses import dataclass

from .base import Noise


@dataclass(frozen=True)
class Elevation(Noise):
    """
    Settings for elevation noise generation.

    scale: Zoom level. Higher values produce smoother,
           larger features.

    octaves: Number of noise layers. More octaves
             add finer details.

    persistence: Amplitude multiplier between octaves.
                 Controls how visible each layer is.

    seed: Random seed for reproducible results.
    """
    scale: int = 100
    octaves: int = 6
    persistence: float = 0.6
    seed: int = 1
