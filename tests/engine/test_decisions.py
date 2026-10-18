from typing import Any

import pytest

from dominion_theory.content import Params, load_params
from dominion_theory.engine import Game, decisions
from dominion_theory.engine.band import Band, adults, held_days
from dominion_theory.engine.stock import Stock

SMALL = {
    'planet.circumference_km': 4000,
    'planet.window.width': 32,
    'planet.window.height': 16,
    'units.band.decisions.horizon': 0,
}
ERA = 'band'
HOME = (100, 50)
FOREST = {'biome': 'forest', 'river': False, 'water': 0.6, 'food': 0.9, 'threat': 0.4, 'passability': 0.6, 'seen': 0}
STRIPPED = {**FOREST, 'food': 0.09}
SEA = {'biome': 'water', 'river': False, 'water': 1.0, 'food': 0.3, 'threat': 0.2, 'passability': 0.0, 'seen': 0}
SHALLOWS = {**SEA, 'biome': 'shallows', 'food': 0.5, 'threat': 0.6, 'passability': 0.0}
GRASS = {'biome': 'grass', 'river': False, 'water': 0.28, 'food': 0.8, 'threat': 0.1, 'passability': 1.0, 'seen': 0}
EAST = (HOME[0] + 1, HOME[1])


def held(known: dict[tuple[int, int], dict[str, Any]], forage: float, water: float, **given: Any) -> Band:
    stores = Stock({'forage': [[0.0, forage]], 'water': [[0.0, water]]})
    return Band(id=1, x=HOME[0], y=HOME[1], members=adults(15), stores=stores, known=dict(known), **given)


def scores(params: Params, band: Band) -> dict[str, float]:
    found = {}
    for scored in decisions.options(params, band, ERA):
        name = str(scored.action.get('towards', 'gather' if scored.action['kind'] == 'gather' else 'camp'))
        found[f'roam-{name}' if scored.action['kind'] == 'roam' else name] = scored.score
    return found


def shared(params: Params, band: Band) -> dict[str, float]:
    gathered = [scored.action for scored in decisions.options(params, band, ERA) if scored.action['kind'] == 'gather']
    return dict(gathered[0]['shares']) if gathered else {}


def fixed(index: int) -> Any:
    return lambda count: index % count


def test_needs_follow_the_stores_and_not_the_fatigue(params: Params) -> None:
    band = held({}, forage=22.5, water=30.0, fatigue=0.9)

    assert decisions.needs(params, band) == pytest.approx({'hunger': 0.4, 'thirst': 0.1})


@pytest.mark.parametrize(('days', 'need'), [(5.0, 0.1), (2.0, 0.1), (1.5, 0.4), (1.0, 0.4), (0.5, 0.8), (0.0, 0.8)])
def test_hunger_is_the_level_the_days_in_the_stores_reach(params: Params, days: float, need: float) -> None:
    assert decisions.level(params, days) == need


def test_a_need_is_whole_only_when_the_stores_lack_a_day_and_somebody_would_die_tonight(params: Params) -> None:
    empty = held({}, forage=0.0, water=0.0, states=['starvation', 'thirst'])
    stocked = held({}, forage=30.0, water=0.0)
    alive = decisions.needs(params, empty)
    for band in (empty, stocked):
        band.members[1].hungry = 1.0
        band.changed()

    assert alive == pytest.approx({'hunger': 0.8, 'thirst': 0.8})
    assert decisions.needs(params, empty) == pytest.approx({'hunger': 1.0, 'thirst': 0.8})
    assert decisions.needs(params, stocked) == pytest.approx({'hunger': 0.1, 'thirst': 0.8})


def test_a_calm_band_is_one_that_neither_hunger_nor_thirst_presses() -> None:
    assert decisions.calm({'hunger': 0.4, 'thirst': 0.1}) == pytest.approx(0.6)


def around(cell: dict[str, Any]) -> dict[tuple[int, int], dict[str, Any]]:
    return {(HOME[0] + dx, HOME[1] + dy): cell for dx in range(-2, 3) for dy in range(-2, 3)}


def best_move(params: Params, band: Band) -> float:
    return max(held.score for held in decisions.options(params, band, ERA, allowed={'move'}, walking=True))


