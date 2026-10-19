import pytest

from dominion_theory.content import ACTIONS, Duration, Params, load_params
from dominion_theory.core.errors import DominionError

BAND = 'units.band'
KINDS = 'encounters.kinds'
STAGES = 'units.band.people.stages'
RESOURCES = 'one of water, forage, meat, stones, sticks, herbs, cords, litters, spears, hides, clothes, waterskins'


def refused(overrides: dict[str, object]) -> dict[str, object]:
    with pytest.raises(DominionError) as raised:
        load_params(overrides=overrides)

    assert raised.value.key == 'error-params-invalid'
    return raised.value.values


def test_resources_are_those_of_their_documents() -> None:
    resources = load_params().resources

    assert {
        name: (held.kind, held.property, held.weight_kg, held.spoils and held.spoils.model_dump(), held.wears)
        for name, held in resources.items()
    } == {
        'water': ('water', 'water', 1.0, {'days': 5}, {}),
        'forage': ('food', 'food', 1.0, {'days': 3}, {}),
        'stones': ('goods', 'stone', 0.5, None, {'eaten': 300}),
        'sticks': ('goods', 'wood', 1.0, {'years': 1}, {'nights': 400, 'attacks': 1}),
        'herbs': ('goods', 'plants', 0.1, {'months': 2}, {'cures': 1}),
        'cords': ('goods', 'plants', 0.1, {'months': 6}, {}),
        'litters': ('goods', None, 4.0, None, {'pulled': 70}),
        'meat': ('food', None, 1.0, {'days': 2}, {}),
        'spears': ('goods', None, 1.5, None, {'hunts': 80}),
        'hides': ('goods', None, 2.0, {'months': 12}, {}),
        'clothes': ('goods', None, 2.0, {'months': 12}, {}),
        'waterskins': ('goods', None, 0.5, {'months': 6}, {}),
    }


def test_band_is_the_one_of_its_document() -> None:
    params = load_params()
    band = params.units.band

    assert band is params.units['band']
    assert (band.start.population, band.start.stores) == (15, {'water': 15.0, 'forage': 15.0})
    assert (band.start.biomes, band.start.stage) == (('grass', 'forest', 'floodplain'), 'adult')
    assert band.start.oldest == Duration(years=12)
    assert band.population.least == 5
    assert band.population.wellbeing.model_dump() == {'food': 1.0, 'water': 1.0, 'safety': 1.0, 'rest': 1.0}
    assert (band.carry_kg, band.gathering, band.consumption_per_day) == (
        6.0,
        {'forage': 3.0, 'water': 4.0, 'stones': 0.5, 'sticks': 1.0, 'herbs': 0.2, 'cords': 0.3},
        {'forage': 1.0, 'water': 1.0},
    )
    assert band.threat.model_dump() == {'camp': 1.0, 'march': 1.0}
    assert band.carry_water_kg == 0.0
    assert (band.speed.base, band.speed.slowdown, band.speed.slowest) == (1.2, 0.03, 0.3)
    assert band.fatigue.model_dump() == {
        'move': 0.3,
        'roam': 0.15,
        'gather': 0.1,
        'camp': -0.3,
        'build': 0.15,
        'slows': 0.5,
    }
    assert band.roaming.model_dump() == {'speed': 0.75, 'share': 0.5, 'hunger': 0.8}
    assert band.people.weakened.model_dump() == {'pace': 0.6, 'gathers': 0.6}
    assert {name: role.model_dump() for name, role in band.people.roles.items()} == {
        'gatherer': {'gathers': 1.0, 'cares': None, 'share': None, 'needs': None, 'gives': ()},
        'nanny': {'gathers': 0.5, 'cares': 5, 'share': None, 'needs': None, 'gives': ()},
        'hunter': {
            'gathers': 1.0,
            'cares': None,
            'share': 0.2,
            'needs': 'spears',
            'gives': tuple(
                {'to': 'band', 'path': path, 'plus': None, 'times': 0.8, 'sex': None, 'seasons': ()}
                for path in ('units.band.threat.camp', 'units.band.threat.march')
            ),
        },
    }
    assert band.people.sickness.model_dump(exclude_none=True) == {
        'lasts': {'days': 5},
        'pace': 0.7,
        'gathers': 0.5,
        'frailty': 2.0,
    }
    assert band.people.exposure.model_dump() == {'encounter': 1.0, 'frailty': 1.0}
    assert band.hunting.model_dump() == {'meat': 4.0, 'hides': 0.05}
    assert band.people.leaves.model_dump(exclude_none=True) == {'back': {'days': 1}}
    assert {name: stage.reserve.model_dump() for name, stage in band.people.stages.items()} == {
        'child': {'food': 1.0, 'water': 1.0, 'grows': True},
        'adult': {'food': 2.0, 'water': 2.0, 'grows': False},
        'elder': {'food': 1.5, 'water': 1.5, 'grows': False},
    }
    assert (band.states.tiredness.begins, band.states.tiredness.ends) == (0.8, 0.3)
    assert (band.sight, band.memory.model_dump()) == (2, {'days': 20})
    assert band.camp_parts == ('evening', 'night')
    assert band.making.per_part == 0.2
    assert band.shelter.model_dump() == {'encounter': 0.5, 'frailty': 0.5}
    assert band.winter_camp.model_dump() == {
        'offered': {'seasons': ('winter',), 'before': {'days': 5}},
        'build': {'days': 2},
        'reach': 1,
        'afar': 1.0,
        'kept': 0.2,
        'threat': 0.5,
        'spoil': 0.5,
        'consumption': 0.8,
        'rest': 1.5,
    }
    injury = band.people.injury
    assert (injury.per_day, injury.heal_in_camp) == (0.002, 2.0)
    assert injury.drawn == {'light': 0.5, 'medium': 0.3, 'heavy': 0.2}
    assert {name: held.model_dump() for name, held in injury.severities.items()} == {
        'light': {'days': 10, 'pace': 0.8, 'gathers': 0.7, 'treated': 0.5},
        'medium': {'days': 15, 'pace': 0.6, 'gathers': 0.4, 'treated': 1.0},
        'heavy': {'days': 20, 'pace': 0.4, 'gathers': 0.2, 'treated': 1.0},
    }
    weights = band.decisions.weights
    assert (weights.hunger, weights.goods, weights.safety, weights.move) == (1.5, 0.4, 2.0, 3.0)
    assert {name: held.model_dump() for name, held in band.decisions.levels.items()} == {
        'sated': {'days': 2.0, 'need': 0.1},
        'fed': {'days': 1.0, 'need': 0.4},
        'hungry': {'days': 0.0, 'need': 0.8},
    }


