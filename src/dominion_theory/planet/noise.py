"""
Gradient noise in planet kilometres that closes around the planet with no seam.
"""

import numpy as np
from numpy.typing import NDArray

LACUNARITY = 2

Floats = NDArray[np.float64]


def stream(seed: int, name: str) -> np.random.Generator:
    """
    A fresh stream of the seed by name, derived as engine/streams.py derives its own.
    """
    sequence = np.random.SeedSequence(seed, spawn_key=tuple(name.encode()))
    return np.random.Generator(np.random.PCG64(sequence))


class Noise:
    """
    Octaves of gradient noise, each on a lattice of a whole number of squares around the planet.
    """

    def __init__(
        self,
        rng: np.random.Generator,
        circumference_km: int,
        scale_km: int,
        octaves: int,
        persistence: float,
    ) -> None:
        self.circumference_km = circumference_km
        self.persistence = persistence
        self.gradients: list[Floats] = []
        base = max(1, round(circumference_km / scale_km))
        for octave in range(octaves):
            around = base * LACUNARITY**octave
            angles = rng.uniform(0.0, 2.0 * np.pi, (around // 2 + 2, around))
            self.gradients.append(np.stack((np.cos(angles), np.sin(angles)), axis=-1))

    def __call__(self, x: Floats, y: Floats) -> Floats:
        """
        The noise at places given in kilometres, within -1..1. x wraps around the planet.
        """
        world = np.zeros(np.broadcast(x, y).shape, dtype=np.float64)
        amplitude = 1.0
        total = 0.0
        for gradients in self.gradients:
            world += amplitude * self._octave(gradients, x, y)
            total += amplitude
            amplitude *= self.persistence
        # Unit gradients keep one octave within sqrt(0.5), so this stretches the sum to -1..1.
        normalized: Floats = world / total * np.sqrt(2.0)
        return normalized

    def _octave(self, gradients: Floats, x: Floats, y: Floats) -> Floats:
        around = gradients.shape[1]
        side = self.circumference_km / around
        u = x / side
        v = y / side
        cell_x = np.floor(u).astype(np.int64)
        cell_y = np.floor(v).astype(np.int64)
        dx = u - cell_x
        dy = v - cell_y

        def corner(shift_x: int, shift_y: int) -> Floats:
            gradient = gradients[cell_y + shift_y, (cell_x + shift_x) % around]
            result: Floats = gradient[..., 0] * (dx - shift_x) + gradient[..., 1] * (dy - shift_y)
            return result

        fade_x = dx * dx * dx * (dx * (dx * 6 - 15) + 10)
        fade_y = dy * dy * dy * (dy * (dy * 6 - 15) + 10)
        top = corner(0, 0) + fade_x * (corner(1, 0) - corner(0, 0))
        bottom = corner(0, 1) + fade_x * (corner(1, 1) - corner(0, 1))
        blended: Floats = top + fade_y * (bottom - top)
        return blended