def test_dread_raises_the_threat_seen_and_unease_sharpens_the_fear_of_it(params: Params) -> None:
    band = held({HOME: FOREST}, 15.0, 15.0)
    band.dread[HOME], band.unease = 0.3, 0.2
    wanted = decisions.needs(params, band)
    fear = 2.0 * decisions.calm(wanted) * 0.7

    assert decisions.seen(params, band, HOME, ERA) == {**FOREST, 'threat': pytest.approx(0.7)}
    assert decisions.here(params, band, wanted, ERA) == pytest.approx(
        decisions.worth(params, {**FOREST, 'threat': 0.7}, wanted)[0] - 0.2 * fear
    )


def test_a_band_leans_out_of_stripped_land_to_the_unknown_but_not_out_of_a_forest_or_grass() -> None:
    blind = load_params(overrides=SMALL)
    hoping = load_params(overrides={**SMALL, 'units.band.decisions.horizon': 2})

    stripped, forest, grass = (held(around(cell), 30.0, 30.0) for cell in (STRIPPED, FOREST, GRASS))

    assert best_move(blind, stripped) < 0 < best_move(hoping, stripped)
    assert best_move(hoping, forest) < 0
    assert best_move(hoping, grass) < 0


def test_unease_sends_a_band_to_poorer_but_safer_land_and_not_on_through_the_same() -> None:
    params = load_params(overrides=SMALL)
    poorer = {**around(FOREST), EAST: {**FOREST, 'threat': 0.3, 'food': 0.1}}
    band, alike = held(poorer, 30.0, 30.0), held(around(FOREST), 30.0, 30.0)

    calm = best_move(params, band)
    band.unease = alike.unease = 0.5

    assert calm < 0 < best_move(params, band)
    assert best_move(params, alike) < 0


def test_wellbeing_is_the_mean_of_fed_watered_safe_and_rested(params: Params) -> None:
    band = held({}, forage=22.5, water=30.0, fatigue=0.2)

    assert decisions.wellbeing(params, band, 0.4) == pytest.approx((0.6 + 0.9 + 0.6 + 0.8) / 4)


def test_a_band_that_eats_nothing_is_never_hungry() -> None:
    params = load_params(overrides={**SMALL, 'units.band.consumption_per_day.forage': 0.0})

    assert decisions.needs(params, held({}, forage=0.0, water=45.0))['hunger'] == 0.0


def test_the_first_example_of_the_document_gathers_forage(params: Params) -> None:
    band = held({HOME: FOREST}, forage=22.5, water=30.0, fatigue=0.1)

    found = scores(params, band)

    shares = {'forage': pytest.approx(5 / 6), 'water': pytest.approx(1 / 6)}
    assert found == pytest.approx({'camp': 0.0, 'gather': 0.5 * 5 / 6 + 1.2 * 0.1 * 0.6 / 6})
    assert decisions.decide(params, band, 0, ERA) == {'kind': 'gather', 'shares': shares}
    assert band.reason == {
        'action': 'gather',
        'shares': shares,
        'need': 'hunger',
        'score': pytest.approx(0.5 * 5 / 6 + 0.072 / 6),
        'pull': None,
    }


def test_a_fed_band_leaves_the_dangerous_forest_for_the_open_grass(params: Params) -> None:
    band = held({HOME: FOREST, EAST: GRASS}, forage=22.5, water=30.0, fatigue=0.1)

    found = scores(params, band)

    own = 0.4 * 0.9 + 0.1 * 0.6 - 2.0 * 0.6 * 0.4
    grass = 0.4 * 0.8 + 0.1 * 0.28 - 2.0 * 0.6 * 0.1
    assert found['east'] == pytest.approx(3.0 * (grass / 1.25 - own))
    assert decisions.decide(params, band, 0, ERA) == {'kind': 'roam', 'towards': 'east'}


def test_a_hungry_band_stays_in_the_forest_to_gather(params: Params) -> None:
    band = held({HOME: FOREST, EAST: GRASS}, forage=7.5, water=30.0, fatigue=0.1)

    found = scores(params, band)

    own = 0.8 * 0.9 + 0.1 * 0.6 - 2.0 * 0.2 * 0.4
    grass = 0.8 * 0.8 + 0.1 * 0.28 - 2.0 * 0.2 * 0.1
    assert found['roam-east'] == pytest.approx(0.75 * 3.0 * (grass / 1.25 - own) + 0.5 * 1.5 * 0.8 * 0.8)
    assert found['gather'] == pytest.approx(1.5 * 0.8 * 0.9 * 10 / 11 + 1.2 * 0.1 * 0.6 / 11)
    assert decisions.decide(params, band, 0, ERA) == {
        'kind': 'gather',
        'shares': {'forage': pytest.approx(10 / 11), 'water': pytest.approx(1 / 11)},
    }


