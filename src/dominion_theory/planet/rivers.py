"""
Dominion Theory: Maps: Rivers

    Generate and apply rivers to maps data.

"""

import numpy as np
from numpy.typing import NDArray


def create(
    height: int,
    width: int,
    num: int,
    elevation: NDArray[np.float64],
    rng: np.random.Generator,
) -> NDArray[np.bool_]:
    """
    Generate rivers, every draw taken from the stream given
    """
    rivers = np.zeros((height, width), dtype=bool)

    for _ in range(num):
        x = int(rng.integers(width // 4, 3 * width // 4))
        y = int(rng.integers(0, height // 3))

        path_length = 0
        max_path_length = min(width, height)

        while y < height - 1 and 0 < x < width - 1 and path_length < max_path_length:

            rivers[y, x] = True

            neighbors = []
            for dx, dy in [(-1, 1), (0, 1), (1, 1)]:
                nx, ny = x + dx, y + dy
                if 0 <= nx < width and 0 <= ny < height:
                    neighbors.append((nx, ny, elevation[ny, nx]))

            if neighbors:
                next_x, next_y, _ = min(neighbors, key=lambda n: n[2])
                x, y = next_x, next_y
            else:
                break

            path_length += 1

    return rivers


def apply(
    biomes: NDArray[np.uint8],
    rivers: NDArray[np.bool_],
    water: int,
) -> NDArray[np.uint8]:
    """
    Applying rivers to provided biom map.
    """
    _biomes = biomes.copy()
    _biomes[rivers] = water

    return _biomes
