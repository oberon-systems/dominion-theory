"""
Dominion Theory: Maps: Rivers

    Generate and apply rivers to maps data.

"""

import numpy as np
from numpy import ndarray

from .settings.biomes import Biomes


# pylint: disable-next=too-many-locals
def create(
    height: int,
    width: int,
    num: int,
    elevation: ndarray,
) -> ndarray:
    """
    Generate rivers
    """
    rivers = np.zeros((height, width), dtype=bool)

    for _ in range(num):
        x = np.random.randint(width // 4, 3 * width // 4)
        y = np.random.randint(0, height // 3)

        path_length = 0
        max_path_length = min(width, height)

        while (
                y < height - 1 and
                0 < x < width - 1 and
                path_length < max_path_length
        ):

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
        biomes: ndarray,
        rivers: ndarray,
) -> ndarray:
    """
    Applying rivers to provided biom map.
    """
    _biomes = biomes.copy()
    _coords = np.where(rivers)

    for i, j in zip(_coords[0], _coords[1]):
        _biomes[i, j] = Biomes.water

    return _biomes
