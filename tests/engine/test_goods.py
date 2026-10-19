from typing import Any

import numpy as np
import pytest

from dominion_theory.content import Duration, Params, load_params
from dominion_theory.engine import Game, StepResult, Window, decisions, encounters
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
GRASS = (WEST + 1, NORTH + 1)
SUMMER = 100
DAY = 5
SPEARS = {
    'kind': 'goods',
    'held': 'personal',
    'weight_kg': 1.5,
    'wears': {'attacks': 1},
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


def test_stones_wear_by_the_food_they_cut_and_a_poor_one_cuts_less(params: Params) -> None:
    held = holding({'stones': [[0.0, 1.0, 0.5]], 'forage': [[0.0, 20.0]], 'water': [[0.0, 20.0]]})

    bands.eat(params, held)

    eaten = 20.0 - held.held('forage')
    assert eaten > 0
    assert held.held('stones') == pytest.approx(1.0 - eaten / 150)
    assert held.worn == pytest.approx({'stones': eaten / 150})


def test_stones_kept_in_the_stores_do_not_wear_while_nothing_is_eaten(params: Params) -> None:
    held = holding({'stones': [[0.0, 1.0, 0.5]]})

    bands.eat(params, held)
    bands.spoil(params, held, 1000)

    assert held.held('stones') == 1.0
    assert held.worn == {} and held.spoiled == {}


def test_sticks_wear_by_the_heads_they_keep_at_night_and_break_in_attacks(params: Params) -> None:
    held = holding({'sticks': [[0.0, 3.0]]})

    bands.wear(params, held, bands.NIGHTS, 40)
    assert held.held('sticks') == pytest.approx(2.9)
    bands.wear(params, held, bands.ATTACKS, 1)
    assert held.held('sticks') == pytest.approx(1.9)
    assert held.worn == pytest.approx({'sticks': 1.1})


def test_an_attack_in_camp_breaks_a_stick_and_one_on_the_march_does_not(
    params: Params, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(encounters, 'strike', lambda *_: ('predator', 0.0, 0.0))
    game = land(params, at=(WEST + 2, NORTH))
    band(game).stores = Stock({'sticks': [[0.0, 3.0]], 'forage': [[0.0, 90.0]], 'water': [[0.0, 90.0]]})

    do(game, camp())
    assert band(game).held('sticks') == pytest.approx(2.0)
    do(game, bands.moving('west'))
    assert band(game).held('sticks') == pytest.approx(2.0)


def test_goods_lost_are_told_in_whole_units_and_the_rest_waits(params: Params) -> None:
    game = land(params)
    band(game).stores = Stock({'sticks': [[0.0, 2.5]]})
    band(game).worn = {'stones': 1.2}
    game.clock.parts = 101 * DAY

    result = do(game, camp())

    lost = [(event.key, event.values) for event in result.events if event.key.startswith('goods-')]
    assert lost == [
        ('goods-spoiled', {'resource': 'sticks', 'count': 2}),
        ('goods-worn', {'resource': 'stones', 'count': 1}),
    ]
    assert band(game).spoiled == pytest.approx({'sticks': 0.5})
    assert band(game).worn == pytest.approx({'stones': 0.2})


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

    bands.hand_out(params, held, 0)

    assert [member.kit.held('spears') for member in held.members] == [1.0, 1.0, 0.0, 0.0]
    assert held.members[0].kit['spears'] == [[0.0, 1.0, 0.9]]
    assert bands.weight(params, held) == 3.0
    assert bands.shared(params, held, 'spears') == pytest.approx(2 / 3)
    assert bands.applied(params, held, held.members[0]).units.band.people.injury.per_day == pytest.approx(0.001)
    assert bands.applied(params, held, held.members[2]).units.band.people.injury.per_day == 0.002
    bands.bury(params, held, [0], 0)
    assert held.held('spears') == 1.0
    assert bands.goods(params, held) == {'spears': 2.0}


def test_herbs_and_cords_are_gathered_on_the_plants_of_a_forest(params: Params) -> None:
    game = land(params, at=(WEST + 2, NORTH))

    do(game, gathering({'herbs': 0.5, 'cords': 0.5}))

    assert band(game).held('herbs') == pytest.approx(15 * 0.2 * 0.5 * 0.5)
    # The herbs gathered first lowered the plants of the cell the cords are gathered on.
    assert band(game).held('cords') == pytest.approx(15 * 0.3 * 0.5 * 0.5 * (1 - 0.75 / 50))
    assert len(band(game).stores['herbs'][0]) == 2
    assert 0.5 <= band(game).stores['cords'][0][2] <= 0.75


def test_a_band_that_knows_herbs_wants_herbs_and_cords_in_a_forest(params: Params) -> None:
    game = land(params, at=(WEST + 2, NORTH))
    held = band(game)
    held.stores = Stock({'forage': [[20.0, 40.0]], 'water': [[20.0, 40.0]]})
    held.changed()

    assert {'herbs', 'cords'}.isdisjoint(shares(params, held))
    held.lore['known'].append('herbs')
    held.restocked()
    assert {'herbs', 'cords'} <= set(shares(params, held))


def test_litters_are_made_whole_of_the_oldest_materials_at_their_mean_quality(params: Params) -> None:
    held = holding({'sticks': [[0.0, 4.5]], 'cords': [[0.0, 3.0, 0.8]]})

    bands.make(params, held, 1)
    assert held.held('litters') == 0.0
    held.lore['known'].append('litters')
    bands.make(params, held, 1)

    assert held.stores['litters'] == [[1.0, 1.0, 0.92]]
    assert held.work == {'litters': pytest.approx([0.5, 0.46])}
    assert (held.held('sticks'), held.held('cords')) == (0.0, 0.0)
    assert held.made == {'litters': 1.0}


def test_making_stops_at_the_keep_and_at_what_the_adults_make(params: Params) -> None:
    held = holding({'sticks': [[0.0, 90.0]], 'cords': [[0.0, 60.0]]}, bands.adults(3))
    held.lore['known'].append('litters')
    held.members[1].kit.add('litters', 0, 1.0)

    bands.make(params, held, 1)
    assert held.held('litters') == 0.0
    assert held.work['litters'][0] == pytest.approx(0.6)
    for _ in range(5):
        bands.make(params, held, 1)
    assert bands.goods(params, held)['litters'] == pytest.approx(3.0)
    assert held.work == {}


def test_the_good_furthest_below_its_keep_is_made_first(params: Params) -> None:
    tree = params.tree()
    tree['resources']['spears'] = {**SPEARS, 'made': {'sticks': 1.0}}
    two = Params.model_validate(tree)
    held = holding({'sticks': [[0.0, 90.0]], 'cords': [[0.0, 60.0]]}, bands.adults(4))
    held.lore['known'] += ['litters', 'spears']
    held.members[1].kit.add('litters', 0, 1.0)

    bands.make(two, held, 1)
    bands.make(two, held, 1)

    assert held.held('spears') == 1.0
    assert held.held('litters') == 0.0


def test_a_litter_made_in_the_evening_goes_to_a_man_and_is_told(params: Params) -> None:
    camping = load_params(overrides={name: value for name, value in SMALL.items() if name != 'units.band.camp_parts'})
    game = land(camping)
    game.clock.parts = SUMMER + 3
    band(game).lore['known'].append('litters')
    band(game).stores.add('sticks', game.day, 4.5)
    band(game).stores.add('cords', game.day, 3.0, 0.8)

    result = do(game, camp())

    made = [event.values for event in result.events if event.key == 'goods-made']
    assert made == [{'resource': 'litters', 'count': 1}]
    assert band(game).work['litters'][0] == pytest.approx(0.5)
    assert [member.kit.held('litters') for member in band(game).members[:4]] == [0.0, 1.0, 0.0, 0.0]


def test_a_personal_good_is_handed_out_whole_and_a_worn_one_is_not_topped_up(params: Params) -> None:
    held = holding({'litters': [[0.0, 0.6]]}, bands.adults(4))
    held.members[3].kit.add('litters', 0, 0.7)

    bands.hand_out(params, held, 0)
    assert [member.kit.held('litters') for member in held.members] == [0.0, 0.0, 0.0, 0.7]
    held.stores.add('litters', 1, 1.0)
    bands.hand_out(params, held, 1)
    assert [member.kit.held('litters') for member in held.members] == [0.0, 1.0, 0.0, 0.7]
    assert held.held('litters') == pytest.approx(0.6)


def test_a_worn_litter_back_in_the_stores_is_taken_apart_and_a_whole_one_is_kept(params: Params) -> None:
    held = holding({}, bands.adults(3))
    held.members[0].kit.add('litters', 0, 0.43, 0.92)
    held.members[1].kit.add('litters', 0, 1.0, 0.9)

    bands.bury(params, held, [0, 1], 7)

    assert held.stores['litters'] == [[0.0, 1.0, 0.9]]
    assert held.stores['sticks'][0] == pytest.approx([7.0, 0.43 * 3, 0.92])
    assert held.stores['cords'][0] == pytest.approx([7.0, 0.43 * 2, 0.92])


def test_a_puller_carries_more_by_the_sex_and_the_band_walks_slower(params: Params) -> None:
    held = holding({}, bands.adults(2))
    assert bands.carry(params, held) == 12.0

    held.members[1].kit.add('litters', 0, 1.0)
    held.restocked()
    assert bands.carry(params, held) == pytest.approx(22.0)
    assert bands.room(params, held) == pytest.approx(18.0)
    assert bands.applied(params, held).units.band.speed.base == pytest.approx(1.2 * (1 - 0.15 * 0.5))
    held.members[0].kit.add('litters', 0, 1.0)
    held.restocked()
    assert bands.carry(params, held) == pytest.approx(29.0)
    assert bands.room(params, held) == pytest.approx(21.0)
    assert bands.applied(params, held).units.band.speed.base == pytest.approx(1.2 * 0.85)


def test_a_litter_wears_by_a_day_pulled_and_one_in_the_stores_does_not(params: Params) -> None:
    game = land(params)
    band(game).members[1].kit.add('litters', 0, 1.0, 0.8)
    band(game).stores.add('litters', 0, 1.0)
    game.clock.parts = 101 * DAY - 1

    do(game, bands.moving('east'))

    assert band(game).members[1].kit.held('litters') == pytest.approx(1.0 - 1 / 56)
    assert band(game).held('litters') == 1.0
    assert band(game).worn == pytest.approx({'litters': 1 / 56})


class Sure:
    """
    A stream whose every draw comes up.
    """

    def random(self, size: int) -> np.ndarray:
        return np.zeros(size)


def hunting(params: Params, game: Game) -> None:
    """
    The band knows spears and its men the role would take hold one each, as they will by the evening.
    """
    held = band(game)
    held.lore['known'] += ['stone_tools', 'sticks', 'herbs', 'spears']
    for at in bands.chosen(params, held, 'hunter'):
        held.members[at].kit.add('spears', 0, 1.0)
    bands.assign(params, held)


def test_the_men_holding_a_spear_hunt_up_to_one_in_five(params: Params) -> None:
    held = holding({'spears': [[0.0, 1.0]]})

    assert bands.eligible(params, held, 'hunter') == []
    held.lore['known'].append('spears')
    assert bands.eligible(params, held, 'hunter') == [1, 3]
    assert bands.kept(params, held, 'spears') == 2.0
    bands.hand_out(params, held, 0)
    bands.assign(params, held)

    assert [member.role for member in held.members[:4]] == ['gatherer', 'hunter', 'gatherer', 'gatherer']
    assert bands.roles(params, held) == {'gatherer': 9, 'nanny': 0, 'hunter': 1}
    guard = bands.applied(params, held).units.band.threat
    assert (guard.camp, guard.march) == pytest.approx((0.9, 0.9))


def test_hunters_hunt_while_the_band_stands_and_not_while_it_walks(params: Params) -> None:
    game = land(params, at=GRASS)
    hunting(params, game)

    do(game, camp())
    meat = 3 * 4.0 * 0.6
    assert band(game).held('meat') == pytest.approx(meat)
    assert band(game).held('hides') == pytest.approx(meat * 0.05)
    # The stock grows back a tick of its 60 days in the same tick.
    assert game.cells.stock(GRASS, 'game') == pytest.approx(1 - meat / 60 + 1 / 300)
    assert [member.kit.held('spears') for member in band(game).members[1:6:2]] == pytest.approx([1 - 1 / 80] * 3)
    do(game, bands.moving('west'))
    assert band(game).held('meat') == pytest.approx(meat)


def test_hunters_do_not_gather_while_the_band_stands(params: Params) -> None:
    game = land(params, at=(WEST + 2, NORTH))
    hunting(params, game)
    band(game).stores = Stock()

    do(game, gathering({'forage': 1.0}))

    assert band(game).held('forage') == pytest.approx(12 * 3.0 * 0.9)


def test_meat_is_eaten_with_forage_the_oldest_first_and_sickens_by_its_share(params: Params) -> None:
    held = holding({'forage': [[1.0, 6.0]], 'meat': [[0.0, 6.0]], 'water': [[0.0, 20.0]]})

    meal = bands.eat(params, held, Sure())  # type: ignore[arg-type]

    assert (held.held('meat'), held.held('forage')) == (0.0, 2.0)
    assert meal.met == {'forage': 1.0, 'water': 1.0}
    assert meal.sickened == 10
    assert [member.sick for member in held.members] == [5.0] * 10
    assert bands.eat(params, holding({'forage': [[0.0, 20.0]]}), Sure()).sickened == 0  # type: ignore[arg-type]


def test_a_sick_member_gathers_and_walks_less_and_dies_more_of_frailty() -> None:
    params = load_params()
    held = holding({}, bands.adults(2))
    held.members[1].sick = 5.0
    held.changed()

    counted = bands.census(params, held)
    assert (counted.gatherers, counted.pace, counted.sick) == pytest.approx((1.5, 0.85, 1))
    assert bands.vulnerable(params, held, 'frailty') == pytest.approx([0.0, 0.1])


def test_herbs_cure_the_sick_then_cut_a_light_wound_once() -> None:
    params = load_params()
    held = holding({'herbs': [[0.0, 2.5]]}, bands.adults(4))
    held.members[1].sick = 5.0
    held.members[2].wound = {'severity': 'heavy', 'left': 20.0}
    held.members[3].wound = {'severity': 'light', 'left': 8.0}

    assert bands.cure(params, held) == 2
    assert held.members[1].sick == 0.0
    assert held.members[2].wound == {'severity': 'heavy', 'left': 20.0}
    assert held.members[3].wound == {'severity': 'light', 'left': 4.0, 'treated': True}
    assert held.held('herbs') == pytest.approx(0.5)
    held.stores.add('herbs', 1, 1.0)
    assert bands.cure(params, held) == 0


def test_poisoning_leaves_sick_instead_of_dead_while_herbs_last(params: Params) -> None:
    held = holding({'herbs': [[0.0, 1.0]]}, bands.adults(3))

    struck = bands.struck(params, held, 0, 1.0, 0.0, {}, np.random.default_rng(7), True)

    assert struck == (1, 0, 1)
    assert [member.sick for member in held.members] == [0.0, 5.0]
    assert held.held('herbs') == 0.0


def test_clothes_guard_their_holder_and_the_band_by_the_members_holding_them() -> None:
    params = load_params()
    held = holding({}, bands.adults(2))
    held.members[1].kit.add('clothes', 0, 1.0)
    held.restocked()

    worn = bands.applied(params, held, held.members[1]).units.band.people
    assert (worn.injury.per_day, worn.exposure.encounter, worn.exposure.frailty) == pytest.approx((0.0014, 0.8, 1.0))
    assert bands.vulnerable(params, held, 'encounter') == pytest.approx([0.0, 0.8])
    assert bands.vulnerable(params, held, 'frailty', 'winter') == pytest.approx([0.0, 0.05 * 0.7])
    guard = bands.applied(params, held).units.band.threat
    assert (guard.camp, guard.march) == pytest.approx((0.95, 0.95))


def test_a_waterskin_carries_water_beside_the_load_of_its_holder(params: Params) -> None:
    held = holding({'water': [[0.0, 10.0]]}, bands.adults(2))
    assert (bands.weight(params, held), bands.room(params, held, 'water')) == (10.0, 2.0)

    held.members[0].kit.add('waterskins', 0, 1.0)
    held.restocked()
    assert bands.skins(params, held) == 3.0
    assert bands.weight(params, held) == pytest.approx(7.5)
    assert bands.room(params, held, 'water') == pytest.approx(4.5)
    held.stores = Stock({'water': [[0.0, 1.0]]})
    assert bands.room(params, held) == pytest.approx(11.5)
    assert bands.room(params, held, 'water') == pytest.approx(13.5)
    assert bands.room(params, held, 'forage') == pytest.approx(11.5)


def test_water_keeps_longer_by_the_adults_and_elders_holding_a_waterskin(params: Params) -> None:
    held = holding({'water': [[0.0, 10.0]]}, [*bands.adults(2), Member(100, 'female')])
    held.members[0].kit.add('waterskins', 0, 1.0)
    held.restocked()
    assert bands.applied(params, held).resources['water'].spoils == Duration(days=6)

    held.members[1].kit.add('waterskins', 0, 1.0)
    held.restocked()
    assert bands.applied(params, held).resources['water'].spoils == Duration(days=8)
    bands.spoil(params, held, 7)
    assert held.held('water') == 10.0
    bands.spoil(params, held, 8)
    assert held.held('water') == 0.0


def test_waterskins_go_to_the_adults_then_the_elders_and_never_to_a_child(params: Params) -> None:
    elder = bands.bounds(params, 'adult')[1] + 1
    held = holding({'waterskins': [[0.0, 3.0, 0.9]]}, [Member(elder, 'male'), Member(100, 'female'), *bands.adults(1)])

    bands.hand_out(params, held, 0)

    assert [member.kit.held('waterskins') for member in held.members] == [1.0, 0.0, 1.0]
    assert held.held('waterskins') == 1.0


def test_a_day_of_raw_meat_sickens_and_herbs_cure_the_sick_that_evening() -> None:
    params = load_params(overrides={**SMALL, 'resources.meat.sickens': 1.0})
    game = land(params)
    band(game).stores = Stock({'meat': [[100.0, 30.0]], 'water': [[100.0, 30.0]], 'herbs': [[100.0, 2.0]]})
    game.clock.parts = 101 * DAY - 1

    result = do(game, camp())

    told = [(event.key, event.values) for event in result.events if event.key.startswith('people-')]
    assert told == [('people-sickened', {'count': 15, 'cause': 'meat'}), ('people-cured', {'count': 2})]
    assert bands.census(params, band(game)).sick == 13
    assert band(game).held('herbs') == 0.0


def test_a_band_beside_a_forest_gathers_a_share_of_its_sticks_and_its_food_from_its_own_cell(params: Params) -> None:
    game = land(params, at=GRASS)
    beside = (WEST + 2, NORTH)

    assert bands.source(game, GRASS, 'sticks') == (beside, 0.3)
    assert bands.source(game, GRASS, 'forage') == (GRASS, 1.0)
    do(game, gathering({'sticks': 1.0}))

    assert band(game).held('sticks') == pytest.approx(15 * 1.0 * 0.8 * 0.3)
    # Wood grows back in 30 days, a 150th of the stock in the same tick.
    assert game.cells.stock(beside, 'wood') == pytest.approx(1 - 15 * 1.0 * 0.8 * 0.3 / 100 + 1 / 150)
