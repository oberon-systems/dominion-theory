import numpy as np
from matplotlib import patches, pyplot
from numpy import ndarray

if __name__ == '__main__':
    import os
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from biomes import BiomeGenerator
else:
    from . import BiomeGenerator


# pylint: disable=too-many-locals
def visualize(biomes: ndarray):
    biome_to_num = {'water': 0, 'grassland': 1, 'forest': 2, 'mountains': 3}
    colors = ['#0077BE', '#228B22', '#006400', '#8B8989']

    unique, counts = np.unique(biomes, return_counts=True)
    stats = {}
    for biome, count in zip(unique, counts):
        percentage = (count / biomes.size) * 100
        stats[biome] = percentage

    cell_size = 5
    height, width = biomes.shape
    big_map = np.zeros((height * cell_size, width * cell_size), dtype=int)

    for i in range(height):
        for j in range(width):
            biome = biomes[i, j]
            value = biome_to_num[biome]

            big_map[i * cell_size:(i + 1) * cell_size, j * cell_size:(j + 1) * cell_size] = value

    pyplot.figure(figsize=(12, 10))
    pyplot.imshow(
        big_map,
        cmap=pyplot.cm.colors.ListedColormap(colors),
        interpolation='nearest',
    )
    pyplot.title('Generated Biome Map (5x5 pixels per cell)')

    legend_elements = [
        patches.Patch(color='#0077BE', label=f'Water ({stats.get("water", 0):.1f}%)'),
        patches.Patch(color='#228B22', label=f'Grassland ({stats.get("grassland", 0):.1f}%)'),
        patches.Patch(color='#006400', label=f'Forest ({stats.get("forest", 0):.1f}%)'),
        patches.Patch(color='#8B8989', label=f'Mountains ({stats.get("mountains", 0):.1f}%)'),
    ]
    pyplot.legend(handles=legend_elements, loc='upper right')
    pyplot.show()


if __name__ == '__main__':
    generator = BiomeGenerator(width=512, height=512)
    _biomes = generator.generate_map(seed=42)
    visualize(_biomes)
