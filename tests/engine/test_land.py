import json
from typing import Any

import numpy as np
import pytest

from dominion_theory.content import Params
from dominion_theory.engine import Game, Window
from dominion_theory.engine.streams import Streams
from dominion_theory.planet import biome_names

# The stocks of stone, wood and plants no cell here has lost.
FULL = {'stone': 1.0, 'wood': 1.0, 'plants': 1.0}
WEST = 100
NORTH = 50
ROWS = (('forest', 'forest', 'water', 'mountain'), ('grass', 'grass', 'grass', 'grass'))
FOREST = (WEST, NORTH)
RIVER = (WEST + 1, NORTH)
SEA = (WEST + 2, NORTH)
GRASS = (WEST, NORTH + 1)
SUMMER = 100
DAY = 5


def land(params: Params, seed: int = 7) -> Game:
    """
    A game on a hand-made window: forest with a river on its second cell, sea, mountain, a row of grass.
    """
    names = biome_names(params)
    biomes = np.array([[names.index(name) for name in row] for row in ROWS], dtype=np.uint8)
    rivers = np.zeros(biomes.shape, dtype=np.bool_)
    rivers[0, 1] = True
    return Game(seed, params, Streams(seed), Window(0, WEST, NORTH, 4, 2), biomes, rivers)


@pytest.fixture
def game(params: Params) -> Game:
    return land(params)


def carried(game: Game) -> dict[str, Any]:
    snapshot = game.snapshot()
    grids = snapshot.pop('grids')
    held: dict[str, Any] = json.loads(json.dumps(snapshot))
    held['grids'] = {name: grid.tolist() for name, grid in grids.items()}
    return held


def depleted(game: Game) -> float:
    return dict(zip(game.counters.names, game.counters.row(), strict=True))['cells_depleted']


def test_a_plain_cell_gives_the_base_under_the_season(game: Game) -> None:
    values = {name: game.value(name, *FOREST) for name in ('water', 'food', 'threat', 'passability')}

    assert game.date.season == 'spring'
    assert values == pytest.approx({'water': 0.6, 'food': 0.9 * 0.7, 'threat': 0.4, 'passability': 0.6})


def test_a_river_adds_and_multiplies(game: Game) -> None:
    values = {name: game.value(name, *RIVER) for name in ('water', 'food', 'threat', 'passability')}

    assert values == pytest.approx({'water': 1.0, 'food': (0.9 + 0.1) * 0.7, 'threat': 0.4, 'passability': 0.6 * 0.7})


@pytest.mark.parametrize(
    ('parts', 'season', 'food'),
    [(0, 'spring', 0.63), (100, 'summer', 0.9), (250, 'autumn', 1.0), (350, 'winter', 0.36)],
)
def test_each_season_lays_its_modifier(game: Game, parts: int, season: str, food: float) -> None:
    game.clock.parts = parts

    assert game.date.season == season
    assert game.value('food', *FOREST) == pytest.approx(food)
    assert game.value('water', *FOREST) == pytest.approx(0.6)


def test_a_value_is_held_between_nothing_and_one(game: Game) -> None:
    game.clock.parts = 250

    assert game.value('food', *RIVER) == 1.0
    assert game.value('water', *RIVER) == 1.0
    assert game.value('passability', *SEA) == 0.0


def test_a_stock_multiplies_the_value(game: Game) -> None:
    game.clock.parts = SUMMER

    game.deplete(*FOREST, 'food', 0.5)
    half = game.value('food', *FOREST)
    game.deplete(*RIVER, 'food', 0.25)
    game.deplete(*FOREST, 'food', 0.8)

    assert half == pytest.approx(0.45)
    assert game.value('food', *RIVER) == pytest.approx((0.9 + 0.1) * 0.75)
    assert game.value('food', *FOREST) == 0.0
    assert game.value('water', *FOREST) == pytest.approx(0.6)
    assert game.cells.stock(FOREST, 'food') == 0.0


@pytest.mark.parametrize(
    ('place', 'name', 'amount', 'said'),
    [
        ((WEST - 1, NORTH), 'food', 0.5, 'outside the window'),
        ((WEST + 4, NORTH), 'food', 0.5, 'outside the window'),
        ((WEST, NORTH + 2), 'food', 0.5, 'outside the window'),
        ((0, 0), 'food', 0.5, 'outside the window'),
        (SEA, 'water', 0.5, 'does not recover'),
        (FOREST, 'threat', 0.5, 'does not recover'),
        (FOREST, 'alpha', 0.5, 'no property alpha'),
        (FOREST, 'food', -0.5, 'not negative'),
    ],
)
def test_a_depletion_that_cannot_be_is_refused(
    game: Game, place: tuple[int, int], name: str, amount: float, said: str
) -> None:
    with pytest.raises(ValueError, match=said):
        game.deplete(*place, name, amount)

    assert len(game.cells) == 0
    assert game.step().changes['cells'] == []


def test_a_value_is_refused_outside_the_window_and_for_an_unknown_property(game: Game) -> None:
    with pytest.raises(ValueError, match='outside the window'):
        game.value('food', WEST, NORTH - 1)
    with pytest.raises(ValueError, match='no property alpha'):
        game.value('alpha', *FOREST)


