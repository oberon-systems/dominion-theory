"""
Dominion Theory: Maps: Tools: Visualizers
"""

import numpy as np
import pygame
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


def color2rgb(color: str) -> tuple:
    if color.startswith('#'):
        color = color[1:]
        return tuple(int(color[i:i+2], 16) for i in (0, 2, 4))

    color_map = {
        'blue': (0, 0, 255),
        'green': (0, 255, 0),
        'red': (255, 0, 0),
        'yellow': (255, 255, 0),
        'white': (255, 255, 255),
        'black': (0, 0, 0),
        'brown': (139, 69, 19),
        'gray': (128, 128, 128),
        'orange': (255, 165, 0),
        'purple': (128, 0, 128),
        'cyan': (0, 255, 255),
        'pink': (255, 192, 203),
        'darkgreen': (0, 100, 0),
        'lightblue': (173, 216, 230),
        'sandy': (244, 164, 96),
        'snow': (255, 250, 250),
    }
    return color_map.get(color.lower(), (128, 128, 128))

# pylint: disable-next=too-many-locals,too-many-statements


def visualize(
    biomes: ndarray,
    scale: int,
    title: str = 'Biome Map',
):
    pygame.init()

    colors, stats, _ = get_biomes_info(biomes)
    height, width = biomes.shape

    legend_width = 250
    screen_width = width * scale + legend_width
    screen_height = max(height * scale, len(colors) * 30 + 100)

    screen = pygame.display.set_mode((screen_width, screen_height))
    pygame.display.set_caption(title)

    font = pygame.font.Font(None, 24)
    small_font = pygame.font.Font(None, 20)

    map_surface = pygame.Surface((width * scale, height * scale))

    for i in range(height):
        for j in range(width):
            biome = biomes[i, j]
            rgb = color2rgb(biome.color)
            pygame.draw.rect(
                map_surface,
                rgb,
                (j * scale, i * scale, scale, scale),
            )

    running = True
    clock = pygame.time.Clock()

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

        screen.fill((40, 40, 40))
        screen.blit(map_surface, (0, 0))

        mouse_x, mouse_y = pygame.mouse.get_pos()
        tooltip_text = None
        tooltip_props = None

        if (
            0 <= mouse_x < width * scale and
            0 <= mouse_y < height * scale
        ):
            grid_x = mouse_x // scale
            grid_y = mouse_y // scale

            if 0 <= grid_x < width and 0 <= grid_y < height:
                biome = biomes[grid_y, grid_x]
                props = biome.properties
                tooltip_text = f"({grid_x}, {grid_y}) {repr(biome)}"
                tooltip_props = (
                    f"W:{props.water:.1f} "
                    f"F:{props.food:.1f} "
                    f"T:{props.threat:.1f} "
                    f"P:{props.passability:.1f}"
                )

                pygame.draw.rect(
                    screen,
                    (255, 255, 0),
                    (grid_x * scale, grid_y * scale, scale, scale),
                    2,
                )

        legend_x = width * scale + 10
        legend_y = 10

        title = font.render('Legend', True, (255, 255, 255))
        screen.blit(title, (legend_x, legend_y))
        legend_y += 30

        for name, color in colors.items():
            rgb = color2rgb(color)
            pygame.draw.rect(screen, rgb, (legend_x, legend_y, 20, 20))
            pygame.draw.rect(screen, (255, 255, 255), (legend_x, legend_y, 20, 20), 1)

            label = small_font.render(f"{name} ({stats[name]:.1f}%)", True, (255, 255, 255))
            screen.blit(label, (legend_x + 30, legend_y + 2))
            legend_y += 25

        if tooltip_text:
            legend_y += 20
            info_title = font.render('Current Cell:', True, (255, 255, 0))
            screen.blit(info_title, (legend_x, legend_y))
            legend_y += 25

            info_text = small_font.render(tooltip_text, True, (255, 255, 255))
            screen.blit(info_text, (legend_x, legend_y))
            legend_y += 20

            props_text = small_font.render(tooltip_props, True, (200, 200, 200))
            screen.blit(props_text, (legend_x, legend_y))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


