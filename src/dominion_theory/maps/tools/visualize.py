"""
Dominion Theory: Maps: Tools: Visualizers
"""

import numpy as np
from matplotlib import patches, pyplot
from numpy import ndarray


def get_biomes_info(biomes: ndarray) -> tuple:
    """
    Collect biomes information
    """
    unique, counts = np.unique(biomes, return_counts=True)

    colors = {}
    stats = {}
    num = {}

    for idx, (biome, count) in enumerate(zip(unique, counts)):
        name = repr(biome)
        colors[name] = biome.color
        stats[name] = (count / biomes.size) * 100
        num[name] = idx

    return colors, stats, num


# pylint: disable-next=too-many-locals
def visualize_with_property(biomes: ndarray, scale: int):
    """
    Show map with properties.
    """
    colors, stats, num = get_biomes_info(biomes)

    height, width = biomes.shape
    _map = np.zeros((height * scale, width * scale), dtype=int)

    for i in range(height):
        for j in range(width):
            biome = biomes[i, j]
            value = num[repr(biome)]
            _map[i * scale:(i + 1) * scale, j * scale:(j + 1) * scale] = value

    fig, ax = pyplot.subplots(figsize=(12, 10))
    ax.imshow(
        _map,
        cmap=pyplot.cm.colors.ListedColormap(list(colors.values())),
        interpolation='nearest',
    )
    ax.set_title('Generated Biome Map - Hover for properties')

    legend_elements = [
        patches.Patch(color=color, label=f'{name.capitalize()} ({stats[name]:.1f}%)')
        for name, color in colors.items()
    ]
    ax.legend(handles=legend_elements, loc='upper right')

    def on_hover(event):
        if event.inaxes == ax:
            x, y = int(event.xdata), int(event.ydata)
            if 0 <= x < _map.shape[1] and 0 <= y < _map.shape[0]:
                orig_x = x // scale
                orig_y = y // scale

                if 0 <= orig_x < width and 0 <= orig_y < height:
                    biome = biomes[orig_y, orig_x]
                    props = biome.properties

                    tooltip = (
                        f"({orig_x}, {orig_y}) {repr(biome).capitalize()} | "
                        f"Water: {props.water:.1f} | "
                        f"Food: {props.food:.1f} | "
                        f"Threat: {props.threat:.1f} | "
                        f"Passability: {props.passability:.1f}"
                    )
                    ax.set_title(tooltip)

    fig.canvas.mpl_connect('motion_notify_event', on_hover)
    pyplot.show()


def visualize_property(biomes: ndarray, name: str):
    """
    Show map for selected property.
    """
    height, width = biomes.shape
    property_map = np.zeros((height, width), dtype=float)

    for i in range(height):
        for j in range(width):
            property_map[i, j] = getattr(biomes[i, j].properties, name, 0.0)

    fig, ax = pyplot.subplots(figsize=(12, 8))
    im = ax.imshow(property_map, cmap='viridis', interpolation='nearest')
    ax.set_title(f'{name.capitalize()} Map - Hover for details')
    pyplot.colorbar(im, label=f'{name.capitalize()} Level')

    def on_hover(event):
        if event.inaxes == ax:
            x, y = int(event.xdata), int(event.ydata)
            if 0 <= x < width and 0 <= y < height:
                biome = biomes[y, x]
                value = getattr(biome.properties, name, 0.0)
                ax.set_title(f'{name.capitalize()} Map - ({x}, {y}) {repr(biome)}: {value:.2f}')

    fig.canvas.mpl_connect('motion_notify_event', on_hover)
    pyplot.show()


# pylint: disable-next=too-many-locals
def visualize_all_properties(biomes: ndarray):
    """
    Show chart maps for all properties.
    """
    height, width = biomes.shape
    properties = ['water', 'food', 'threat', 'passability']
    colormaps = ['Blues', 'Greens', 'Reds', 'Purples']

    property_maps = {}
    for prop in properties:
        prop_map = np.zeros((height, width), dtype=float)
        for i in range(height):
            for j in range(width):
                prop_map[i, j] = getattr(biomes[i, j].properties, prop, 0.0)
        property_maps[prop] = prop_map

    fig, axes = pyplot.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('All Biome Properties - Hover for details')

    for idx, (prop_name, cmap) in enumerate(zip(properties, colormaps)):
        row, col = idx // 2, idx % 2
        ax = axes[row, col]

        im = ax.imshow(property_maps[prop_name], cmap=cmap, interpolation='nearest')
        ax.set_title(f'{prop_name.capitalize()}')
        pyplot.colorbar(im, ax=ax)

    pyplot.tight_layout()
    pyplot.show()


def visualize(biomes: ndarray, scale: int):
    """
    Simple visualisation
    """
    colors, stats, num = get_biomes_info(biomes)

    height, width = biomes.shape
    big_map = np.zeros((height * scale, width * scale), dtype=int)

    for i in range(height):
        for j in range(width):
            biome = biomes[i, j]
            value = num[repr(biome)]
            big_map[i * scale:(i + 1) * scale, j * scale:(j + 1) * scale] = value

    pyplot.figure(figsize=(12, 10))
    pyplot.imshow(
        big_map,
        cmap=pyplot.cm.colors.ListedColormap(list(colors.values())),
        interpolation='nearest',
    )
    pyplot.title('Generated Biome Map')

    legend_elements = [
        patches.Patch(color=color, label=f'{name.capitalize()} ({stats[name]:.1f}%)')
        for name, color in colors.items()
    ]
    pyplot.legend(handles=legend_elements, loc='upper right')
    pyplot.show()
