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
ZOOMS = 24
NEARER = (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS)
FURTHER = (pygame.K_MINUS, pygame.K_KP_MINUS)
MOVES = {pygame.K_LEFT: (-1, 0), pygame.K_RIGHT: (1, 0), pygame.K_UP: (0, -1), pygame.K_DOWN: (0, 1)}

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
    Opens a window until it is closed or Escape is pressed: the map, and beside it the legend and the cell
    pointed at. The picture holds a pixel to a cell; the wheel or plus and minus zoom, a drag or the arrows move.
    """
    pygame.init()
    rows, columns = picture.shape[:2]
    width, height = columns * scale, rows * scale
    screen = pygame.display.set_mode((width + PANEL, max(height, 2 * MARGIN + (len(legend) + 14) * LINE)))
    pygame.display.set_caption(title)
    font = pygame.font.Font(None, LINE)
    cells = _surface(picture)
    clock = pygame.time.Clock()
    zoom, west, north = scale, 0.0, 0.0
    drawn: tuple[int, int, int] | None = None
    shown = cells

    running = True
    while running:
        x, y = pygame.mouse.get_pos()
        over = x < width and y < height
        step = 0
        for event in pygame.event.get():
            if event.type == pygame.QUIT or event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
            elif event.type == pygame.MOUSEWHEEL:
                step += event.y
            elif event.type == pygame.KEYDOWN and event.key in NEARER:
                step += 1
            elif event.type == pygame.KEYDOWN and event.key in FURTHER:
                step -= 1
            elif event.type == pygame.KEYDOWN and event.key in MOVES:
                east, south = MOVES[event.key]
                west, north = west + east * width / zoom / 4, north + south * height / zoom / 4
            elif event.type == pygame.MOUSEMOTION and event.buttons[0] and over:
                west, north = west - event.rel[0] / zoom, north - event.rel[1] / zoom
        if step:
            # The cell under the pointer stays under it; with the pointer off the map, the middle does.
            hold_x, hold_y = (x, y) if over else (width / 2, height / 2)
            nearer = min(max(zoom + step, 1), ZOOMS)
            west, north = west + hold_x / zoom - hold_x / nearer, north + hold_y / zoom - hold_y / nearer
            zoom = nearer
        across, down = min(-(-width // zoom), columns), min(-(-height // zoom), rows)
        west, north = min(max(west, 0.0), columns - across), min(max(north, 0.0), rows - down)
        left, top = int(west), int(north)
        if drawn != (zoom, left, top):
            part = cells.subsurface((left, top, across, down))
            shown = pygame.transform.scale(part, (across * zoom, down * zoom))
            drawn = (zoom, left, top)

        screen.fill(BACK)
        screen.blit(shown, (0, 0), (0, 0, width, height))
        column, row = left + x // zoom, top + y // zoom
        found = describe(column, row) if over and column < columns and row < rows else ()
        if found:
            pygame.draw.rect(screen, MARK, ((column - left) * zoom, (row - top) * zoom, zoom, zoom), 1)
        pygame.draw.rect(screen, BACK, (width, 0, PANEL, screen.get_height()))

        beside, line = width + MARGIN, MARGIN
        for colour, words in legend:
            if colour is not None:
                pygame.draw.rect(screen, colour, (beside, line + 1, SWATCH, SWATCH))
            screen.blit(font.render(words, True, TEXT), (beside + SWATCH + 8 if colour else beside, line))
            line += LINE
        line += LINE
        screen.blit(font.render(f'zoom {zoom} px to a cell', True, TEXT), (beside, line))
        line += 2 * LINE
        for words in found:
            screen.blit(font.render(words, True, MARK if words is found[0] else TEXT), (beside, line))
            line += LINE

        pygame.display.flip()
        clock.tick(FRAMES)

    pygame.quit()
