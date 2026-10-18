from typing import Any

import numpy as np
import pytest

from dominion_theory.content import Condition, Params, load_params
from dominion_theory.engine import Game, Window, lore
from dominion_theory.engine import band as bands
from dominion_theory.engine.streams import Streams
from dominion_theory.planet import biome_names

SMALL = {
    'planet.circumference_km': 4000,
    'planet.window.width': 32,
    'planet.window.height': 16,
    'encounters.chance': 0.0,
    'units.band.people.birth.conceive_per_day': 0.0,
    'units.band.people.injury.per_day': 0.0,
    'units.band.people.age.per_year': 0.0,
    'units.band.people.stages.adult.dies.frailty': 0.0,
}
WEST = 100
NORTH = 50
# Four biomes in sight from the fourth column, two from the second.
ROWS = (('grass', 'grass', 'grass', 'forest', 'hills', 'swamp', 'swamp'),) * 3
NARROW = (('grass', 'grass', 'grass', 'forest', 'forest', 'forest', 'hills'),) * 3
DAY = 5
SUMMER = 20 * DAY
# The night of the last day of the first winter.
THAW = 100 * DAY - 1


@pytest.fixture
def params() -> Params:
    return load_params(overrides=SMALL)


def land(params: Params, rows: tuple[tuple[str, ...], ...] = ROWS, at: int = 1, parts: int = SUMMER) -> Game:
    """
    A game with no player on a hand-made window in summer, the band in the middle row at the column given.
    """
    names = biome_names(params)
    biomes = np.array([[names.index(name) for name in row] for row in rows], dtype=np.uint8)
    rivers = np.zeros(biomes.shape, dtype=np.bool_)
    game = Game(7, params, Streams(7), Window(0, WEST, NORTH, len(rows[0]), len(rows)), biomes, rivers)
    game.clock.parts = parts
    game.band = bands.start(game, WEST + at, NORTH + 1, game.day, game.streams['people'])
    game.band.members = bands.adults(game.band.population)
    game.band.stores = {'forage': [[float(game.day), 45.0]], 'water': [[float(game.day), 45.0]]}
    game.band.changed()
    return game


def band(game: Game) -> bands.Band:
    assert game.band is not None
    return game.band


def counts(game: Game) -> dict[str, Any]:
    held: dict[str, Any] = band(game).lore['counts']
    return held


def learned(game: Game, ticks: int) -> list[dict[str, Any]]:
    return [event.values for _ in range(ticks) for event in game.step().events if event.key == 'skill-learned']


def condition(**given: Any) -> Condition:
    return Condition.model_validate(given)


def test_a_band_starts_knowing_nothing_and_the_land_it_sees_is_its_first() -> None:
    game = land(load_params(overrides=SMALL))

    assert band(game).lore == {
        'known': [],
        'counts': {
            'seen': ['forest', 'grass'],
            'first': ['forest', 'grass'],
            'winters': 0,
            'walked': {},
            'walked_by': {},
            'camped_by': {},
            'days_in': {},
        },
        'since': {},
    }


def test_a_cell_entered_counts_its_biome_walked_and_every_biome_beside_it(params: Params) -> None:
    game = land(params, at=2)
    band(game).x += 1
    lore.entered(game, band(game))

    assert counts(game)['walked'] == {'forest': 1}
    assert counts(game)['walked_by'] == {'forest': 1, 'grass': 1, 'hills': 1}


def test_a_day_counts_the_land_seen_the_day_in_the_biome_and_the_night_beside_it(params: Params) -> None:
    game = land(params, at=2)
    band(game).x += 2
    bands.look(game, band(game), game.day)
    lore.day_ends(game, band(game))

    assert counts(game)['seen'] == ['forest', 'grass', 'hills', 'swamp']
    assert counts(game)['first'] == ['forest', 'grass', 'hills']
    assert counts(game)['days_in'] == {'hills': 1}
    assert counts(game)['camped_by'] == {'forest': 1, 'hills': 1, 'swamp': 1}