def test_unknown_unit_is_a_key_error() -> None:
    with pytest.raises(KeyError):
        load_params().units['tribe']


def test_era_holds_what_a_cell_gives_and_how_winter_slows_it() -> None:
    band = load_params().eras.band

    assert band.capacity == {'food': 100.0, 'water': 2000.0, 'stone': 50.0, 'wood': 100.0, 'plants': 50.0, 'game': 60.0}
    assert band.recovery == {'food': {'winter': 0.25}, 'plants': {'winter': 0.25}}


def test_council_is_the_one_of_its_document() -> None:
    council = load_params().council

    assert (council.part, council.spread, council.voice.share, council.voice.least) == ('evening', 0.2, 0.5, 2.0)
    assert council.judgement.slack == 0.1
    assert council.status.model_dump() == {
        'start': 50.0,
        'abstained': -2.0,
        'outvoted': -1.0,
        'go_worked': 4.0,
        'go_failed': -6.0,
        'go_even': 0.0,
        'stay_worked': 3.0,
        'stay_failed': -6.0,
        'stay_even': 0.0,
        'camp_worked': 3.0,
        'camp_failed': -6.0,
        'camp_even': 0.0,
        'death': -5.0,
        'birth': 5.0,
    }


def test_encounters_are_those_of_their_document() -> None:
    encounters = load_params().encounters
    drowning, predator = encounters.kinds['drowning'], encounters.kinds['predator']

    assert (encounters.chance, encounters.actions) == (
        0.02,
        {'camp': 0.5, 'build': 1.0, 'gather': 1.0, 'roam': 1.2, 'move': 1.5},
    )
    assert set(encounters.actions) == set(ACTIONS)
    assert list(encounters.kinds) == ['predator', 'accident', 'drowning', 'poisoning']
    assert (predator.biomes, predator.rivers, predator.actions, predator.resources) == ((), False, (), ())
    assert (drowning.biomes, drowning.rivers, drowning.actions) == (('shallows',), True, ('move', 'roam', 'gather'))
    assert (drowning.loss.min, drowning.loss.max) == (0.05, 0.15)
    assert encounters.kinds['poisoning'].resources == ('water',)
    assert (encounters.kinds['accident'].wounds, predator.wounds) == ({'light': 0.2, 'medium': 0.4, 'heavy': 0.4}, {})


