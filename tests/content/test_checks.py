import pytest

from dominion_theory.content import load_params
from dominion_theory.core.errors import DominionError


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
    params = load_params(overrides={'time.day_parts': ['day', 'night'], 'eras.band.parts_per_tick': 2})

    assert params.eras.band.parts_per_tick == 2