def test_a_stripped_cell_is_full_after_exactly_its_recovery_time(game: Game) -> None:
    ticks = 3 * DAY
    game.deplete(*FOREST, 'water', 1.0)

    seen = [game.step().changes['cells'] for _ in range(ticks - 1)]
    kept = len(game.cells)
    last = game.step().changes['cells']

    assert game.stocked == ('water', 'food', 'stone', 'wood', 'plants')
    for tick, cells in enumerate(seen, start=1):
        assert cells == [pytest.approx({'x': WEST, 'y': NORTH, 'water': tick / ticks, 'food': 1.0, **FULL})]
    assert kept == 1
    assert last == [{'x': WEST, 'y': NORTH, 'water': 1.0, 'food': 1.0, **FULL}]
    assert len(game.cells) == 0
    assert game.snapshot()['cells'] == []
    assert game.step().changes['cells'] == []
    assert game.value('water', *FOREST) == pytest.approx(0.6)


def test_two_properties_of_a_cell_recover_each_at_its_pace(game: Game) -> None:
    game.deplete(*GRASS, 'water', 1.0)
    game.deplete(*GRASS, 'food', 1.0)

    for _ in range(3 * DAY):
        early = game.step().changes['cells']
    kept = game.snapshot()['cells']
    for _ in range(17 * DAY - 1):
        late = game.step().changes['cells']
    before = len(game.cells)
    last = game.step().changes['cells']

    assert early == [pytest.approx({'x': WEST, 'y': NORTH + 1, 'water': 1.0, 'food': 0.15, **FULL})]
    assert kept == [{'x': WEST, 'y': NORTH + 1, 'stocks': {'food': pytest.approx(0.15)}}]
    assert late == [pytest.approx({'x': WEST, 'y': NORTH + 1, 'water': 1.0, 'food': 0.99, **FULL})]
    assert before == 1
    assert last == [{'x': WEST, 'y': NORTH + 1, 'water': 1.0, 'food': 1.0, **FULL}]
    assert len(game.cells) == 0


def test_a_cell_without_one_of_the_stocks_reports_it_full(game: Game) -> None:
    game.deplete(*SEA, 'food', 0.5)

    (cell,) = game.step().changes['cells']

    assert cell == pytest.approx({'x': WEST + 2, 'y': NORTH, 'water': 1.0, 'food': 0.5 + 1 / (30 * DAY), **FULL})


def test_changed_cells_come_by_coordinate(game: Game) -> None:
    for place in [GRASS, RIVER, FOREST]:
        game.deplete(*place, 'food', 0.5)

    cells = game.step().changes['cells']

    assert [(cell['x'], cell['y']) for cell in cells] == [FOREST, GRASS, RIVER]
    assert [(cell['x'], cell['y']) for cell in game.snapshot()['cells']] == [FOREST, GRASS, RIVER]


def test_the_counter_follows_the_kept_cells(game: Game) -> None:
    game.deplete(*FOREST, 'water', 0.1)
    game.deplete(*GRASS, 'food', 0.9)
    game.deplete(*GRASS, 'water', 0.9)

    first = game.step().counters[2]
    for _ in range(DAY):
        later = game.step().counters[2]

    assert game.counters.names[2] == 'cells_depleted'
    assert (first, later) == (2, 1)
    assert depleted(game) == len(game.cells) == 1


def test_a_restored_game_steps_as_the_original_with_depleted_cells(game: Game) -> None:
    game.deplete(*FOREST, 'food', 0.7)
    game.deplete(*GRASS, 'water', 0.4)
    for _ in range(4):
        game.step()
    game.deplete(*RIVER, 'water', 1.0)

    copy = Game.restore(carried(game))

    assert copy.state_hash() == game.state_hash()
    assert np.array_equal(copy.rivers, game.rivers)
    assert copy.window == game.window
    for _ in range(40 * DAY):
        ours, theirs = game.step(), copy.step()
        assert (theirs.hash, theirs.changes, theirs.counters) == (ours.hash, ours.changes, ours.counters)
    assert len(game.cells) == 0


def test_equal_depletions_give_equal_hashes_and_another_gives_another(params: Params) -> None:
    first, second, other = land(params), land(params), land(params)
    for game in (first, second):
        game.deplete(*FOREST, 'food', 0.5)
    other.deplete(*FOREST, 'food', 0.4)

    same = [(first.step().hash, second.step().hash) for _ in range(10 * DAY)]
    apart = [other.step().hash for _ in range(10 * DAY)]

    assert all(ours == theirs for ours, theirs in same)
    assert not {ours for ours, _ in same} & set(apart)
    assert land(params).state_hash() != land(params, seed=8).state_hash()


def test_the_hash_covers_the_cells_and_the_rivers(params: Params) -> None:
    plain, stripped, crossed = land(params), land(params), land(params)

    stripped.deplete(*FOREST, 'food', 0.5)
    crossed.rivers[1, 2] = True

    assert len({plain.state_hash(), stripped.state_hash(), crossed.state_hash()}) == 3
