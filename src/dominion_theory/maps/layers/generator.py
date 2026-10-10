import numpy as np
from numpy.typing import NDArray

LATTICE = 256


def _perlin(
    x: NDArray[np.float64],
    y: NDArray[np.float64],
    permutation: NDArray[np.int64],
    gradients: NDArray[np.float64],
) -> NDArray[np.float64]:
    """
    Gradient noise for every point at once, on a lattice that repeats every LATTICE cells.
    """
    cell_x = np.floor(x).astype(np.int64)
    cell_y = np.floor(y).astype(np.int64)
    dx = x - cell_x
    dy = y - cell_y

    def corner(shift_x: int, shift_y: int) -> NDArray[np.float64]:
        index = permutation[(permutation[(cell_x + shift_x) % LATTICE] + cell_y + shift_y) % LATTICE]
        gradient = gradients[index]
        result: NDArray[np.float64] = gradient[..., 0] * (dx - shift_x) + gradient[..., 1] * (dy - shift_y)
        return result

    fade_x = dx * dx * dx * (dx * (dx * 6 - 15) + 10)
    fade_y = dy * dy * dy * (dy * (dy * 6 - 15) + 10)

    top = corner(0, 0) + fade_x * (corner(1, 0) - corner(0, 0))
    bottom = corner(0, 1) + fade_x * (corner(1, 1) - corner(0, 1))

    blended: NDArray[np.float64] = top + fade_y * (bottom - top)
    return blended


def generator(
    height: int,
    width: int,
    scale: int,
    octaves: int,
    persistence: float,
    lacunarity: float,
    seed: int,
) -> NDArray[np.float64]:
    """
    Generate a "natural" elevation/moisture map, a base layer.

    The same seed always gives the same layer, with values within -1..1.
    """
    rng = np.random.default_rng(seed)
    permutation = rng.permutation(LATTICE)
    angles = rng.uniform(0.0, 2.0 * np.pi, LATTICE)
    gradients = np.stack((np.cos(angles), np.sin(angles)), axis=-1)

    rows, columns = np.mgrid[0:height, 0:width]
    x = columns / scale
    y = rows / scale

    world = np.zeros((height, width), dtype=np.float64)
    amplitude = 1.0
    frequency = 1.0
    total = 0.0

    for _ in range(octaves):
        world += amplitude * _perlin(x * frequency, y * frequency, permutation, gradients)
        total += amplitude
        amplitude *= persistence
        frequency *= lacunarity

    # Unit gradients keep one octave within sqrt(0.5), so this stretches the sum to -1..1.
    normalized: NDArray[np.float64] = world / total * np.sqrt(2.0)
    return normalized
