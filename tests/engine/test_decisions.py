from typing import Any

import pytest

from dominion_theory.content import Params, load_params
from dominion_theory.engine import Game, decisions
from dominion_theory.engine.band import Band

SMALL = {'planet.circumference_km': 4000, 'planet.window.width': 32, 'planet.window.height': 16}
ERA = 'band'
HOME = (100, 50)
FOREST = {'biome': 'forest', 'river': False, 'water': 0.6, 'food': 0.9, 'threat': 0.4, 'passability': 0.6, 'seen': 0}
STRIPPED = {**FOREST, 'food': 0.09}
SEA = {'biome': 'water', 'river': False, 'water': 1.0, 'food': 0.3, 'threat': 0.2, 'passability': 0.0, 'seen': 0}
SHALLOWS = {**SEA, 'biome': 'shallows', 'food': 0.5, 'threat': 0.6, 'passability': 0.3}


def held(known: dict[tuple[int, int], dict[str, Any]], forage: float, water: float, **given: Any) -> Band:
    stores = {'forage': [[0.0, forage]], 'water': [[0.0, water]]}
    return Band(id=1, x=HOME[0], y=HOME[1], population=15, stores=stores, known=dict(known), **given)


def scores(params: Params, band: Band, part: str = 'midday') -> dict[str, float]:
    found = decisions.options(params, band, part, ERA)
    return {str(scored.action.get('towards', scored.action.get('resource', 'camp'))): scored.score for scored in found}


def fixed(index: int) -> Any:
    return lambda count: index % count


def test_needs_follow_the_stores_the_fatigue_and_the_night(params: Params) -> None:
    band = held({}, forage=22.5, water=30.0, fatigue=0.1)

    by_day = decisions.needs(params, band, 'midday')
    by_night = decisions.needs(params, band, 'night')

    assert by_day == pytest.approx({'hunger': 0.5, 'thirst': 1 / 3, 'rest': 0.1})
    assert by_night['rest'] == pytest.approx(0.6)


def test_a_state_doubles_its_need_and_a_need_is_held_at_one(params: Params) -> None:
    band = held({}, forage=30.0, water=0.0, fatigue=0.6, states=['starvation', 'thirst', 'tiredness'])

    assert decisions.needs(params, band, 'midday') == pytest.approx({'hunger': 2 / 3, 'thirst': 1.0, 'rest': 1.0})


def test_a_band_that_eats_nothing_is_never_hungry() -> None:
    params = load_params(overrides={**SMALL, 'units.band.consumption_per_day.forage': 0.0})

    assert decisions.needs(params, held({}, forage=0.0, water=45.0), 'midday')['hunger'] == 0.0


def test_the_first_example_of_the_document_gathers_forage(params: Params) -> None:
    band = held({HOME: FOREST}, forage=22.5, water=30.0, fatigue=0.1)

    found = scores(params, band)

    assert found == pytest.approx({'camp': 0.07, 'forage': 1.5 * 0.5 * 0.9 * 37.5 / 40.5, 'water': 1.2 / 3 * 0.6})
    assert decisions.decide(params, band, 'midday', 0, ERA) == {'kind': 'gather', 'resource': 'forage'}
    assert band.reason == {
        'action': 'gather',
        'resource': 'forage',
        'need': 'hunger',
        'score': pytest.approx(0.625),
        'pull': None,
    }


def test_the_second_example_of_the_document_camps_at_night(params: Params) -> None:
    band = held({HOME: FOREST}, forage=37.5, water=30.0, fatigue=0.55)

    found = scores(params, band, 'night')

    fit = {'forage': 22.5 / 40.5, 'water': 22.5 / 36}

    assert found == pytest.approx({'camp': 0.7, 'forage': 1.5 / 6 * 0.9 * fit['forage'], 'water': 0.24 * fit['water']})
    assert decisions.decide(params, band, 'night', 0, ERA) == {'kind': 'camp'}
    assert band.reason is not None
    assert band.reason['need'] == 'rest'


def test_the_third_example_of_the_document_walks_to_the_remembered_forest() -> None:
    params = load_params(overrides={**SMALL, 'units.band.consumption_per_day.water': 0.0})
    east, far = (HOME[0] + 1, HOME[1]), (HOME[0] + 3, HOME[1])
    band = held({HOME: STRIPPED, east: STRIPPED, far: FOREST}, forage=11.25, water=0.0, fatigue=0.1)

    found = scores(params, band)

    assert found == pytest.approx(
        {
            'camp': 0.07,
            'forage': 1.5 * 0.75 * 0.09,
            'water': 0.0,
            'east': 3.0 * ((0.75 * 0.9 - 0.12) / 1.75 - (0.75 * 0.09 - 0.12)) - 0.7 * 0.1 / 0.6,
        }
    )
    assert decisions.decide(params, band, 'midday', 0, ERA) == {'kind': 'move', 'towards': 'east'}
    assert band.reason is not None
    assert (band.reason['need'], band.reason['pull']) == ('hunger', {'x': far[0], 'y': far[1]})


