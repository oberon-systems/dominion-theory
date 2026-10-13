from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient

from dominion_theory.api import PREFIX
from dominion_theory.api.maps import rectangle
from dominion_theory.content import load_params
from dominion_theory.engine import Game

SMALL = {'planet.circumference_km': 4000, 'planet.window.width': 32, 'planet.window.height': 16}


@pytest.fixture(scope='module')
def game() -> Game:
    return Game.create(seed=42, params=load_params(overrides=SMALL))


def test_the_whole_window_is_given_when_nothing_is_asked(game: Game) -> None:
    whole = rectangle(game)
    names = whole['biomes']

    assert (whole['scale'], whole['x'], whole['y']) == (0, game.window.x, game.window.y)
    assert (whole['width'], whole['height']) == (32, 16)
    assert len(whole['cells']) == 32 * 16
    assert sorted(set(whole['cells'])) == list(range(len(names)))
    assert [names[cell] for cell in whole['cells']] == [
        game.snapshot()['biomes'][code] for code in game.biomes.ravel().tolist()
    ]


def test_a_rectangle_is_read_row_by_row(game: Game) -> None:
    west, north = game.window.x, game.window.y
    part = rectangle(game, x=west + 4, y=north + 2, width=3, height=2)
    whole = rectangle(game)
    rows = [whole['cells'][row * 32 + 4 : row * 32 + 7] for row in (2, 3)]

    assert (part['x'], part['y'], part['width'], part['height']) == (west + 4, north + 2, 3, 2)
    assert [part['biomes'][cell] for cell in part['cells']] == [whole['biomes'][cell] for row in rows for cell in row]


@pytest.mark.parametrize(
    ('asked', 'given'),
    [
        ((30, 14, 8, 8), (30, 14, 2, 2)),
        ((-4, -4, 6, 6), (0, 0, 2, 2)),
        ((40, 20, 4, 4), (32, 16, 0, 0)),
        ((-9, 0, 4, 4), (0, 0, 0, 4)),
    ],
)
def test_a_rectangle_is_cut_to_the_window(
    game: Game, asked: tuple[int, int, int, int], given: tuple[int, int, int, int]
) -> None:
    west, north = game.window.x, game.window.y
    part = rectangle(game, west + asked[0], north + asked[1], *asked[2:])

    assert (part['x'] - west, part['y'] - north, part['width'], part['height']) == given
    assert len(part['cells']) == given[2] * given[3]


def test_the_map_is_served_in_rectangles(client: TestClient, new_game: Callable[..., dict[str, Any]]) -> None:
    created = new_game(seed=42)
    address = f'{PREFIX}/games/{created["id"]}/map'

    window = client.get(f'{PREFIX}/games/{created["id"]}/snapshot').json()['window']

    part = client.get(address, params={'x': window['x'] + 4, 'y': window['y'] + 2, 'width': 3, 'height': 2})

    assert part.status_code == 200
    assert set(part.json()) == {'scale', 'x', 'y', 'width', 'height', 'biomes', 'cells'}
    assert len(part.json()['cells']) == 6
    assert len(client.get(address).json()['cells']) == 32 * 16
    assert client.get(address, params={'width': -1}).status_code == 400
    assert client.get(address, params={'x': 'alpha'}).status_code == 400
