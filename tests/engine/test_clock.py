import ast
from pathlib import Path

import pytest

from dominion_theory.content import Duration, Time, load_params
from dominion_theory.engine import clock as clock_module
from dominion_theory.engine.clock import (
    DAY_STARTED,
    MONTH_STARTED,
    SEASON_STARTED,
    YEAR_STARTED,
    Boundary,
    Clock,
    Date,
)

DEFAULT_PLAN = [
    {'season': 'spring', 'day': 1},
    {'season': 'summer', 'day': 21},
    {'season': 'autumn', 'day': 51},
    {'season': 'winter', 'day': 71},
]


@pytest.fixture
def time() -> Time:
    return load_params().time


@pytest.fixture
def harsh() -> Time:
    return load_params(preset='harsh-winter').time


def test_game_starts_on_the_first_morning(time: Time) -> None:
    assert Clock(time).date == Date(1, 1, 1, 'morning', 'spring')


def test_worked_example(time: Time) -> None:
    assert Clock(time, 1234).date == Date(3, 5, 7, 'night', 'summer')


@pytest.mark.parametrize(
    ('parts', 'date'),
    [
        (4, Date(1, 1, 1, 'night', 'spring')),
        (5, Date(1, 1, 2, 'morning', 'spring')),
        (49, Date(1, 1, 10, 'night', 'spring')),
        (50, Date(1, 2, 1, 'morning', 'spring')),
        (99, Date(1, 2, 10, 'night', 'spring')),
        (100, Date(1, 3, 1, 'morning', 'summer')),
        (499, Date(1, 10, 10, 'night', 'winter')),
        (500, Date(2, 1, 1, 'morning', 'spring')),
    ],
)
def test_first_and_last_part_of_each_unit(time: Time, parts: int, date: Date) -> None:
    assert Clock(time, parts).date == date


def test_clock_is_restored_from_its_count(time: Time) -> None:
    clock = Clock(time)
    for _ in range(137):
        clock.advance(1)

    assert Clock(time, clock.parts).date == clock.date


def test_negative_count_is_refused(time: Time) -> None:
    with pytest.raises(ValueError):
        Clock(time, -1)


def test_tick_inside_a_day_crosses_nothing(time: Time) -> None:
    clock = Clock(time)

    assert clock.advance(1) == []
    assert clock.parts == 1


def test_tick_of_a_day_crosses_one_day(time: Time) -> None:
    assert Clock(time).advance(5) == [Boundary(DAY_STARTED, {'year': 1, 'month': 1, 'day': 2})]


def test_month_boundary(time: Time) -> None:
    assert Clock(time, 49).advance(1) == [
        Boundary(DAY_STARTED, {'year': 1, 'month': 2, 'day': 1}),
        Boundary(MONTH_STARTED, {'year': 1, 'month': 2, 'season': 'spring'}),
    ]


def test_season_boundary(time: Time) -> None:
    assert Clock(time, 99).advance(1) == [
        Boundary(DAY_STARTED, {'year': 1, 'month': 3, 'day': 1}),
        Boundary(MONTH_STARTED, {'year': 1, 'month': 3, 'season': 'summer'}),
        Boundary(SEASON_STARTED, {'year': 1, 'season': 'summer'}),
    ]


def test_year_boundary_reports_all_four_in_order(time: Time) -> None:
    assert Clock(time, 499).advance(1) == [
        Boundary(DAY_STARTED, {'year': 2, 'month': 1, 'day': 1}),
        Boundary(MONTH_STARTED, {'year': 2, 'month': 1, 'season': 'spring'}),
        Boundary(SEASON_STARTED, {'year': 2, 'season': 'spring'}),
        Boundary(YEAR_STARTED, {'year': 2, 'seasons': DEFAULT_PLAN}),
    ]


def test_tick_longer_than_a_day_reports_every_day(time: Time) -> None:
    crossed = Clock(time).advance(10)

    assert [boundary.values['day'] for boundary in crossed] == [2, 3]


def test_a_year_of_ticks_counts_its_boundaries(time: Time) -> None:
    clock = Clock(time)
    keys = [boundary.key for _ in range(500) for boundary in clock.advance(1)]

    assert keys.count(DAY_STARTED) == 100
    assert keys.count(MONTH_STARTED) == 10
    assert keys.count(SEASON_STARTED) == 4
    assert keys.count(YEAR_STARTED) == 1


def test_schedule_of_the_defaults(time: Time) -> None:
    schedule = Clock(time).schedule(1)

    assert schedule.year == 1
    assert schedule.plan() == DEFAULT_PLAN
    assert [schedule.season(day) for day in (1, 20, 21, 50, 51, 70, 71, 100)] == [
        'spring',
        'spring',
        'summer',
        'summer',
        'autumn',
        'autumn',
        'winter',
        'winter',
    ]


def test_harsh_winter_season_starts(harsh: Time) -> None:
    clock = Clock(harsh, 299)

    assert clock.schedule(1).plan() == [
        {'season': 'spring', 'day': 1},
        {'season': 'summer', 'day': 21},
        {'season': 'autumn', 'day': 41},
        {'season': 'winter', 'day': 61},
    ]
    assert clock.date == Date(1, 6, 10, 'night', 'autumn')
    assert clock.advance(1)[-1] == Boundary(SEASON_STARTED, {'year': 1, 'season': 'winter'})
    assert clock.date == Date(1, 7, 1, 'morning', 'winter')


def test_harsh_winter_keeps_the_length_of_the_year(harsh: Time) -> None:
    clock = Clock(harsh, 499)

    assert clock.date == Date(1, 10, 10, 'night', 'winter')
    assert clock.advance(1)[-1].key == YEAR_STARTED
    assert clock.date == Date(2, 1, 1, 'morning', 'spring')


@pytest.mark.parametrize(
    ('written', 'parts'),
    [
        ({'parts': 2}, 2),
        ({'days': 3}, 15),
        ({'months': 1}, 50),
        ({'years': 2}, 1000),
        ({'days': 0}, 0),
    ],
)
def test_duration_in_parts(time: Time, written: dict[str, int], parts: int) -> None:
    assert Clock(time).to_parts(Duration(**written)) == parts


def test_duration_follows_the_parameters() -> None:
    short = load_params(overrides={'time.days_per_month': 6}).time

    assert Clock(short).to_parts(Duration(months=1)) == 30
    assert Clock(short).to_parts(Duration(years=1)) == 300


@pytest.mark.parametrize('parts_per_tick', [1, 5])
def test_shares_of_a_flow_sum_to_the_daily_amount(time: Time, parts_per_tick: int) -> None:
    clock = Clock(time)
    ticks = time.parts_per_day // parts_per_tick

    assert sum(clock.daily_share(3.7, parts_per_tick) for _ in range(ticks)) == pytest.approx(3.7)


@pytest.mark.parametrize('parts_per_tick', [1, 5])
def test_shares_of_a_yearly_rate_sum_to_the_yearly_amount(time: Time, parts_per_tick: int) -> None:
    clock = Clock(time)
    ticks = clock.parts_per_year // parts_per_tick

    assert sum(clock.yearly_share(0.04, parts_per_tick) for _ in range(ticks)) == pytest.approx(0.04)


def test_module_reads_no_wall_clock() -> None:
    tree = ast.parse(Path(clock_module.__file__).read_text())
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            modules.add('.' * node.level + (node.module or ''))

    assert modules == {'collections.abc', 'dataclasses', 'typing', '..content'}