def test_a_cell_the_band_has_not_seen_does_not_pull(params: Params) -> None:
    east = (HOME[0] + 1, HOME[1])
    blind = held({HOME: STRIPPED, east: STRIPPED}, forage=11.25, water=45.0, fatigue=0.1)

    found = scores(params, blind)

    assert found['east'] < found['forage']
    assert set(found) == {'camp', 'forage', 'water', 'east'}


def test_a_loaded_band_does_not_gather(params: Params) -> None:
    band = held({HOME: FOREST}, forage=15.0, water=75.0)

    found = scores(params, band)

    assert (found['forage'], found['water']) == (0.0, 0.0)


def test_a_cell_gives_only_what_its_biome_lists(params: Params) -> None:
    band = held({HOME: {**FOREST, 'biome': 'snow'}}, forage=0.0, water=0.0)

    assert set(scores(params, band)) == {'camp', 'water'}


def test_water_is_no_way_and_a_shore_only_beside_known_land(params: Params) -> None:
    east, further, north = (HOME[0] + 1, HOME[1]), (HOME[0] + 2, HOME[1]), (HOME[0], HOME[1] - 1)
    band = held({HOME: FOREST, east: SHALLOWS, further: SHALLOWS, north: SEA}, forage=0.0, water=0.0)

    assert decisions.reachable(params, band, east, ERA)
    assert not decisions.reachable(params, band, further, ERA)
    assert not decisions.reachable(params, band, north, ERA)
    assert not decisions.reachable(params, band, (HOME[0] - 1, HOME[1]), ERA)
    assert set(scores(params, band)) == {'camp', 'forage', 'water', 'east'}


def test_a_tie_goes_to_the_first_in_the_order_and_a_move_in_progress_is_kept(params: Params) -> None:
    around = {(HOME[0] + dx, HOME[1] + dy): FOREST for dx in (-1, 0, 1) for dy in (-1, 0, 1)}
    band = held({**around, HOME: STRIPPED}, forage=0.0, water=45.0)

    first = decisions.decide(params, band, 'midday', 0, ERA)
    band.target = (HOME[0] - 1, HOME[1])
    kept = decisions.decide(params, band, 'midday', 0, ERA)

    assert first == {'kind': 'move', 'towards': 'north'}
    assert kept == {'kind': 'move', 'towards': 'west'}
    assert scores(params, band)['west'] == pytest.approx(scores(params, band)['north'] + 0.1)


def test_a_band_with_nothing_to_want_wanders_and_keeps_its_way_for_a_day(params: Params) -> None:
    around = {(HOME[0] + dx, HOME[1] + dy): FOREST for dx in (-1, 0, 1) for dy in (-1, 0, 1)}
    band = held(around, forage=45.0, water=45.0)

    first = decisions.decide(params, band, 'midday', 4, ERA, fixed(2))
    same_day = decisions.decide(params, band, 'afternoon', 4, ERA, fixed(5))
    next_day = decisions.decide(params, band, 'midday', 5, ERA, fixed(5))

    assert first == same_day == {'kind': 'move', 'towards': 'east'}
    assert next_day == {'kind': 'move', 'towards': 'south-west'}
    assert band.wander == {'towards': 'south-west', 'until': 6}
    assert band.reason is not None
    assert (band.reason['action'], band.reason['need']) == ('move', 'wander')


def test_a_band_that_has_a_reason_draws_nothing(params: Params) -> None:
    def never(count: int) -> int:
        raise AssertionError(count)

    band = held({HOME: FOREST}, forage=0.0, water=45.0, wander={'towards': 'east', 'until': 9})

    assert decisions.decide(params, band, 'midday', 0, ERA, never) == {'kind': 'gather', 'resource': 'forage'}
    assert band.wander is None


def test_a_band_with_nowhere_to_go_camps_instead_of_wandering(params: Params) -> None:
    band = held({HOME: FOREST}, forage=45.0, water=45.0)

    assert decisions.decide(params, band, 'midday', 0, ERA, fixed(0)) == {'kind': 'camp'}


def test_a_band_on_a_stripped_cell_walks_to_better_land(params: Params) -> None:
    game = Game.create(seed=7, params=load_params(overrides={**SMALL, 'encounters.chance': 0.0}))
    assert game.band is not None
    start = game.band.place
    for dx in (-2, -1, 0, 1, 2):
        for dy in (-2, -1, 0, 1, 2):
            at = start[0] + dx, start[1] + dy
            if at != (start[0] + 2, start[1]) and game.biome(*at) == 'forest':
                game.deplete(*at, 'food', 0.95)
    game.band.stores['forage'] = []

    for _ in range(12):
        game.step()

    assert game.band.place != start
    assert dict(zip(game.counters.names, game.counters.row(), strict=True))['moves'] > 0


def test_a_year_alone_gives_the_same_hashes_twice(params: Params) -> None:
    first, second = Game.create(seed=7, params=params), Game.create(seed=7, params=params)

    assert [first.step().hash for _ in range(500)] == [second.step().hash for _ in range(500)]
    assert first.tick == 500
