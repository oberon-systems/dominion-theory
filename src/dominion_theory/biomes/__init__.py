import noise
import numpy as np
from numpy import ndarray


class BiomeGenerator:
    """
    Bioms Gemerator Class.
    """

    def __init__(
        self,
        width: int = 512,
        height: int = 512,
    ):
        self.width = width
        self.height = height

    # pylint: disable=too-many-positional-arguments
    # pylint: disable=too-many-arguments
    def layer(
        self,
        scale: int = 100,
        octaves: int = 4,
        persistence: float = 0.5,
        lacunarity: float = 2.0,
        seed: int = 0,
    ) -> ndarray:
        """
        Creates "natural" elevation/moisture map, a base layer.
        """
        world = np.zeros((self.height, self.width))
        for i in range(self.height):
            for j in range(self.width):
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

    def elevation(self) -> ndarray:
        """
        Creates elevation layer.
        """
        return self.layer(scale=100, octaves=6, persistence=0.6, seed=1)

    def moisture(self) -> ndarray:
        """
        Creates moisture layer.
        """
        return self.layer(scale=80, octaves=4, persistence=0.5, seed=2)

    def biomes(
        self,
        elevation: ndarray,
        moisture: ndarray,
    ) -> ndarray:
        """
        Creates bioms layer, depended on elevation and moisture.
        """
        _biomes = np.zeros((self.height, self.width), dtype=object)

        water_level = -0.2
        mountain_level = 0.15
        forest_moisture = 0.0

        for i in range(self.height):
            for j in range(self.width):
                elev = elevation[i, j]
                moist = moisture[i, j]

                if elev < water_level:
                    _biomes[i, j] = 'water'
                elif elev > mountain_level:
                    _biomes[i, j] = 'mountains'
                elif moist > forest_moisture:
                    _biomes[i, j] = 'forest'
                else:
                    _biomes[i, j] = 'grassland'

        return _biomes

    def create_rivers(
        self,
        elevation: ndarray,
        num_rivers: int = 8,
    ) -> ndarray:
        """
        Generate rivers
        """
        rivers = np.zeros((self.height, self.width), dtype=bool)

        for _ in range(num_rivers):
            x = np.random.randint(self.width // 4, 3 * self.width // 4)
            y = np.random.randint(0, self.height // 3)

            path_length = 0
            max_path_length = min(self.width, self.height)

            while (
                y < self.height - 1 and
                0 < x < self.width - 1 and
                path_length < max_path_length
            ):

                rivers[y, x] = True

                neighbors = []
                for dx, dy in [(-1, 1), (0, 1), (1, 1)]:
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < self.width and 0 <= ny < self.height:
                        neighbors.append((nx, ny, elevation[ny, nx]))

                if neighbors:
                    next_x, next_y, _ = min(neighbors, key=lambda n: n[2])
                    x, y = next_x, next_y
                else:
                    break

                path_length += 1

        return rivers

    # pylint: disable=redefined-outer-name
    def apply_rivers(
        self,
        biomes: ndarray,
        rivers: ndarray,
    ) -> ndarray:
        """
        Applying rivers to provided biom map.
        """
        _biomes = biomes.copy()
        river_coords = np.where(rivers)

        for i, j in zip(river_coords[0], river_coords[1]):
            _biomes[i, j] = 'water'

        return _biomes

    def generate_map(
        self,
        seed: [int | None] = None,
    ) -> ndarray:
        if seed is not None:
            np.random.seed(seed)

        elevation = self.elevation()
        moisture = self.moisture()
        biomes = self.biomes(elevation, moisture)
        rivers = self.create_rivers(elevation)

        _biomes = self.apply_rivers(biomes, rivers)

        return _biomes


if __name__ == '__main__':
    generator = BiomeGenerator(width=100, height=100)
    # pylint: disable=redefined-outer-name
    biomes = generator.generate_map(seed=42)

    unique, counts = np.unique(biomes, return_counts=True)
    for biome, count in zip(unique, counts):
        percentage = (count / biomes.size) * 100
        print(f"{biome}: {percentage:.1f}%")
