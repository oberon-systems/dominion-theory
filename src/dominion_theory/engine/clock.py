"""
Game time: a count of parts since the start, and the calendar worked out from it.
"""

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

from ..content import Duration, Time

DAY_STARTED = 'day-started'
MONTH_STARTED = 'month-started'
SEASON_STARTED = 'season-started'
YEAR_STARTED = 'year-started'


@dataclass(frozen=True)
class Date:
    year: int
    month: int
    day: int
    part: str
    season: str


@dataclass(frozen=True)
class Boundary:
    key: str
    values: dict[str, Any]


class SeasonSchedule:
    """
    On which day of its year each season starts. Rules ask it; none counts months.
    """

    def __init__(self, time: Time, year: int) -> None:
        self.year = year
        starts = []
        day = 1
        for season in time.seasons:
            starts.append((season.name, day))
            day += season.months * time.days_per_month
        self.starts: tuple[tuple[str, int], ...] = tuple(starts)

    def season(self, day: int) -> str:
        return next(name for name, start in reversed(self.starts) if start <= day)

    def starting(self, day: int) -> str | None:
        return next((name for name, start in self.starts if start == day), None)

    def plan(self) -> list[dict[str, Any]]:
        return [{'season': name, 'day': start} for name, start in self.starts]


class Clock:
    """
    Holds the count of parts and nothing else; a date is never stored.
    """

    def __init__(self, time: Time, parts: int = 0) -> None:
        if parts < 0:
            raise ValueError('the count of parts cannot be negative')
        self._time = time
        self.parts = parts

    @property
    def parts_per_year(self) -> int:
        return self._time.parts_per_day * self._time.days_per_year

    @property
    def date(self) -> Date:
        return self._date(self.parts)

    def schedule(self, year: int) -> SeasonSchedule:
        return SeasonSchedule(self._time, year)

    def advance(self, parts_per_tick: int) -> list[Boundary]:
        if parts_per_tick < 1:
            raise ValueError('a tick covers at least one part')
        per_day = self._time.parts_per_day
        first = self.parts // per_day + 1
        self.parts += parts_per_tick
        crossed: list[Boundary] = []
        for days in range(first, self.parts // per_day + 1):
            crossed.extend(self._boundaries(days))
        return crossed

    def to_parts(self, duration: Duration) -> int:
        per_day = self._time.parts_per_day
        per_unit = {
            'parts': 1,
            'days': per_day,
            'months': per_day * self._time.days_per_month,
            'years': self.parts_per_year,
        }
        return duration.amount * per_unit[duration.unit]

    def daily_share(self, per_day: float, parts_per_tick: int) -> float:
        return per_day * parts_per_tick / self._time.parts_per_day

    def yearly_share(self, per_year: float, parts_per_tick: int) -> float:
        return per_year * parts_per_tick / self.parts_per_year

    def _date(self, parts: int) -> Date:
        time = self._time
        days, part = divmod(parts, time.parts_per_day)
        year, day_of_year = divmod(days, time.days_per_year)
        month, day = divmod(day_of_year, time.days_per_month)
        season = self.schedule(year + 1).season(day_of_year + 1)
        return Date(year + 1, month + 1, day + 1, time.day_parts[part], season)

    def _boundaries(self, days: int) -> Iterator[Boundary]:
        date = self._date(days * self._time.parts_per_day)
        day_of_year = days % self._time.days_per_year + 1
        schedule = self.schedule(date.year)
        yield Boundary(DAY_STARTED, {'year': date.year, 'month': date.month, 'day': date.day})
        if date.day == 1:
            yield Boundary(MONTH_STARTED, {'year': date.year, 'month': date.month, 'season': date.season})
        if schedule.starting(day_of_year) is not None:
            yield Boundary(SEASON_STARTED, {'year': date.year, 'season': date.season})
        if day_of_year == 1:
            yield Boundary(YEAR_STARTED, {'year': date.year, 'seasons': schedule.plan()})
