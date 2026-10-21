from typing import Any

import pytest

from dominion_theory.content import load_params
from dominion_theory.core.errors import DominionError

WINTERING = {'learned': {'counter': 'winters', 'at_least': 1}, 'opens': {'proposals': ['winter_camp']}}


def refused(skill: dict[str, Any], name: str = 'wintering') -> dict[str, object]:
    with pytest.raises(DominionError) as raised:
        load_params(overrides={f'skills.{name}': skill})

    assert raised.value.key == 'error-params-invalid'
    return raised.value.values


def test_the_skills_of_the_band_era_are_those_of_their_document() -> None:
    skills = load_params().skills

    assert list(skills) == [
        'orientation',
        'wintering',
        'stone_tools',
        'sticks',
        'litters',
        'herbs',
        'spears',
        'waterskins',
        'drying',
        'midwifery',
    ]
    assert skills['stone_tools'].learned.biomes == ('hills', 'mountain', 'outcrops')
    assert (skills['stone_tools'].opens.gathers, skills['sticks'].opens.gathers) == (('stones',), ('sticks',))
    assert skills['sticks'].learned.biome == 'forest'
    assert skills['orientation'].opens.proposals == ('go_place',)
    assert [held.counter for held in skills['orientation'].learned.any] == ['seen', 'marched']
    assert skills['wintering'].learned.at_least == 1
    assert (skills['litters'].needs, skills['litters'].opens.makes) == (('sticks', 'herbs'), ('litters',))
    assert skills['herbs'].opens.gathers == ('herbs', 'cords')
    assert [held.at_least for held in skills['herbs'].learned.any] == [40, 40, 15]
    spears = skills['spears']
    assert (spears.needs, spears.learned.holds) == (
        ('stone_tools', 'sticks', 'herbs'),
        {'sticks': 1.0, 'stones': 1.0, 'cords': 1.0},
    )
    assert (spears.opens.makes, spears.opens.roles) == (('spears', 'clothes'), ('hunter',))
    drying = skills['drying']
    assert [(held.knows, held.counter, held.season, held.at_least) for held in drying.learned.all] == [
        (('herbs',), None, None, None),
        ((), 'foraged_in', 'summer', 15.0),
    ]
    assert drying.opens.makes == ('dried',)
    waterskins = skills['waterskins']
    assert (waterskins.needs, waterskins.learned.holds, waterskins.opens.makes) == (
        ('spears', 'herbs'),
        {'hides': 1.0, 'cords': 1.0},
        ('waterskins',),
    )


def test_a_skill_needs_skills_that_exist_and_never_itself() -> None:
    assert refused({**WINTERING, 'needs': ['alpha']})['path'] == 'skills.wintering.needs'
    assert refused({**WINTERING, 'needs': ['wintering']}) == {
        'path': 'skills.wintering.needs',
        'found': 'wintering',
        'expected': 'skills that do not need themselves through others',
    }


def test_two_skills_that_need_each_other_are_refused() -> None:
    with pytest.raises(DominionError) as raised:
        load_params(
            overrides={
                'skills.wintering': {**WINTERING, 'needs': ['orientation']},
                'skills.orientation': {**WINTERING, 'needs': ['wintering']},
            }
        )

    assert raised.value.values['expected'] == 'skills that do not need themselves through others'


@pytest.mark.parametrize(
    ('learned', 'path'),
    [
        ({'counter': 'alpha', 'at_least': 1}, 'skills.wintering.learned.counter'),
        ({'counter': 'winters', 'biome': 'forest', 'at_least': 1}, 'skills.wintering.learned.biome'),
        ({'counter': 'days_in', 'at_least': 1}, 'skills.wintering.learned.biome'),
        ({'counter': 'days_in', 'biome': 'alpha', 'at_least': 1}, 'skills.wintering.learned.biome'),
        ({'counter': 'days_in', 'biomes': ['new', 'forest'], 'at_least': 1}, 'skills.wintering.learned.biome'),
        ({'holds': {'alpha': 1}}, 'skills.wintering.learned.holds'),
        ({'any': [{'counter': 'beta', 'at_least': 1}]}, 'skills.wintering.learned.counter'),
    ],
)
def test_a_condition_names_known_counters_biomes_and_resources(learned: dict[str, Any], path: str) -> None:
    assert refused({**WINTERING, 'learned': learned})['path'] == path


@pytest.mark.parametrize(
    'learned',
    [
        {'counter': 'winters'},
        {'counter': 'winters', 'at_least': 1, 'holds': {'water': 1}},
        {'holds': {'water': 1}, 'at_least': 1},
        {'counter': 'days_in', 'biome': 'forest', 'biomes': ['grass'], 'at_least': 1},
        {},
    ],
)
def test_a_condition_is_one_of_four_kinds(learned: dict[str, Any]) -> None:
    assert str(refused({**WINTERING, 'learned': learned})['path']).startswith('skills.wintering.learned')


@pytest.mark.parametrize(
    ('opens', 'path'),
    [
        ({'proposals': ['alpha']}, 'skills.wintering.opens.proposals'),
        ({'gathers': ['alpha']}, 'skills.wintering.opens.gathers'),
        ({'makes': ['alpha']}, 'skills.wintering.opens.makes'),
        ({'roles': ['alpha']}, 'skills.wintering.opens.roles'),
    ],
)
def test_a_skill_opens_only_what_exists(opens: dict[str, Any], path: str) -> None:
    assert refused({**WINTERING, 'opens': opens})['path'] == path


def test_a_skill_of_every_kind_of_condition_is_read() -> None:
    skill = {
        'needs': ['orientation'],
        'learned': {
            'all': [
                {'counter': 'days_in', 'biomes': ['grass', 'floodplain'], 'at_least': 90},
                {'any': [{'counter': 'walked', 'biome': 'new', 'at_least': 8}, {'holds': {'water': 1}}]},
            ]
        },
        'opens': {'gathers': ['forage'], 'makes': ['water'], 'roles': ['nanny']},
    }

    read = load_params(overrides={'skills.wintering': skill}).skills['wintering']

    assert read.needs == ('orientation',)
    assert [held.counter for held in read.learned.walk()] == [None, 'days_in', None, 'walked', None]
