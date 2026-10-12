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
    assert render('time-date', DATE, 'en') == 'evening, day 3, month 7, year 1, autumn'
    assert render('time-date', DATE, 'ru') == 'вечер, день 3, месяц 7, год 1, осень'


def test_date_as_a_value_is_put_in_place() -> None:
    words = render('error-game-not-found', {'id': DATE}, 'en')

    assert words == 'There is no game evening, day 3, month 7, year 1, autumn.'


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


def test_missing_value_is_logged(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING):
        assert render('error-game-not-found', {}, 'en') == 'There is no game id.'

    assert 'the message error-game-not-found in en' in caplog.text


def test_unknown_language_is_refused() -> None:
    with pytest.raises(DominionError) as raised:
        render('time-season-winter', lang='xx')

    assert raised.value.key == LOCALE_UNKNOWN
