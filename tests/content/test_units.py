import pytest

from dominion_theory.content import ACTIONS, Duration, Params, load_params
from dominion_theory.core.errors import DominionError

BAND = 'units.band'
KINDS = 'encounters.kinds'


def refused(overrides: dict[str, object]) -> dict[str, object]:
    with pytest.raises(DominionError) as raised:
        load_params(overrides=overrides)

    assert raised.value.key == 'error-params-invalid'
    return raised.value.values


def test_resources_are_those_of_their_documents() -> None:
    resources = load_params().resources

    assert {name: (held.property, held.weight_kg, held.spoils.model_dump()) for name, held in resources.items()} == {
        'water': ('water', 1.0, {'days': 5}),
        'forage': ('food', 1.0, {'days': 3}),
    }


def test_band_is_the_one_of_its_document() -> None:
    params = load_params()
    band = params.units.band

    assert band is params.units['band']
    assert (band.start.population, band.start.stores) == (15, {'water': 15.0, 'forage': 15.0})
    assert band.start.biomes == ('grass', 'forest', 'floodplain')
    assert (band.population.least, band.population.growth_per_year, band.population.rest_growth) == (5, 0.3, 3.0)
    assert (band.carry_kg, band.gathering, band.consumption_per_day) == (
        6.0,
        {'forage': 3.0, 'water': 4.0},
        {'forage': 1.0, 'water': 1.0},
    )
    assert (band.speed.base, band.speed.slowdown, band.speed.slowest) == (1.2, 0.03, 0.3)
    assert (band.fatigue.move, band.fatigue.gather, band.fatigue.camp) == (0.15, 0.08, -0.35)
    assert (band.states.short, band.states.starvation.loss_per_day, band.states.thirst.loss_per_day) == (
        0.75,
        0.05,
        0.15,
    )
    assert (band.states.tiredness.begins, band.states.tiredness.ends, band.states.tiredness.slows) == (0.8, 0.3, 0.5)
    assert (band.sight, band.memory.model_dump()) == (2, {'days': 20})
    assert band.decisions.night_parts == ('evening', 'night')
    assert (band.decisions.weights.hunger, band.decisions.weights.move) == (1.5, 3.0)
    assert band.decisions.comfort.model_dump() == {'days': 3}


def test_unknown_unit_is_a_key_error() -> None:
    with pytest.raises(KeyError):
        load_params().units['tribe']


def test_era_holds_what_a_cell_gives_and_how_winter_slows_it() -> None:
    band = load_params().eras.band

    assert band.capacity == {'food': 200.0, 'water': 2000.0}
    assert band.recovery == {'food': {'winter': 0.25}}


def test_council_is_the_one_of_its_document() -> None:
    council = load_params().council

    assert (council.min_gap.model_dump(), council.voice.share, council.voice.least) == ({'days': 2}, 0.5, 2.0)
    assert council.intent.model_dump() == {'move': {'days': 1}, 'rest': {'days': 2}, 'stay_and_gather': {'days': 2}}
    assert (council.judgement.tolerance, council.judgement.disaster) == (0.25, 0.2)
    assert council.status.model_dump() == {
        'start': 50.0,
        'declined': -2.0,
        'move_worked': 4.0,
        'move_failed': -6.0,
        'move_disaster': -20.0,
        'rest': 2.0,
        'stay_worked': 3.0,
        'stay_failed': -6.0,
        'stay_disaster': -20.0,
    }


def test_encounters_are_those_of_their_document() -> None:
    encounters = load_params().encounters
    drowning, predator = encounters.kinds['drowning'], encounters.kinds['predator']

    assert (encounters.chance, encounters.actions) == (0.02, {'camp': 0.5, 'gather': 1.0, 'move': 1.5})
    assert set(encounters.actions) == set(ACTIONS)
    assert list(encounters.kinds) == ['predator', 'accident', 'drowning', 'poisoning']
    assert (predator.biomes, predator.rivers, predator.actions, predator.resources) == ((), False, (), ())
    assert (drowning.biomes, drowning.rivers, drowning.actions) == (('shallows',), True, ('move', 'gather'))
    assert (drowning.loss.min, drowning.loss.max) == (0.05, 0.15)
    assert encounters.kinds['poisoning'].resources == ('water',)


def test_shallows_are_a_shore_and_no_other_biome_is() -> None:
    biomes = load_params().biomes
    shallows = biomes['shallows'].eras['band']

    assert [name for name, biome in biomes.items() if biome.eras['band'].shore] == ['shallows']
    assert (shallows.properties['threat'].base, shallows.properties['passability'].base) == (0.6, 0.3)
    assert shallows.resources == ('water', 'forage')


def test_seasons_change_water_and_movement_where_the_biome_says() -> None:
    biomes = load_params().biomes
    grass, forest, desert = (biomes[name].eras['band'].properties for name in ('grass', 'forest', 'desert'))

    assert {season: held.amount for season, held in grass['water'].seasons.items()} == {
        'spring': 1.2,
        'summer': 0.7,
        'winter': 0.8,
    }
    assert {season: held.amount for season, held in grass['passability'].seasons.items()} == {
        'spring': 0.8,
        'winter': 0.7,
    }
    assert forest['water'].seasons == forest['passability'].seasons == {}
    assert desert['water'].seasons == desert['passability'].seasons == {}


@pytest.mark.parametrize(
    ('duration', 'parts'),
    [({'parts': 3}, 3), ({'days': 2}, 10), ({'months': 1}, 50), ({'years': 1}, 500)],
)
def test_duration_is_counted_in_parts_of_the_tree(duration: dict[str, int], parts: int) -> None:
    assert load_params().parts(Duration(**duration)) == parts