def test_a_counter_reads_a_set_by_its_size_a_biome_by_its_sum_and_new_land_by_its_most(params: Params) -> None:
    game = land(params)
    counts(game).update(
        {'seen': ['forest', 'grass', 'hills'], 'walked': {'grass': 30, 'hills': 12, 'swamp': 7}, 'winters': 2}
    )
    held = counts(game)

    assert lore.counted(condition(counter='seen', at_least=1), held) == 3
    assert lore.counted(condition(counter='winters', at_least=1), held) == 2
    assert lore.counted(condition(counter='walked', biomes=['grass', 'swamp'], at_least=1), held) == 37
    assert lore.counted(condition(counter='walked', biome='new', at_least=1), held) == 12
    assert lore.counted(condition(counter='walked', biome='forest', at_least=1), held) == 0
    assert lore.counted(condition(counter='walked', biome='hills', at_least=1), held, {'walked': {'hills': 5}}) == 7


def test_conditions_join_by_any_and_all_and_hold_what_the_stores_hold(params: Params) -> None:
    game = land(params)
    seen = condition(counter='seen', at_least=2)
    far = condition(counter='seen', at_least=9)
    water = condition(holds={'water': 40})

    assert lore.holds(seen, band(game)) and not lore.holds(far, band(game))
    assert lore.holds(condition(any=[far, water]), band(game))
    assert not lore.holds(condition(all=[far, water]), band(game))
    assert not lore.holds(condition(holds={'water': 50}), band(game))


def test_a_skill_with_needs_counts_only_what_was_gained_once_they_were_met() -> None:
    late = {'needs': ['wintering'], 'learned': {'counter': 'seen', 'at_least': 1}, 'opens': {}}
    params = load_params(overrides={**SMALL, 'skills.orientation': late})
    game = land(params)

    first = lore.learn(params, band(game))
    counts(game)['winters'] = 1
    second = lore.learn(params, band(game))
    third = lore.learn(params, band(game))
    kept = dict(band(game).lore['since'])
    counts(game)['seen'].append('hills')
    fourth = lore.learn(params, band(game))

    assert (first, second, third, fourth) == ([], ['wintering'], [], ['orientation'])
    assert kept['orientation']['seen'] == ['forest', 'grass']
    assert band(game).lore['since'] == {}


def test_a_band_that_sees_four_biomes_learns_orientation_at_the_end_of_the_day(params: Params) -> None:
    game = land(params, at=3)

    before = lore.known(band(game), 'orientation')
    told = learned(game, DAY)

    assert not before
    assert told == [{'skill': 'skill-orientation'}]
    assert game.counters.row()[game.counters.names.index('skills')] == 1


def test_a_band_that_walks_twenty_cells_of_new_land_learns_orientation(params: Params) -> None:
    game = land(params, NARROW)
    counts(game)['walked'] = {'forest': 30, 'grass': 40, 'hills': 19}

    short = lore.learn(params, band(game))
    counts(game)['walked']['hills'] += 1

    assert short == []
    assert lore.learn(params, band(game)) == ['orientation']


def test_a_winter_lived_through_teaches_wintering_at_the_end_of_the_first_day_of_spring(params: Params) -> None:
    game = land(params, NARROW, parts=THAW)

    offered = game.wintering
    game.step()
    winters = counts(game)['winters']
    told = learned(game, DAY)

    assert (offered, winters) == (False, 1)
    assert told == [{'skill': 'skill-wintering'}]


def test_a_known_skill_opens_what_it_opens_and_nothing_else_is_closed(params: Params) -> None:
    game = land(params)
    closed = lore.opened(params, band(game), 'proposals', 'winter_camp')
    band(game).lore['known'].append('wintering')

    assert not closed
    assert lore.opened(params, band(game), 'proposals', 'winter_camp')
    assert lore.opened(params, band(game), 'gathers', 'forage')


def test_the_lore_is_carried_by_the_snapshot_and_shown_as_the_skills_known(params: Params) -> None:
    game = land(params, at=3)
    learned(game, DAY)

    snapshot = game.snapshot()
    copy = Game.restore(snapshot)
    band(copy).lore['counts']['winters'] += 1

    assert band(copy).lore['known'] == ['orientation']
    assert snapshot['units'][0]['lore']['counts']['winters'] == 0
    assert band(game).lore['counts']['winters'] == 0
    assert band(game).shown(params, 0)['lore'] == ['orientation']
