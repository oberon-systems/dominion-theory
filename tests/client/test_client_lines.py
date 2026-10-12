from dominion_theory.client import line, words

DATE = {'year': 1, 'month': 3, 'day': 1, 'part': 'morning', 'season': 'summer'}
SEASON = {'key': 'season-started', 'values': {'year': 1, 'season': 'summer'}}
MONTH = {'key': 'month-started', 'values': {'year': 1, 'month': 3, 'season': 'summer'}}


def test_a_message_becomes_words_in_the_language() -> None:
    assert words(SEASON, 'en') == 'Year 1: summer has come.'
    assert words(SEASON, 'ru') == 'Год 1: наступило лето.'


def test_a_message_without_values_is_rendered() -> None:
    assert words({'key': 'error-request-unreadable'}, 'en') == 'The request cannot be read.'


def test_a_line_is_the_date_and_the_words_of_the_events_in_order() -> None:
    update = {'seq': 100, 'date': DATE, 'events': [MONTH, SEASON]}

    assert line(update, 'en') == (
        'morning, day 1, month 3, year 1, summer: '
        'Month 3 of year 1 begins; the season is summer. Year 1: summer has come.'
    )
    assert line(update, 'ru') == (
        'утро, день 1, месяц 3, год 1, лето: ' 'Начался месяц 3 года 1; время года — лето. Год 1: наступило лето.'
    )


def test_a_line_without_events_is_the_date_alone() -> None:
    update = {'seq': 101, 'date': {**DATE, 'part': 'midday'}, 'events': []}

    assert line(update, 'en') == 'midday, day 1, month 3, year 1, summer'