def test_tree_with_the_new_sections_validates_back() -> None:
    params = load_params()

    assert Params.model_validate(params.tree()).hash == params.hash


def test_resource_names_a_property_of_the_era() -> None:
    assert refused({'resources.forage.property': 'soil'}) == {
        'path': 'resources.forage.property',
        'found': 'soil',
        'expected': 'a property of the era band: water, food, threat, passability',
    }


def test_resource_weighs_something_and_keeps_for_a_time() -> None:
    assert refused({'resources.water.weight_kg': 0.0})['path'] == 'resources.water.weight_kg'
    assert refused({'resources.water.spoils': {'days': 0}})['path'] == 'resources.water'


@pytest.mark.parametrize('section', ['gathering', 'consumption_per_day', 'start.stores'])
def test_band_names_only_resources_that_exist(section: str) -> None:
    assert refused({f'{BAND}.{section}': {'stone': 1.0}}) == {
        'path': f'{BAND}.{section}',
        'found': 'stone',
        'expected': 'one of water, forage',
    }


def test_start_population_is_not_below_the_least() -> None:
    assert refused({f'{BAND}.start.population': 4}) == {
        'path': f'{BAND}.start.population',
        'found': 4,
        'expected': 'at least the 5 people of population.least',
    }


def test_start_stores_fit_what_the_band_carries() -> None:
    assert refused({f'{BAND}.start.stores.water': 80.0}) == {
        'path': f'{BAND}.start.stores',
        'found': {'water': 80.0, 'forage': 15.0},
        'expected': 'up to the 90 kg the band carries',
    }


def test_start_biome_exists_and_can_be_entered() -> None:
    assert refused({f'{BAND}.start.biomes': ['alpha']})['path'] == f'{BAND}.start.biomes'
    assert refused({f'{BAND}.start.biomes': ['water']}) == {
        'path': f'{BAND}.start.biomes',
        'found': 'water',
        'expected': 'a biome that can be entered',
    }
    assert refused({f'{BAND}.start.biomes': []})['path'] == f'{BAND}.start.biomes'


def test_tiredness_ends_below_where_it_begins() -> None:
    assert refused({f'{BAND}.states.tiredness.ends': 0.8})['path'] == f'{BAND}.states.tiredness'


@pytest.mark.parametrize(
    'path',
    [f'{BAND}.states.short', f'{BAND}.states.thirst.loss_per_day', 'encounters.chance', 'council.judgement.disaster'],
)
def test_share_lies_between_nothing_and_one(path: str) -> None:
    assert refused({path: 1.5})['path'] == path


def test_night_parts_are_parts_of_the_day() -> None:
    assert refused({f'{BAND}.decisions.night_parts': ['dusk']}) == {
        'path': f'{BAND}.decisions.night_parts',
        'found': 'dusk',
        'expected': 'one of morning, midday, afternoon, evening, night',
    }


def test_voice_of_the_player_is_never_an_ordinary_one() -> None:
    assert refused({'council.voice.least': 1.0})['path'] == 'council.voice.least'


def test_move_is_not_judged_before_its_intent_ends() -> None:
    assert refused({'council.judgement.move_after': {'parts': 4}}) == {
        'path': 'council.judgement.move_after',
        'found': {'parts': 4},
        'expected': 'not shorter than council.intent.move',
    }
    assert (
        load_params(overrides={'council.judgement.move_after': {'parts': 5}}).council.judgement.move_after.amount == 5
    )


def test_status_starts_within_its_scale() -> None:
    assert refused({'council.status.start': 101})['path'] == 'council.status.start'


@pytest.mark.parametrize(
    ('section', 'value', 'expected'),
    [
        ('biomes', ['alpha'], None),
        ('actions', ['swim'], 'one of move, gather, camp'),
        ('resources', ['stone'], 'one of water, forage'),
    ],
)
def test_encounter_names_what_exists(section: str, value: list[str], expected: str | None) -> None:
    values = refused({f'{KINDS}.predator': {'weight': 1.0, 'loss': {'min': 0.0, 'max': 0.1}, section: value}})

    assert (values['path'], values['found']) == (f'{KINDS}.predator.{section}', value[0])
    assert expected is None or values['expected'] == expected


def test_encounter_loss_is_ordered_and_its_weight_is_positive() -> None:
    assert refused({f'{KINDS}.predator.loss': {'min': 0.2, 'max': 0.1}})['path'] == f'{KINDS}.predator.loss'
    assert refused({f'{KINDS}.predator.weight': 0})['path'] == f'{KINDS}.predator.weight'


def test_factor_of_an_action_names_an_action() -> None:
    assert refused({'encounters.actions': {'swim': 1.0}}) == {
        'path': 'encounters.actions',
        'found': 'swim',
        'expected': 'one of move, gather, camp',
    }


@pytest.mark.parametrize('section', ['capacity', 'recovery'])
def test_era_names_its_own_properties(section: str) -> None:
    value: dict[str, object] = {'soil': 1.0} if section == 'capacity' else {'soil': {'winter': 0.5}}

    assert refused({f'eras.band.{section}': value}) == {
        'path': f'eras.band.{section}',
        'found': 'soil',
        'expected': 'one of water, food, threat, passability',
    }


def test_recovery_names_a_season_of_the_year() -> None:
    assert refused({'eras.band.recovery.food': {'monsoon': 0.5}}) == {
        'path': 'eras.band.recovery.food',
        'found': 'monsoon',
        'expected': 'one of spring, summer, autumn, winter',
    }


def test_shore_can_be_entered() -> None:
    assert refused({'biomes.shallows.eras.band.properties.passability.base': 0.0}) == {
        'path': 'biomes.shallows.eras.band.properties.passability.base',
        'found': 0.0,
        'expected': 'a shore that can be entered',
    }
