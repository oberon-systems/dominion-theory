"""
Moisture Noise Settings
"""

from dataclasses import dataclass

from .base import Noise


@dataclass(frozen=True)
class Moisture(Noise):
    """
    Settings for moisture noise generation.

    scale: Zoom level. Higher values produce smoother,
           larger features.

    octaves: Number of noise layers. More octaves
             add finer details.

    persistence: Amplitude multiplier between octaves.
                 Controls how visible each layer is.

    seed: Random seed for reproducible results.
    """
    scale: int = 80
    octaves: int = 4
    persistence: float = 0.5
