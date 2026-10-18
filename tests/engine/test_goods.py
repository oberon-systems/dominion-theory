from typing import Any

import numpy as np
import pytest

from dominion_theory.content import Params, load_params
from dominion_theory.engine import Game, StepResult, Window, decisions
from dominion_theory.engine import band as bands
from dominion_theory.engine.band import Action, Member, camp, gathering
from dominion_theory.engine.stock import Stock
from dominion_theory.engine.streams import Streams
from dominion_theory.planet import biome_names

SMALL = {
    'planet.circumference_km': 4000,
    'planet.window.width': 32,
    'planet.window.height': 16,
    'encounters.chance': 0.0,
    'units.band.camp_parts': [],
    'units.band.decisions.horizon': 0,
    'units.band.unease.gain': 0.0,
    'units.band.people.birth.conceive_per_day': 0.0,
    'units.band.people.injury.per_day': 0.0,
    'units.band.people.age.per_year': 0.0,
    'units.band.people.stages.adult.dies.frailty': 0.0,
}
WEST = 100
NORTH = 50
ROWS = (
    ('hills', 'hills', 'forest'),
    ('hills', 'grass', 'forest'),
)
HOME = (WEST, NORTH + 1)
SUMMER = 100
DAY = 5
SPEARS = {
    'kind': 'goods',
    'held': 'personal',
    'weight_kg': 1.5,
    'wears': {'months': 6},
    'keep': {'per': 'adult', 'amount': 1.0},
    'gives': [{'to': 'member', 'path': 'units.band.people.injury.per_day', 'times': 0.5}],
}


@pytest.fixture
def params() -> Params:
    return load_params(overrides=SMALL)


def land(params: Params, parts: int = SUMMER, at: tuple[int, int] = HOME) -> Game:
    """
    A game on a hand-made window of hills and forest in summer, with a band of adults on the hills.
    """
    names = biome_names(params)
    biomes = np.array([[names.index(name) for name in row] for row in ROWS], dtype=np.uint8)
    rivers = np.zeros(biomes.shape, dtype=np.bool_)
    game = Game(7, params, Streams(7), Window(0, WEST, NORTH, len(ROWS[0]), len(ROWS)), biomes, rivers)
    game.clock.parts = parts
    game.band = bands.start(game, *at, game.day, game.streams['people'])
    game.band.members = bands.adults(game.band.population)
    game.band.changed()
    return game


def holding(stores: dict[str, list[list[float]]], members: list[Member] | None = None) -> bands.Band:
    return bands.Band(id=1, x=WEST, y=NORTH, members=members or bands.adults(10), stores=Stock(stores))


def armed() -> Params:
    tree = load_params(overrides={**SMALL, 'units.band.people.injury.per_day': 0.002}).tree()
    tree['resources']['spears'] = SPEARS
    return Params.model_validate(tree)


def do(game: Game, action: Action) -> StepResult:
    game.choose = lambda _game, _band: action
    return game.step()


def band(game: Game) -> bands.Band:
    assert game.band is not None
    return game.band


def shares(params: Params, held: bands.Band) -> dict[str, Any]:
    found = [option.action for option in decisions.options(params, held, 'band') if option.action['kind'] == 'gather']
    return found[0]['shares'] if found else {}


def test_stones_are_gathered_of_a_quality_drawn_from_the_range_of_the_hills(params: Params) -> None:
    game = land(params)

    do(game, gathering({'stones': 1.0}))

    lots = band(game).stores['stones']
    assert len(lots) == 1
    assert lots[0][1] == pytest.approx(15 * 0.5 * 0.5)
    assert 0.5 <= lots[0][2] <= 0.75


def test_a_gathering_of_goods_stops_at_their_keep(params: Params) -> None:
    game = land(params, at=(WEST + 2, NORTH))
    band(game).stores.add('sticks', game.day, 1.5)

    do(game, gathering({'sticks': 1.0}))

    assert band(game).held('sticks') == pytest.approx(0.3 * 15)


def test_stones_wear_out_by_their_quality_and_the_band_is_told(params: Params) -> None:
    game = land(params)
    band(game).stores = Stock({'stones': [[0.0, 1.0, 0.5], [0.0, 2.0, 1.0]]})
    game.clock.parts = 31 * DAY

    result = do(game, camp())

    assert [event.values for event in result.events if event.key == 'goods-worn'] == [
        {'resource': 'stones', 'count': 1.0}
    ]
    assert band(game).held('stones') == 2.0


def test_a_band_without_goods_lives_by_the_tree_as_it_is(params: Params) -> None:
    assert bands.applied(params, holding({'forage': [[0.0, 5.0]]})) is params


def test_stones_held_lay_their_bonuses_by_the_share_of_the_keep(params: Params) -> None:
    half = bands.applied(params, holding({'stones': [[0.0, 1.5, 0.8]]}))
    full = bands.applied(params, holding({'stones': [[0.0, 9.0, 0.8]]}))

    assert half.units.band.consumption_per_day['forage'] == pytest.approx(0.95)
    assert params.days(half.units.band.people.age.begins) == 1750
    assert full.units.band.consumption_per_day == pytest.approx({'forage': 0.9, 'water': 1.0})
    assert params.days(full.units.band.people.age.begins) == 1800
    assert params.units.band.consumption_per_day['forage'] == 1.0


def test_sticks_held_lower_the_threat_the_band_meets_in_camp(params: Params) -> None:
    guard = bands.applied(params, holding({'sticks': [[0.0, 3.0]]})).units.band.threat

    assert (guard.camp, guard.march) == pytest.approx((0.8, 1.0))


def test_the_bonuses_are_kept_until_the_goods_change(params: Params) -> None:
    held = holding({'stones': [[0.0, 1.5, 0.8]]})
    laid = bands.applied(params, held)

    assert bands.applied(params, held) is laid
    held.stores.add('stones', 1, 1.5, 0.8)
    held.restocked()
    assert bands.applied(params, held).units.band.consumption_per_day['forage'] == pytest.approx(0.9)


def test_a_fed_band_that_knows_stone_tools_gathers_stones_and_a_hungry_one_does_not(params: Params) -> None:
    game = land(params)
    held = band(game)
    held.stores = Stock({'forage': [[20.0, 40.0]], 'water': [[20.0, 40.0]]})
    held.changed()

    assert 'stones' not in shares(params, held)
    held.lore['known'].append('stone_tools')
    held.restocked()
    assert shares(params, held)['stones'] > shares(params, held)['forage']
    held.stores = Stock()
    held.changed()
    assert 'stones' not in shares(params, held)


def test_personal_goods_go_to_those_their_keep_counts_and_back_from_the_dead() -> None:
    params = armed()
    held = holding({'spears': [[0.0, 2.0, 0.9]]}, [*bands.adults(3), Member(100, 'female')])

    bands.hand_out(params, held)

    assert [member.kit.held('spears') for member in held.members] == [1.0, 1.0, 0.0, 0.0]
    assert held.members[0].kit['spears'] == [[0.0, 1.0, 0.9]]
    assert bands.weight(params, held) == 3.0
    assert bands.shared(params, held, 'spears') == pytest.approx(2 / 3)
    assert bands.applied(params, held, held.members[0]).units.band.people.injury.per_day == pytest.approx(0.001)
    assert bands.applied(params, held, held.members[2]).units.band.people.injury.per_day == 0.002
    bands.bury(held, [0])
    assert held.held('spears') == 1.0
    assert bands.goods(params, held) == {'spears': 2.0}