def test_a_hungry_band_only_roams_and_a_fed_one_may_walk(params: Params) -> None:
    hungry = held({HOME: FOREST, EAST: GRASS}, forage=7.5, water=30.0, fatigue=0.1)
    fed = held({HOME: FOREST, EAST: GRASS}, forage=22.5, water=30.0, fatigue=0.1)

    kinds = {
        name: {scored.action['kind'] for scored in decisions.options(params, band, ERA)}
        for name, band in (('hungry', hungry), ('fed', fed))
    }

    assert kinds == {'hungry': {'camp', 'gather', 'roam'}, 'fed': {'camp', 'gather', 'move', 'roam'}}


def test_a_roam_is_the_slower_move_with_the_foraging_of_what_the_band_is_short_of(params: Params) -> None:
    watered = held({HOME: FOREST, EAST: GRASS}, forage=22.5, water=30.0)
    dry = held({HOME: FOREST, EAST: GRASS}, forage=22.5, water=15.0)

    roams = [scores(params, band)['roam-east'] for band in (watered, dry)]

    def walk(thirst: float) -> float:
        own = 0.4 * 0.9 + thirst * 0.6 - 2.0 * 0.6 * 0.4
        grass = 0.4 * 0.8 + thirst * 0.28 - 2.0 * 0.6 * 0.1
        return 0.75 * 3.0 * (grass / 1.25 - own)

    assert roams[0] == pytest.approx(walk(0.1) + 0.5 * 1.5 * 0.4 * 0.8)
    assert roams[1] == pytest.approx(walk(0.4) + 0.5 * (1.5 * 0.4 * 0.8 + 1.2 * 0.4 * 0.28))


def test_an_intent_to_go_gives_the_roam_the_whole_gain(params: Params) -> None:
    band = held({HOME: FOREST, EAST: GRASS}, forage=22.5, water=30.0)
    going = {'kind': 'go', 'to': {'x': EAST[0], 'y': EAST[1]}}

    held_to = decisions.intended(params, band, going, ERA, 'east')
    found = decisions.options(params, band, ERA, decisions.NARROWED['go'], {'east'})

    by_kind = {scored.action['kind']: scored.score for scored in found}
    assert by_kind['roam'] == pytest.approx(by_kind['move'] + 0.5 * 1.5 * 0.4 * 0.8)
    assert held_to.action == {'kind': 'roam', 'towards': 'east'}


def test_the_stripped_example_of_the_document_walks_to_the_remembered_forest() -> None:
    params = load_params(overrides={**SMALL, 'units.band.consumption_per_day.water': 0.0})
    far = (HOME[0] + 3, HOME[1])
    band = held({HOME: STRIPPED, EAST: STRIPPED, far: FOREST}, forage=11.25, water=0.0, fatigue=0.1)

    found = scores(params, band)

    own = 0.8 * 0.09 - 2.0 * 0.2 * 0.4
    forest = 0.8 * 0.9 - 2.0 * 0.2 * 0.4
    assert found == pytest.approx(
        {
            'camp': 0.0,
            'gather': 1.5 * 0.8 * 0.09,
            'roam-east': 0.75 * 3.0 * (forest / 1.75 - own) + 0.5 * 1.5 * 0.8 * 0.09,
        }
    )
    assert decisions.decide(params, band, 0, ERA) == {'kind': 'roam', 'towards': 'east'}
    assert band.reason is not None
    assert (band.reason['need'], band.reason['pull']) == ('hunger', {'x': far[0], 'y': far[1]})


def test_a_cell_the_band_has_not_seen_does_not_pull(params: Params) -> None:
    east = (HOME[0] + 1, HOME[1])
    blind = held({HOME: STRIPPED, east: STRIPPED}, forage=11.25, water=45.0, fatigue=0.1)

    found = scores(params, blind)

    assert found['roam-east'] < found['gather']
    assert set(found) == {'camp', 'gather', 'roam-east'}


def test_a_loaded_band_does_not_gather(params: Params) -> None:
    band = held({HOME: FOREST}, forage=15.0, water=75.0)

    found = scores(params, band)

    assert found['gather'] == 0.0


def test_a_cell_gives_only_what_its_biome_lists(params: Params) -> None:
    band = held({HOME: {**FOREST, 'biome': 'snow'}}, forage=0.0, water=0.0)

    assert set(scores(params, band)) == {'camp', 'gather'}
    assert set(shared(params, band)) == {'water'}


