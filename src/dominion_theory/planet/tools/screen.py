"""
Dominion Theory: Maps: Tools: Screen

    The only place of the tool that needs pygame: a picture written to a file or shown in a window.
"""

from collections.abc import Callable, Sequence
from pathlib import Path

import numpy as np
import pygame

from .pictures import Picture

FRAMES = 30
PANEL = 280
MARGIN = 12
LINE = 22
SWATCH = 14
BACK = (40, 40, 40)
TEXT = (235, 235, 235)
MARK = (255, 255, 0)

Entry = tuple[tuple[int, int, int] | None, str]
Describe = Callable[[int, int], Sequence[str]]


def _surface(picture: Picture) -> pygame.Surface:
    return pygame.surfarray.make_surface(np.ascontiguousarray(picture.swapaxes(0, 1)))


def save(picture: Picture, path: Path) -> None:
    """
    Writes the picture in the format its suffix names. It needs no display.
    """
    pygame.image.save(_surface(picture), str(path))


def show(picture: Picture, title: str, legend: Sequence[Entry], describe: Describe, scale: int) -> None:
    """
    Opens a window until it is closed or Escape is pressed: the map, and beside it the legend and the cell pointed at.
    """
    pygame.init()
    height, width = picture.shape[:2]
    rows = len(legend) + 12
    screen = pygame.display.set_mode((width + PANEL, max(height, 2 * MARGIN + rows * LINE)))
    pygame.display.set_caption(title)
    font = pygame.font.Font(None, LINE)
    drawn = _surface(picture)
    clock = pygame.time.Clock()

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT or event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False

        screen.fill(BACK)
        screen.blit(drawn, (0, 0))
        left, top = width + MARGIN, MARGIN
        for colour, words in legend:
            if colour is not None:
                pygame.draw.rect(screen, colour, (left, top + 1, SWATCH, SWATCH))
            screen.blit(font.render(words, True, TEXT), (left + SWATCH + 8 if colour else left, top))
            top += LINE

        x, y = pygame.mouse.get_pos()
        found = describe(x, y) if x < width and y < height else ()
        if found:
            pygame.draw.rect(screen, MARK, (x - x % scale, y - y % scale, scale, scale), 1)
        top += LINE
        for words in found:
            screen.blit(font.render(words, True, MARK if words is found[0] else TEXT), (left, top))
            top += LINE

        pygame.display.flip()
        clock.tick(FRAMES)

    pygame.quit()
