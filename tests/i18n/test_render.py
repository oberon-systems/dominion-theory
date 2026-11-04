import logging

import pytest

from dominion_theory.core.errors import DominionError
from dominion_theory.i18n import LOCALE_UNKNOWN, catalogues, render

DATE = {'year': 1, 'month': 7, 'day': 3, 'part': 'evening', 'season': 'autumn'}


def test_message_with_values() -> None:
    assert render('error-game-not-found', {'id': 'alpha'}, 'en') == 'There is no game alpha.'
    assert render('error-game-not-found', {'id': 'alpha'}, 'ru') == 'Игра alpha не найдена.'


def test_english_is_the_default() -> None:
    assert render('time-season-winter') == 'winter'


def test_value_that_is_a_key_is_rendered_in_place() -> None:
    values = {'id': 'c-1', 'reason': 'refused-unknown-command'}

    assert render('command-refused', values, 'en') == 'Command c-1 was refused: there is no such command.'
    assert render('command-refused', values, 'ru') == 'Команда c-1 отклонена: такой команды нет.'


def test_date_is_rendered_through_its_own_message() -> None:
    assert render('time-date', DATE, 'en') == 'day 3, month 7, year 1, autumn'
    assert render('time-date', DATE, 'ru') == 'день 3, месяц 7, год 1, осень'


def test_date_as_a_value_is_put_in_place() -> None:
    words = render('error-game-not-found', {'id': DATE}, 'en')

    assert words == 'There is no game day 3, month 7, year 1, autumn.'


def test_identifier_becomes_a_name() -> None:
    values = {'year': 2, 'month': 3, 'season': 'summer'}

    assert render('month-started', values, 'en') == 'Month 3 of year 2 begins; the season is summer.'
    assert render('month-started', values, 'ru') == 'Начался месяц 3 года 2; время года — лето.'


def test_russian_verb_agrees_with_the_gender_of_the_season() -> None:
    assert render('season-started', {'year': 1, 'season': 'summer'}, 'ru') == 'Год 1: наступило лето.'
    assert render('season-started', {'year': 1, 'season': 'winter'}, 'ru') == 'Год 1: наступила зима.'


def test_value_the_message_does_not_ask_for_is_left_out() -> None:
    values = {'year': 2, 'seasons': [{'season': 'spring', 'day': 1}]}

    assert render('year-started', values, 'ru') == 'Начался год 2.'


def test_value_that_is_neither_number_nor_text_is_shown_as_written() -> None:
    values = {'path': 'time.seasons', 'found': ['alpha', 'alpha'], 'expected': 'beta'}

    words = render('error-params-invalid', values, 'en')

    assert words == "The parameter time.seasons is ['alpha', 'alpha']; expected beta."


def test_russian_counts_people_in_three_forms() -> None:
    forms = [render('people-lost', {'count': count}, 'ru') for count in (1, 3, 5)]

    assert forms == ['Погиб 1 человек.', 'Погибли 3 человека.', 'Погибло 5 человек.']


def test_english_counts_people_in_two_forms() -> None:
    forms = [render('people-lost', {'count': count}, 'en') for count in (1, 3, 5)]

    assert forms == ['1 person has died.', '3 people have died.', '5 people have died.']


def test_missing_in_the_language_falls_back_to_english(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    texts = {'en': 'alpha-word = alpha { $id }\n', 'ru': 'beta-word = бета\n'}
    monkeypatch.setattr(catalogues, 'catalogue', lambda lang: texts[lang])
    catalogues._bundle.cache_clear()

    try:
        with caplog.at_level(logging.WARNING):
            assert render('alpha-word', {'id': 7}, 'ru') == 'alpha 7'
    finally:
        catalogues._bundle.cache_clear()

    assert 'the message alpha-word is missing in ru' in caplog.text


def test_missing_everywhere_gives_the_key(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING):
        assert render('alpha-missing', {'id': 7}, 'ru') == 'alpha-missing'

    assert 'the message alpha-missing is missing in ru' in caplog.text
    assert 'the message alpha-missing is missing in en' in caplog.text


@pytest.mark.parametrize(
    ('key', 'measures', 'lang', 'words'),
    [
        (
            'proposal-failed',
            ('proposal-camp', 80.0, 5, 12.0, 3.0, 0),
            'en',
            'It went badly: we camp here. Hungry 5 days, stores 12 -> 3 days. Your standing is now 80.',
        ),
        (
            'proposal-worked',
            ('proposal-explore-ne', 54.0, 0, 6.0, 7.0, 9),
            'en',
            'It went well: we explore to the north-east. 9 new cells, stores 6 -> 7 days. Your standing is now 54.',
        ),
        (
            'proposal-even',
            ('proposal-camp', 54.0, 1, 3.5, 1.0, 1),
            'en',
            'It came out even: we camp here. Hungry 1 day, 1 new cell, stores 3.5 -> 1 day. Your standing stays 54.',
        ),
        (
            'proposal-worked',
            ('proposal-camp', 53.0, 0, 6.0, 6.0, 0),
            'en',
            'It went well: we camp here. Stores 6 -> 6 days. Your standing is now 53.',
        ),
        (
            'proposal-failed',
            ('proposal-camp', 80.0, 5, 12.0, 3.0, 0),
            'ru',
            'Вышло плохо: стоим здесь. Голодали 5 дней, запасы 12 -> 3 дн. Ваш вес теперь 80.',
        ),
        (
            'proposal-worked',
            ('proposal-explore-ne', 54.0, 0, 6.0, 7.0, 9),
            'ru',
            'Всё вышло хорошо: идём в разведку на северо-восток. 9 новых клеток, запасы 6 -> 7 дн. Ваш вес теперь 54.',
        ),
        (
            'proposal-even',
            ('proposal-camp', 54.0, 2, 3.5, 1.0, 1),
            'ru',
            (
                'Ни хорошо, ни плохо: стоим здесь. Голодали 2 дня, 1 новая клетка, запасы 3,5 -> 1 дн. '
                'Ваш вес остаётся 54.'
            ),
        ),
        (
            'proposal-worked',
            ('proposal-camp', 53.0, 0, 6.0, 6.0, 0),
            'ru',
            'Всё вышло хорошо: стоим здесь. Запасы 6 -> 6 дн. Ваш вес теперь 53.',
        ),
    ],
)
def test_a_verdict_says_why_and_only_what_happened(
    key: str, measures: tuple[str, float, int, float, float, int], lang: str, words: str
) -> None:
    values = dict(zip(('proposal', 'status', 'short', 'before', 'after', 'found'), measures, strict=True))

    assert render(key, values, lang) == words


def test_missing_value_is_logged(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING):
        assert render('error-game-not-found', {}, 'en') == 'There is no game id.'

    assert 'the message error-game-not-found in en' in caplog.text


def test_unknown_language_is_refused() -> None:
    with pytest.raises(DominionError) as raised:
        render('time-season-winter', lang='xx')

    assert raised.value.key == LOCALE_UNKNOWN
