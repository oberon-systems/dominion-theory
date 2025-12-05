import noise
import numpy as np
from numpy import ndarray


# pylint: disable-next=too-many-arguments,too-many-positional-arguments
def generator(
    height: int,
    width: int,
    scale: int,
    octaves: int,
    persistence: float,
    lacunarity: float,
    seed: int,
) -> ndarray:
    """
    Generate a "natural" elevation/moisture map, a base layer.
    """
    world = np.zeros((height, width))
    for i in range(height):
        for j in range(width):
            world[i][j] = noise.pnoise2(
                (i + seed * 1000) / scale,
                (j + seed * 1000) / scale,
                octaves=octaves,
                persistence=persistence,
                lacunarity=lacunarity,
                repeatx=1024,
                repeaty=1024,
                base=seed,
            )
    return world
