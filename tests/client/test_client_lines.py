from typing import Any

import pytest

from dominion_theory.client import band_words, follow, line, parts, words
from dominion_theory.client.lines import Look
from dominion_theory.engine import EVENTS

DATE = {'year': 1, 'month': 3, 'day': 1, 'part': 'morning', 'season': 'summer'}
SEASON = {'key': 'season-started', 'values': {'year': 1, 'season': 'summer'}}
MONTH = {'key': 'month-started', 'values': {'year': 1, 'month': 3, 'season': 'summer'}}
BAND = {
    'id': 1,
    'kind': 'band',
    'place': {'scale': 0, 'x': 2301, 'y': 744},
    'population': 15,
    'stores': {'forage': 22.5, 'water': 30.0},
    'fatigue': 0.3,
    'states': [],
    'action': {'kind': 'camp'},
    'intent': None,
    'reason': None,
}
# One of every event the engine declares, with the values it carries.
SAMPLES: dict[str, dict[str, Any]] = {
    'command-accepted': {'id': 'c-1'},
    'command-refused': {'id': 'c-1', 'reason': 'refused-no-council'},
    'day-started': {'year': 1, 'month': 1, 'day': 2},
    'month-started': {'year': 1, 'month': 2, 'season': 'spring'},
    'season-started': {'year': 1, 'season': 'summer'},
    'year-started': {'year': 2, 'seasons': 4},
    'band-state-began': {'state': 'state-thirst'},
    'band-state-ended': {'state': 'state-starvation'},
    'people-lost': {'count': 2, 'cause': 'encounter'},
    'people-born': {'count': 1},
    'people-injured': {'count': 2},
    'band-died': {},
    'encounter': {'kind': 'encounter-predator', 'lost': 1},
    'council-opened': {'leader': 'proposal-stay-and-gather', 'occasion': 'occasion-hunger'},
    'council-agreed': {'leader': 'proposal-go-forest', 'occasion': 'occasion-arrived'},
    'council-followed': {'proposal': 'proposal-stay-and-gather'},
    'council-turned': {'proposal': 'proposal-go-forest', 'yes': 8.75, 'all': 17.75},
    'council-outvoted': {'proposal': 'proposal-go-through-grass', 'winner': 'proposal-stay-and-gather', 'status': 49.0},
    'council-abstained': {'status': 48.0},
    'proposal-worked': {'proposal': 'proposal-stay-and-gather', 'status': 53.0},
    'proposal-even': {'proposal': 'proposal-stay-and-gather', 'status': 53.0},
    'proposal-failed': {'proposal': 'proposal-go-unknown', 'status': 44.0},
    'intent-ended': {'proposal': 'proposal-go-hills'},
    'intent-arrived': {},
    'seat-blamed': {'lost': 3, 'status': 35.0},
    'seat-praised': {'born': 1, 'status': 55.0},
    'seat-banished': {},
    'skill-learned': {'skill': 'skill-orientation'},
    'goods-made': {'resource': 'litters', 'count': 2},
    'goods-spoiled': {'resource': 'sticks', 'count': 2},
    'goods-worn': {'resource': 'stones', 'count': 3},
}


def test_a_message_becomes_words_in_the_language() -> None:
    assert words(SEASON, 'en') == 'Year 1: summer has come.'
    assert words(SEASON, 'ru') == 'Год 1: наступило лето.'


def test_goods_made_spoiled_and_worn_are_told_with_their_count() -> None:
    made = {'key': 'goods-made', 'values': {'resource': 'litters', 'count': 2}}
    worn = {'key': 'goods-worn', 'values': {'resource': 'stones', 'count': 3}}
    spoiled = {'key': 'goods-spoiled', 'values': {'resource': 'sticks', 'count': 2}}

    assert words(made, 'en') == 'Made: litters 2.'
    assert words(made, 'ru') == 'Сделаны: волокуши 2.'

    assert words(worn, 'en') == 'Worn out: stones 3.'
    assert words(worn, 'ru') == 'Износились: камни 3.'
    assert words(spoiled, 'en') == 'Spoiled: sticks 2.'
    assert words(spoiled, 'ru') == 'Испортились: палки 2.'


def test_a_message_without_values_is_rendered() -> None:
    assert words({'key': 'error-request-unreadable'}, 'en') == 'The request cannot be read.'