def test_water_and_shallows_are_no_way_and_a_band_beside_the_shallows_gathers_from_them(params: Params) -> None:
    east, north = (HOME[0] + 1, HOME[1]), (HOME[0], HOME[1] - 1)
    band = held({HOME: FOREST, east: SHALLOWS, north: SEA}, forage=0.0, water=0.0)
    inland = held({HOME: FOREST}, forage=0.0, water=0.0)

    assert not any(decisions.reachable(band, at) for at in (east, north, (HOME[0] - 1, HOME[1])))
    assert set(shared(params, band)) == {'forage', 'water'}
    assert decisions.seen(params, band, HOME, ERA) == {**FOREST, 'water': 1.0}
    assert scores(params, band)['gather'] > scores(params, inland)['gather']
    assert shared(params, band) == shared(params, inland)


def test_a_cell_by_the_shallows_lists_what_they_give(params: Params) -> None:
    east = (HOME[0] + 1, HOME[1])
    band = held({HOME: {**FOREST, 'biome': 'snow'}, east: SHALLOWS}, forage=0.0, water=0.0)

    assert decisions.gathers(params, band, HOME, ERA) == {'water', 'forage'}
    assert decisions.seen(params, band, HOME, ERA) == {**FOREST, 'biome': 'snow', 'water': 1.0}
    assert set(shared(params, band)) == {'forage', 'water'}


def test_a_tie_goes_to_the_first_in_the_order_and_a_way_in_progress_is_kept(params: Params) -> None:
    around = {(HOME[0] + dx, HOME[1] + dy): FOREST for dx in (-1, 0, 1) for dy in (-1, 0, 1)}
    band = held({**around, HOME: STRIPPED}, forage=0.0, water=45.0)

    first = decisions.decide(params, band, 0, ERA)
    band.target = (HOME[0] - 1, HOME[1])
    kept = decisions.decide(params, band, 0, ERA)

    assert first == {'kind': 'roam', 'towards': 'north'}
    assert kept == {'kind': 'roam', 'towards': 'west'}
    assert scores(params, band)['roam-west'] == pytest.approx(scores(params, band)['roam-north'] + 0.1)


def test_a_band_with_nothing_to_want_roams_away_and_keeps_its_way_for_a_day(params: Params) -> None:
    around = {(HOME[0] + dx, HOME[1] + dy): FOREST for dx in (-1, 0, 1) for dy in (-1, 0, 1)}
    band = held(around, forage=45.0, water=45.0)

    first = decisions.decide(params, band, 4, ERA, fixed(2))
    same_day = decisions.decide(params, band, 4, ERA, fixed(5))
    next_day = decisions.decide(params, band, 5, ERA, fixed(5))

    assert first == same_day == {'kind': 'roam', 'towards': 'east'}
    assert next_day == {'kind': 'roam', 'towards': 'south-west'}
    assert band.wander == {'towards': 'south-west', 'until': 6}
    assert band.reason is not None
    assert (band.reason['action'], band.reason['need']) == ('roam', 'wander')


def test_a_band_that_has_a_reason_draws_nothing(params: Params) -> None:
    def never(count: int) -> int:
        raise AssertionError(count)

    band = held({HOME: FOREST}, forage=0.0, water=45.0, wander={'towards': 'east', 'until': 9})

    assert decisions.decide(params, band, 0, ERA, never)['kind'] == 'gather'
    assert band.wander is None


def test_a_band_with_nowhere_to_go_camps_instead_of_wandering(params: Params) -> None:
    band = held({HOME: FOREST}, forage=45.0, water=45.0)

    assert decisions.decide(params, band, 0, ERA, fixed(0)) == {'kind': 'camp'}


def test_a_hungry_band_on_a_stripped_cell_roams_to_better_land(params: Params) -> None:
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
    assert dict(zip(game.counters.names, game.counters.row(), strict=True))['roams'] > 0


def test_a_year_alone_gives_the_same_hashes_twice(params: Params) -> None:
    first, second = Game.create(seed=7, params=params), Game.create(seed=7, params=params)

    assert [first.step().hash for _ in range(500)] == [second.step().hash for _ in range(500)]
    assert first.tick == 500


def test_stores_last_for_days_and_for_ever_when_nobody_eats() -> None:
    fasting = load_params(overrides={**SMALL, 'units.band.consumption_per_day.forage': 0.0})
    band = held({}, forage=22.5, water=30.0)

    assert held_days(load_params(overrides=SMALL), band, 'food') == 1.5
    assert held_days(fasting, band, 'food') == float('inf')