def visualize_property(biomes: ndarray, name: str, scale: int):
    pygame.init()

    height, width = biomes.shape

    property_map = np.zeros((height, width), dtype=float)
    for i in range(height):
        for j in range(width):
            property_map[i, j] = getattr(biomes[i, j].properties, name, 0.0)

    min_val = property_map.min()
    max_val = property_map.max()

    legend_width = 250
    screen_width = width * scale + legend_width
    screen_height = max(height * scale, 300)

    screen = pygame.display.set_mode((screen_width, screen_height))
    pygame.display.set_caption(f"{name.capitalize()} Map")

    font = pygame.font.Font(None, 24)
    small_font = pygame.font.Font(None, 20)

    map_surface = pygame.Surface((width * scale, height * scale))

    for i in range(height):
        for j in range(width):
            if max_val > min_val:
                normalized = (property_map[i, j] - min_val) / (max_val - min_val)
            else:
                normalized = 0.5

            r = int(normalized * 255)
            g = int((1 - normalized) * 100)
            b = int((1 - normalized) * 255)

            pygame.draw.rect(
                map_surface,
                (r, g, b),
                (j * scale, i * scale, scale, scale),
            )

    running = True
    clock = pygame.time.Clock()

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

        screen.fill((40, 40, 40))
        screen.blit(map_surface, (0, 0))

        mouse_x, mouse_y = pygame.mouse.get_pos()

        if 0 <= mouse_x < width * scale and 0 <= mouse_y < height * scale:
            grid_x = mouse_x // scale
            grid_y = mouse_y // scale

            if 0 <= grid_x < width and 0 <= grid_y < height:
                pygame.draw.rect(
                    screen,
                    (255, 255, 0),
                    (grid_x * scale, grid_y * scale, scale, scale),
                    2,
                )

                biome = biomes[grid_y, grid_x]
                value = property_map[grid_y, grid_x]

                legend_x = width * scale + 10
                legend_y = 10

                title = font.render(f"{name.capitalize()} Map", True, (255, 255, 255))
                screen.blit(title, (legend_x, legend_y))
                legend_y += 40

                info = small_font.render(f"Position: ({grid_x}, {grid_y})", True, (255, 255, 255))
                screen.blit(info, (legend_x, legend_y))
                legend_y += 25

                biome_info = small_font.render(f"Biome: {repr(biome)}", True, (255, 255, 255))
                screen.blit(biome_info, (legend_x, legend_y))
                legend_y += 25

                value_info = small_font.render(f"{name}: {value:.2f}", True, (255, 255, 0))
                screen.blit(value_info, (legend_x, legend_y))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


def visualize_all_properties(biomes: ndarray, scale: int):
    pygame.init()

    height, width = biomes.shape
    properties = ['water', 'food', 'threat', 'passability']

    property_maps = {}
    for prop in properties:
        prop_map = np.zeros((height, width), dtype=float)
        for i in range(height):
            for j in range(width):
                prop_map[i, j] = getattr(biomes[i, j].properties, prop, 0.0)
        property_maps[prop] = prop_map

    map_width = width * scale
    map_height = height * scale
    padding = 10

    screen_width = map_width * 2 + padding * 3
    screen_height = map_height * 2 + padding * 3 + 30

    screen = pygame.display.set_mode((screen_width, screen_height))
    pygame.display.set_caption('All Properties')

    font = pygame.font.Font(None, 20)

    color_schemes = {
        'water': lambda n: (0, int(n * 150), int(n * 255)),
        'food': lambda n: (0, int(n * 255), 0),
        'threat': lambda n: (int(n * 255), 0, 0),
        'passability': lambda n: (int(n * 128), 0, int(n * 255)),
    }

    surfaces = {}
    for prop in properties:
        surf = pygame.Surface((map_width, map_height))
        prop_map = property_maps[prop]
        min_val, max_val = prop_map.min(), prop_map.max()

        for i in range(height):
            for j in range(width):
                if max_val > min_val:
                    normalized = (prop_map[i, j] - min_val) / (max_val - min_val)
                else:
                    normalized = 0.5

                color = color_schemes[prop](normalized)
                pygame.draw.rect(surf, color, (j * scale, i * scale, scale, scale))

        surfaces[prop] = surf

    positions = {
        'water': (padding, padding + 20),
        'food': (map_width + padding * 2, padding + 20),
        'threat': (padding, map_height + padding * 2 + 20),
        'passability': (map_width + padding * 2, map_height + padding * 2 + 20),
    }

    running = True
    clock = pygame.time.Clock()

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

        screen.fill((40, 40, 40))

        for prop in properties:
            pos = positions[prop]
            screen.blit(surfaces[prop], pos)

            label = font.render(prop.capitalize(), True, (255, 255, 255))
            screen.blit(label, (pos[0], pos[1] - 20))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