def test_a_line_is_the_date_and_the_words_of_the_events_in_order() -> None:
    update = {'seq': 100, 'date': DATE, 'events': [MONTH, SEASON]}

    assert line(update, 'en') == (
        'day 1, month 3, year 1, summer: ' 'Month 3 of year 1 begins; the season is summer. Year 1: summer has come.'
    )
    assert line(update, 'ru') == (
        'день 1, месяц 3, год 1, лето: ' 'Начался месяц 3 года 1; время года — лето. Год 1: наступило лето.'
    )


def test_a_line_without_events_is_the_date_alone() -> None:
    update = {'seq': 101, 'date': {**DATE, 'part': 'midday'}, 'events': []}

    assert line(update, 'en') == 'day 1, month 3, year 1, summer'


@pytest.mark.parametrize(
    ('band', 'lang', 'said'),
    [
        (BAND, 'en', '15 people, forage 22.5, water 30, camps.'),
        (BAND, 'ru', '15 человек, подножный корм 22,5, вода 30, стоит лагерем.'),
        (
            {**BAND, 'population': 1, 'states': ['thirst'], 'action': {'kind': 'gather', 'shares': {'water': 1.0}}},
            'en',
            '1 person, forage 22.5, water 30, thirst, gathers water.',
        ),
        (
            {**BAND, 'population': 2, 'states': ['thirst'], 'action': {'kind': 'gather', 'shares': {'water': 1.0}}},
            'ru',
            '2 человека, подножный корм 22,5, вода 30, жажда, собирает воду.',
        ),
        (
            {**BAND, 'action': {'kind': 'move', 'towards': 'north-east'}},
            'en',
            '15 people, forage 22.5, water 30, walks north-east.',
        ),
        (
            {**BAND, 'action': {'kind': 'move', 'towards': 'north-east'}},
            'ru',
            '15 человек, подножный корм 22,5, вода 30, идёт на северо-восток.',
        ),
        (
            {**BAND, 'ages': {'child': 3, 'adult': 10, 'elder': 2}, 'pregnant': 1, 'injured': 0},
            'en',
            '15 people, 3 children, 10 adults, 2 elders, 1 with child, forage 22.5, water 30, camps.',
        ),
        (
            {**BAND, 'ages': {'child': 0, 'adult': 15, 'elder': 0}, 'pregnant': 0, 'injured': 2},
            'ru',
            '15 человек, раненых 2, подножный корм 22,5, вода 30, стоит лагерем.',
        ),
        (
            {**BAND, 'injured': 3, 'wounds': {'light': 2, 'medium': 0, 'heavy': 1}},
            'ru',
            '15 человек, раненых 3 (тяжело 1), подножный корм 22,5, вода 30, стоит лагерем.',
        ),
        (
            {**BAND, 'injured': 3, 'wounds': {'light': 2, 'medium': 0, 'heavy': 1}},
            'en',
            '15 people, 3 injured (1 badly), forage 22.5, water 30, camps.',
        ),
        (
            {**BAND, 'action': {'kind': 'gather', 'shares': {'water': 0.44, 'forage': 0.56}}},
            'en',
            '15 people, forage 22.5, water 30, gathers forage (56%) and water (44%).',
        ),
        (
            {**BAND, 'action': {'kind': 'gather', 'shares': {'water': 0.44, 'forage': 0.56}}},
            'ru',
            '15 человек, подножный корм 22,5, вода 30, собирает подножный корм (56%) и воду (44%).',
        ),
        (
            {**BAND, 'roles': {'gatherer': 13, 'nanny': 2}},
            'ru',
            '15 человек, 2 няньки, подножный корм 22,5, вода 30, стоит лагерем.',
        ),
        (
            {**BAND, 'camp': {'x': 2301, 'y': 744, 'built': 0.5}, 'action': {'kind': 'build'}},
            'en',
            '15 people, forage 22.5, water 30, builds a winter camp.',
        ),
        (
            {**BAND, 'camp': {'x': 2301, 'y': 744, 'built': 1.0}},
            'ru',
            '15 человек, в зимнем лагере, подножный корм 22,5, вода 30, стоит лагерем.',
        ),
        (
            {**BAND, 'lore': ['orientation', 'wintering']},
            'en',
            '15 people, knows how to find its way, to winter, forage 22.5, water 30, camps.',
        ),
        (
            {**BAND, 'lore': ['wintering']},
            'ru',
            '15 человек, умеет зимовать, подножный корм 22,5, вода 30, стоит лагерем.',
        ),
        (
            {**BAND, 'stores': {'forage': 22.5, 'water': 30.0, 'stones': 4.0}, 'goods': {'stones': 4.0, 'sticks': 1.5}},
            'en',
            '15 people, forage 22.5, water 30, stones 4, sticks 1.5, camps.',
        ),
        (
            {**BAND, 'lore': ['stone_tools', 'sticks'], 'goods': {'stones': 4.0}},
            'ru',
            '15 человек, умеет обрабатывать камень, заготавливать палки, подножный корм 22,5, вода 30, камни 4, '
            'стоит лагерем.',
        ),
    ],
)
def test_the_band_is_its_people_stores_states_and_action(band: dict[str, object], lang: str, said: str) -> None:
    assert band_words(band, lang) == said


