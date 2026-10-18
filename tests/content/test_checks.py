import pytest

from dominion_theory.content import load_params
from dominion_theory.core.errors import DominionError

HALVES = {
    'time.day_parts': ['day', 'night'],
    'units.band.camp_parts': ['night'],
    'council.part': 'day',
}


def refused(overrides: dict[str, object]) -> dict[str, object]:
    with pytest.raises(DominionError) as raised:
        load_params(overrides=overrides)

    assert raised.value.key == 'error-params-invalid'
    return raised.value.values


def test_season_needs_a_month() -> None:
    values = refused({'time.seasons.winter.months': 0})

    assert values['path'] == 'time.seasons.winter.months'
    assert values['found'] == 0
    assert values['expected'] == 'Input should be greater than or equal to 1'


def test_year_needs_a_season() -> None:
    assert refused({'time.seasons': []})['path'] == 'time.seasons'


def test_season_names_do_not_repeat() -> None:
    assert refused({'time.seasons.winter.name': 'spring'}) == {
        'path': 'time.seasons',
        'found': ['spring', 'summer', 'autumn', 'spring'],
        'expected': 'names that do not repeat',
    }


def test_day_part_names_do_not_repeat() -> None:
    assert refused({'time.day_parts': ['day', 'day']})['path'] == 'time.day_parts'


@pytest.mark.parametrize('tick', [1, 5, 10, 50])
def test_tick_divides_a_day_or_covers_whole_days(tick: int) -> None:
    assert load_params(overrides={'eras.band.parts_per_tick': tick}).eras.band.parts_per_tick == tick


@pytest.mark.parametrize('tick', [2, 3, 7, 12])
def test_tick_that_cuts_a_day_is_refused(tick: int) -> None:
    assert refused({'eras.band.parts_per_tick': tick}) == {
        'path': 'eras.band.parts_per_tick',
        'found': tick,
        'expected': 'a divisor or a multiple of the 5 parts of a day',
    }


def test_tick_is_checked_against_the_day_of_the_same_tree() -> None:
    params = load_params(overrides={**HALVES, 'eras.band.parts_per_tick': 2})

    assert params.eras.band.parts_per_tick == 2


BAND = 'biomes.forest.eras.band'
BARE = {'properties': {'food': {'base': 0.5}}, 'resources': []}
TINY = {'eras.band.cell_km': 1, 'planet.skeleton_km': 1, 'planet.window.width': 4, 'planet.window.height': 4}


def test_biome_gives_exactly_the_properties_of_its_era() -> None:
    values = refused({f'{BAND}.properties': {'food': {'base': 0.5}}})

    assert values == {
        'path': f'{BAND}.properties',
        'found': ['food'],
        'expected': 'the properties water, food, threat, passability, stone, wood',
    }
    assert refused({'eras.band.properties': ['water', 'food']})['path'] == 'biomes.desert.eras.band.properties'


def test_biome_gives_every_era_and_no_other() -> None:
    assert refused({'biomes.forest.eras': {}})['path'] == 'biomes.forest.eras'
    assert refused({'biomes.forest.eras': {'band': BARE, 'alpha': BARE}}) == {
        'path': 'biomes.forest.eras',
        'found': ['alpha', 'band'],
        'expected': 'the eras band',
    }


def test_season_of_a_modifier_exists() -> None:
    assert refused({f'{BAND}.properties.food.seasons': {'monsoon': {'times': 2.0}}}) == {
        'path': f'{BAND}.properties.food.seasons',
        'found': 'monsoon',
        'expected': 'one of spring, summer, autumn, winter',
    }


def test_resource_is_a_known_one() -> None:
    assert refused({f'{BAND}.resources': ['water', 'stone']}) == {
        'path': f'{BAND}.resources',
        'found': 'stone',
        'expected': 'one of water, forage, stones, sticks',
    }
    assert refused({f'{BAND}.resources': ['water', 'water']})['expected'] == 'names that do not repeat'


def test_orders_of_generation_do_not_repeat() -> None:
    values = refused({'biomes.forest.generation.order': 50})

    assert (values['path'], values['expected']) == ('biomes', 'orders of generation that do not repeat')