def test_shallows_are_a_shore_and_no_other_biome_is() -> None:
    biomes = load_params().biomes
    shallows = biomes['shallows'].eras['band']

    assert [name for name, biome in biomes.items() if biome.eras['band'].shore] == ['shallows']
    assert (shallows.properties['threat'].base, shallows.properties['passability'].base) == (0.6, 0.0)
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
        'expected': 'a property of the era band: water, food, threat, passability, stone, wood, plants, game',
    }


def test_resource_weighs_something_and_keeps_for_a_time() -> None:
    assert refused({'resources.water.weight_kg': 0.0})['path'] == 'resources.water.weight_kg'
    assert refused({'resources.water.spoils': {'days': 0}})['path'] == 'resources.water'


@pytest.mark.parametrize('section', ['gathering', 'consumption_per_day', 'start.stores'])
def test_band_names_only_resources_that_exist(section: str) -> None:
    assert refused({f'{BAND}.{section}': {'stone': 1.0}}) == {
        'path': f'{BAND}.{section}',
        'found': 'stone',
        'expected': RESOURCES,
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


@pytest.mark.parametrize('path', [f'{BAND}.people.injury.drawn', f'{KINDS}.accident.wounds'])
def test_wounds_are_drawn_from_severities_that_exist_by_some_weight(path: str) -> None:
    tree = load_params().tree()
    *above, last = path.split('.')
    node = tree
    for name in above:
        node = node[name]
    node[last] = {'grave': 1.0}

    with pytest.raises(DominionError) as raised:
        Params.model_validate(tree)

    assert raised.value.values == {'path': path, 'found': 'grave', 'expected': 'one of light, medium, heavy'}
    assert refused({f'{path}.{name}': 0.0 for name in ('light', 'medium', 'heavy')})['path'] == path


def test_one_role_cares_for_nobody() -> None:
    roles = {'gatherer': {'gathers': 1.0}, 'nanny': {'gathers': 0.0}}

    assert refused({f'{BAND}.people.roles': roles})['path'] == f'{BAND}.people.roles'


def test_a_role_needs_a_personal_good_and_lays_its_bonuses_on_the_band() -> None:
    roles = f'{BAND}.people.roles.hunter'
    member = [{'to': 'member', 'path': 'units.band.carry_kg', 'times': 2.0}]

    assert refused({f'{roles}.needs': 'sticks'})['path'] == f'{roles}.needs'
    assert refused({f'{roles}.gives': member})['path'] == f'{roles}.gives.to'
    assert refused({f'{roles}.gives': [{'to': 'band', 'path': 'units.band', 'times': 0.8}]})['path'] == (
        f'{roles}.gives.path'
    )


def test_the_last_stage_does_not_grow_its_reserve() -> None:
    assert refused({f'{STAGES}.elder.reserve.grows': True})['path'] == f'{STAGES}.elder.reserve.grows'


def test_tiredness_ends_below_where_it_begins() -> None:
    assert refused({f'{BAND}.states.tiredness.ends': 0.8})['path'] == f'{BAND}.states.tiredness'


@pytest.mark.parametrize(
    'path',
    [f'{BAND}.people.weakened.gathers', 'encounters.chance', f'{BAND}.shelter.encounter'],
)
def test_share_lies_between_nothing_and_one(path: str) -> None:
    assert refused({path: 1.5})['path'] == path


def test_camp_parts_are_parts_of_the_day() -> None:
    assert refused({f'{BAND}.camp_parts': ['dusk']}) == {
        'path': f'{BAND}.camp_parts',
        'found': 'dusk',
        'expected': 'one of morning, midday, afternoon, evening, night',
    }


@pytest.mark.parametrize(
    ('overrides', 'path'),
    [
        ({f'{BAND}.decisions.levels.hungry.days': 1}, f'{BAND}.decisions'),
        ({f'{BAND}.decisions.levels.hungry.need': 1.5}, f'{BAND}.decisions.levels.hungry.need'),
        (
            {f'{BAND}.population.wellbeing': {'food': 0.0, 'water': 0.0, 'safety': 0.0, 'rest': 0.0}},
            f'{BAND}.population.wellbeing',
        ),
        ({'council.spread': 0.0}, 'council.spread'),
    ],
)
def test_levels_growth_and_spread_are_checked(overrides: dict[str, object], path: str) -> None:
    assert refused(overrides)['path'] == path


def test_people_are_those_of_the_band_document() -> None:
    people = load_params().units.band.people

    told = {
        name: (stage.until, stage.settles, stage.gathers, stage.conceives, stage.votes)
        for name, stage in people.stages.items()
    }

    assert told == {
        'child': (Duration(years=4), Duration(months=7), 0.0, False, False),
        'adult': (Duration(years=17), None, 1.0, True, True),
        'elder': (None, None, 0.0, False, True),
    }
    assert (people.age.per_year, people.injury.per_day, people.birth.child_survives) == (0.15, 0.002, 0.5)
    assert load_params().council.blamed == ('hunger', 'thirst', 'encounter')


@pytest.mark.parametrize(
    ('overrides', 'path', 'expected'),
    [
        ({f'{STAGES}.adult.until': None}, f'{STAGES}.adult.until', 'an age for every stage but the last'),
        ({f'{STAGES}.adult.until': {'years': 3}}, f'{STAGES}.adult.until', 'an age above the stage before'),
        ({f'{STAGES}.adult.conceives': False}, STAGES, 'a stage that conceives'),
        ({f'{BAND}.start.stage': 'elder'}, f'{BAND}.start.stage', 'one of child, adult'),
        ({f'{BAND}.start.oldest': {'years': 4}}, f'{BAND}.start.oldest', 'an age above the start of the start stage'),
        ({f'{BAND}.people.birth.pause.min': {'months': 3}}, f'{BAND}.people.birth.pause', 'min not above max'),
        ({'council.blamed': ['boredom']}, 'council.blamed', 'one of hunger, thirst, encounter, age, frailty, birth'),
    ],
)
def test_people_are_checked(overrides: dict[str, object], path: str, expected: str) -> None:
    found = refused(overrides)

    assert (found['path'], found['expected']) == (path, expected)


@pytest.mark.parametrize(('stage', 'settles'), [('elder', {'months': 7}), ('child', {'parts': 2})])
def test_a_stage_settles_over_a_day_or_more_and_never_the_last(stage: str, settles: dict[str, int]) -> None:
    tree = load_params().tree()
    tree['units']['band']['people']['stages'][stage]['settles'] = settles

    with pytest.raises(DominionError) as raised:
        Params.model_validate(tree)

    found = raised.value.values
    assert found['path'] == f'{STAGES}.{stage}.settles'
    assert found['expected'] == 'a span above 0 on a stage before the last'


def test_voice_of_the_player_is_never_an_ordinary_one() -> None:
    assert refused({'council.voice.least': 1.0})['path'] == 'council.voice.least'


def test_the_council_sits_in_a_part_of_the_day() -> None:
    assert refused({'council.part': 'dusk'}) == {
        'path': 'council.part',
        'found': 'dusk',
        'expected': 'one of morning, midday, afternoon, evening, night',
    }
    assert load_params(overrides={'council.part': 'evening'}).council.part == 'evening'


def test_status_starts_within_its_scale() -> None:
    assert refused({'council.status.start': 101})['path'] == 'council.status.start'


@pytest.mark.parametrize(
    ('section', 'value', 'expected'),
    [
        ('biomes', ['alpha'], None),
        ('actions', ['swim'], 'one of move, roam, gather, camp, build'),
        ('resources', ['stone'], RESOURCES),
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
        'expected': 'one of move, roam, gather, camp, build',
    }


@pytest.mark.parametrize('section', ['capacity', 'recovery'])
def test_era_names_its_own_properties(section: str) -> None:
    value: dict[str, object] = {'soil': 1.0} if section == 'capacity' else {'soil': {'winter': 0.5}}

    assert refused({f'eras.band.{section}': value}) == {
        'path': f'eras.band.{section}',
        'found': 'soil',
        'expected': 'one of water, food, threat, passability, stone, wood, plants, game',
    }


def test_a_winter_camp_is_offered_in_seasons_of_the_year_and_takes_some_time_to_build() -> None:
    assert refused({f'{BAND}.winter_camp.offered.seasons': ['monsoon']}) == {
        'path': f'{BAND}.winter_camp.offered.seasons',
        'found': 'monsoon',
        'expected': 'one of spring, summer, autumn, winter',
    }
    assert refused({f'{BAND}.winter_camp.build': {'days': 0}})['path'] == f'{BAND}.winter_camp'


def test_recovery_names_a_season_of_the_year() -> None:
    assert refused({'eras.band.recovery.food': {'monsoon': 0.5}}) == {
        'path': 'eras.band.recovery.food',
        'found': 'monsoon',
        'expected': 'one of spring, summer, autumn, winter',
    }


def test_goods_spoil_or_wear_by_their_uses_and_draw_a_quality_where_their_property_is_given() -> None:
    stones = load_params().resources['stones']

    assert stones.held == 'common'
    assert stones.keep is not None and stones.keep.model_dump() == {'per': 'head', 'amount': 0.3}
    assert stones.quality['mountain'].model_dump() == {'min': 0.8, 'max': 1.0}
    assert refused({'resources.stones.wears': {'walked': 1}})['path'] == 'resources.stones'
    assert refused({'resources.stones.wears': {}})['path'] == 'resources.stones'
    assert refused({'resources.sticks.spoils': {'days': 0}})['path'] == 'resources.sticks'
    worn = {'kind': 'food', 'property': 'food', 'weight_kg': 1.0, 'spoils': {'days': 3}, 'wears': {'eaten': 1}}
    assert refused({'resources.forage': worn})['path'] == 'resources.forage'
    assert refused({'resources.stones.kind': 'alpha'})['path'] == 'resources.stones'
    assert refused({'resources.stones.quality.hills.max': 1.5})['path'] == 'resources.stones.quality.hills.max'
    assert refused({'resources.stones.quality': {'forest': {'min': 0.5, 'max': 0.6}}}) == {
        'path': 'resources.stones.quality',
        'found': 'forest',
        'expected': 'a biome that gives the property stone',
    }


def test_a_keep_counts_members_of_a_kind_and_a_recipe_names_other_resources() -> None:
    assert refused({'resources.sticks.keep.per': 'alpha'})['path'] == 'resources.sticks.keep.per'
    assert refused({'resources.sticks.made': {'sticks': 1.0}})['path'] == 'resources.sticks.made'
    assert refused({'resources.sticks.made': {'alpha': 1.0}})['path'] == 'resources.sticks.made'


@pytest.mark.parametrize(
    ('bonus', 'path'),
    [
        ({'to': 'band', 'path': 'units.band.speed', 'times': 0.8}, 'resources.sticks.gives.path'),
        ({'to': 'band', 'path': 'units.band.alpha', 'times': 0.8}, 'resources.sticks.gives.path'),
        ({'to': 'band', 'path': 'units.band.carry_kg', 'plus': {'days': 1}}, 'resources.sticks.gives.path'),
        ({'to': 'band', 'path': 'units.band.memory', 'plus': 1.0}, 'resources.sticks.gives.path'),
        ({'to': 'member', 'path': 'units.band.carry_kg', 'times': 2.0}, 'resources.sticks.gives.to'),
        ({'to': 'alpha', 'path': 'units.band.carry_kg', 'times': 2.0}, 'resources.sticks.gives.to'),
        ({'to': 'band', 'path': 'units.band.carry_kg', 'times': 2.0, 'sex': 'alpha'}, 'resources.sticks.gives.sex'),
        (
            {'to': 'band', 'path': 'units.band.carry_kg', 'times': 2.0, 'seasons': ['alpha']},
            'resources.sticks.gives.seasons',
        ),
    ],
)
def test_a_bonus_lies_on_the_band_or_a_member_over_a_number_of_the_tree(bonus: dict[str, object], path: str) -> None:
    assert refused({'resources.sticks.gives': [bonus]})['path'] == path


def test_a_bonus_of_a_span_is_a_span() -> None:
    gives = load_params().resources['stones'].gives

    assert [(bonus.path, bonus.model_dump(exclude_none=True)) for bonus in gives][1] == (
        'units.band.people.age.begins',
        {'to': 'band', 'path': 'units.band.people.age.begins', 'plus': {'years': 1}, 'seasons': ()},
    )