def test_a_line_carries_the_band_and_the_status_when_it_moved() -> None:
    moved = {'seq': 7, 'date': DATE, 'events': [SEASON], 'changes': {'seat': {'status': 52.0}}}
    still = {'seq': 8, 'date': DATE, 'events': [], 'changes': {'seat': {'council': None}}}

    assert line(moved, 'en', BAND) == (
        'day 1, month 3, year 1, summer: '
        '15 people, forage 22.5, water 30, camps. Your standing is 52. Year 1: summer has come.'
    )
    assert line(moved, 'ru', BAND) == (
        'день 1, месяц 3, год 1, лето: '
        '15 человек, подножный корм 22,5, вода 30, стоит лагерем. Ваш вес 52. Год 1: наступило лето.'
    )
    assert line(still, 'en', BAND) == ('day 1, month 3, year 1, summer: 15 people, forage 22.5, water 30, camps.')


def test_a_line_shows_the_table_of_a_council_that_sits() -> None:
    table = [
        {'proposal': {'kind': 'stay-and-gather'}, 'key': 'proposal-stay-and-gather', 'votes': 8},
        {'proposal': {'kind': 'go', 'to': {'x': 3, 'y': 0}}, 'key': 'proposal-go-forest', 'votes': 5},
    ]
    sitting = {'leader': {'kind': 'stay-and-gather'}, 'table': table}
    opened = {'seq': 9, 'date': DATE, 'events': [], 'changes': {'seat': {'council': sitting}}}
    empty = {'seq': 9, 'date': DATE, 'events': [], 'changes': {'seat': {'council': {'leader': None, 'table': []}}}}

    assert line(opened, 'en') == (
        'day 1, month 3, year 1, summer: ' 'The votes: we stay and gather - 8; we go into the forest - 5.'
    )
    assert line(opened, 'ru').endswith('Голоса: остаёмся собирать - 8; идём в лес - 5.')
    assert line(empty, 'en') == 'day 1, month 3, year 1, summer'


def test_the_band_follows_the_changes_and_leaves_when_gone() -> None:
    walked = {**BAND, 'action': {'kind': 'move', 'towards': 'east'}}

    assert follow(BAND, {'changes': {'units': [], 'gone': []}}) == BAND
    assert follow(BAND, {'changes': {'units': [walked], 'gone': []}}) == walked
    assert follow(None, {'changes': {'units': [walked], 'gone': []}}) == walked
    assert follow(BAND, {'changes': {'units': [], 'gone': [1]}}) is None
    assert follow(BAND, {'changes': {}}) == BAND


@pytest.mark.parametrize('lang', ['en', 'ru'])
@pytest.mark.parametrize('key', sorted(EVENTS))
def test_every_event_is_spoken_in_both_languages(key: str, lang: str) -> None:
    said = words({'key': key, 'values': SAMPLES[key]}, lang)
    keyed = [value for name, value in SAMPLES[key].items() if name != 'id' and isinstance(value, str) and '-' in value]

    assert said != key
    assert [value for value in keyed if value in said] == []


def test_the_parts_of_a_line_carry_how_each_looks() -> None:
    update = {
        'seq': 7,
        'date': DATE,
        'events': [MONTH, {'key': 'people-lost', 'values': {'count': 2, 'cause': 'hunger'}}],
        'changes': {'seat': {'status': 48.0}},
    }

    said = parts(update, 'en', {**BAND, 'states': ['thirst']})

    assert ''.join(part.text for part in said) == line(update, 'en', {**BAND, 'states': ['thirst']})
    assert [part.look for part in said if part.look != Look.PLAIN] == [
        Look.DATE,
        Look.BAND,
        Look.BAND,
        Look.BAND,
        Look.STATE,
        Look.BAND,
        Look.STATUS,
        Look.EVENT,
        Look.LOSS,
    ]