@pytest.mark.parametrize(
    ('overrides', 'found'),
    [
        ({'biomes.grass.generation': {'order': 90, 'moisture': {'max': 0.5}}}, []),
        ({'biomes.forest.generation': {'order': 70}}, ['forest', 'grass']),
    ],
)
def test_exactly_one_biome_has_no_ranges(overrides: dict[str, object], found: list[str]) -> None:
    assert refused(overrides) == {'path': 'biomes', 'found': found, 'expected': 'exactly one biome with no ranges'}


@pytest.mark.parametrize('written', [{'min': 0.6, 'max': 0.5}, {}, {'min': 2.0}])
def test_range_that_holds_nothing_is_refused(written: dict[str, float]) -> None:
    path = str(refused({'biomes.forest.generation.moisture': written})['path'])

    assert path.startswith('biomes.forest.generation.moisture')


@pytest.mark.parametrize(
    ('path', 'value', 'where'),
    [
        (f'{BAND}.properties.food.base', 1.1, f'{BAND}.properties.food.base'),
        (f'{BAND}.properties.food.base', -0.1, f'{BAND}.properties.food.base'),
        (f'{BAND}.properties.food.seasons.winter.times', -1.0, f'{BAND}.properties.food.seasons.winter.times'),
        (f'{BAND}.properties.food.recovery', {'days': 0}, f'{BAND}.properties.food'),
        ('biomes.forest.colour', 'green', 'biomes.forest.colour'),
        ('biomes.forest.colour', '#06400', 'biomes.forest.colour'),
        ('planet.sea', 1.5, 'planet.sea'),
        ('planet.window.latitude', {'min': 0.6, 'max': 0.3}, 'planet.window.latitude'),
    ],
)
def test_value_out_of_its_range_is_refused(path: str, value: object, where: str) -> None:
    assert refused({path: value})['path'] == where


def test_river_effects_name_properties_of_their_era() -> None:
    assert refused({'planet.rivers.effects.band': {'shade': {'plus': 0.1}}}) == {
        'path': 'planet.rivers.effects.band',
        'found': 'shade',
        'expected': 'one of water, food, threat, passability, stone, wood',
    }
    assert refused({'planet.rivers.effects': {'alpha': {}}})['path'] == 'planet.rivers.effects'


def test_belts_of_moisture_run_from_the_equator_to_the_pole() -> None:
    belts = [{'latitude': 0.5, 'wet': 1.0}, {'latitude': 0.2, 'wet': 0.0}]

    assert str(refused({'planet.moisture.belts': belts})['path']).startswith('planet.moisture')
    assert str(refused({'planet.moisture.belts': []})['path']).startswith('planet.moisture')


def test_need_names_a_biome_that_exists() -> None:
    values = refused({'planet.window.needs.biomes': {'alpha': 0.1}})

    assert (values['path'], values['found']) == ('planet.window.needs.biomes', 'alpha')


@pytest.mark.parametrize(
    ('overrides', 'path'),
    [
        ({'eras.band.cell_km': 7}, 'eras.band.cell_km'),
        ({'planet.circumference_km': 40010}, 'eras.band.cell_km'),
        ({'planet.skeleton_km': 150}, 'planet.skeleton_km'),
        ({**TINY, 'planet.circumference_km': 16}, 'planet.circumference_km'),
        ({'planet.window.width': 4001}, 'planet.window.width'),
        ({'planet.window.height': 2001}, 'planet.window.height'),
        ({'planet.window.x': 0}, 'planet.window'),
        ({'planet.window.x': 3489, 'planet.window.y': 0}, 'planet.window.x'),
        ({'planet.window.x': 0, 'planet.window.y': 1745}, 'planet.window.y'),
    ],
)
def test_planet_and_window_that_do_not_add_up_are_refused(overrides: dict[str, object], path: str) -> None:
    assert refused(overrides)['path'] == path


def test_small_planet_and_a_window_put_by_hand_are_taken() -> None:
    small = {'planet.circumference_km': 4000, 'planet.window.width': 32, 'planet.window.height': 16}
    params = load_params(overrides={**small, 'planet.window.x': 368, 'planet.window.y': 184})

    assert (params.planet.window.x, params.planet.window.y) == (368, 184)
