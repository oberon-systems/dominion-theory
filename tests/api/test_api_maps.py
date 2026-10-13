from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient

from dominion_theory.api import PREFIX
from dominion_theory.api.maps import rectangle
from dominion_theory.api.schemas import STREAM, Update
from dominion_theory.content import load_params
from dominion_theory.engine import Game
from dominion_theory.runner import Service

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


def test_an_untouched_map_has_rivers_and_full_stocks(game: Game) -> None:
    whole = rectangle(game)
    part = rectangle(game, x=game.window.x + 4, y=game.window.y + 2, width=3, height=2)

    assert game.stocked == ('water', 'food')
    assert whole['rivers'] == game.rivers.astype(int).ravel().tolist()
    assert set(whole['rivers']) <= {0, 1}
    assert whole['water'] == whole['food'] == [1.0] * (32 * 16)
    assert part['rivers'] == game.rivers[2:4, 4:7].astype(int).ravel().tolist()
    assert part['water'] == part['food'] == [1.0] * 6


def test_a_lowered_stock_is_shown_at_its_cell() -> None:
    game = Game.create(seed=42, params=load_params(overrides=SMALL))
    west, north = game.window.x, game.window.y
    game.deplete(west + 5, north + 3, 'food', 0.25)

    whole = rectangle(game)
    part = rectangle(game, x=west + 4, y=north + 2, width=3, height=2)
    beside = rectangle(game, x=west + 6, y=north + 2, width=3, height=2)

    assert whole['food'][3 * 32 + 5] == 0.75
    assert whole['food'].count(1.0) == 32 * 16 - 1
    assert whole['water'] == [1.0] * (32 * 16)
    assert part['food'] == [1.0, 1.0, 1.0, 1.0, 0.75, 1.0]
    assert beside['food'] == [1.0] * 6


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
    assert len(part['cells']) == len(part['rivers']) == len(part['water']) == len(part['food']) == given[2] * given[3]


def test_the_map_is_served_in_rectangles(client: TestClient, new_game: Callable[..., dict[str, Any]]) -> None:
    created = new_game(seed=42)
    address = f'{PREFIX}/games/{created["id"]}/map'

    window = client.get(f'{PREFIX}/games/{created["id"]}/snapshot').json()['window']

    part = client.get(address, params={'x': window['x'] + 4, 'y': window['y'] + 2, 'width': 3, 'height': 2})

    assert part.status_code == 200
    assert set(part.json()) == {'scale', 'x', 'y', 'width', 'height', 'biomes', 'cells', 'rivers', 'water', 'food'}
    assert [len(part.json()[name]) for name in ('cells', 'rivers', 'water', 'food')] == [6, 6, 6, 6]
    assert len(client.get(address).json()['cells']) == 32 * 16
    assert client.get(address, params={'width': -1}).status_code == 400
    assert client.get(address, params={'x': 'alpha'}).status_code == 400


def test_a_depletion_reaches_the_map_and_the_stream(
    client: TestClient, new_game: Callable[..., dict[str, Any]], service: Service
) -> None:
    created = new_game(seed=42)
    game = service.find(created['id']).game
    x, y = game.window.x + 5, game.window.y + 3
    address = f'{PREFIX}/games/{created["id"]}'

    game.deplete(x, y, 'food', 0.5)
    shown = client.get(f'{address}/map', params={'x': x, 'y': y, 'width': 1, 'height': 1}).json()
    with client.websocket_connect(f'{address}/updates?after=0') as stream:
        assert client.post(f'{address}/clock', json={'action': 'step'}).status_code == 200
        update = stream.receive_json()
    (cell,) = update['changes']['cells']

    assert (shown['food'], shown['water']) == ([0.5], [1.0])
    assert isinstance(STREAM.validate_python(update), Update)
    assert set(cell) == {'x', 'y', 'water', 'food'}
    assert (cell['x'], cell['y'], cell['water']) == (x, y, 1.0)
    assert 0.5 < cell['food'] < 0.6
    assert client.get(f'{address}/map').json()['food'][3 * 32 + 5] == cell['food']
