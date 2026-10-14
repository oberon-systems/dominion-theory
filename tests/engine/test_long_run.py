from dataclasses import dataclass
from typing import Any

import pytest

from dominion_theory.content import load_params
from dominion_theory.engine import Game
from dominion_theory.engine.events import BAND_DIED, BAND_STATE_BEGAN, PEOPLE_LOST

SMALL = {'planet.circumference_km': 4000, 'planet.window.width': 32, 'planet.window.height': 16}
NO_FOOD = {
    **SMALL,
    'units.band.gathering.forage': 0,
    'units.band.start.stores.forage': 0,
    'units.band.population.growth_per_year': 0,
    'encounters.chance': 0,
}
YEARS = 4
HALFWAY = 2
ACTIONS = ('moves', 'gathers', 'camps')


@dataclass(frozen=True)
class Year:
    totals: dict[str, float]
    population: int
    hash: str
    snapshot: dict[str, Any]


def live(game: Game, years: int) -> list[Year]:
    per_year = game.clock.parts_per_year
    before = dict(zip(game.counters.names, game.counters.row(), strict=True))
    lived = []
    first = game.clock.parts // per_year + 1
    for year in range(first, first + years):
        while game.clock.parts < year * per_year and not game.over:
            game.step()
        after = dict(zip(game.counters.names, game.counters.row(), strict=True))
        totals = {name: after[name] - before[name] for name in ACTIONS}
        population = 0 if game.band is None else game.band.population
        lived.append(Year(totals, population, game.state_hash(), game.snapshot()))
        before = after
    return lived


@pytest.fixture(scope='module')
def years() -> list[Year]:
    return live(Game.create(seed=42, params=load_params(overrides=SMALL)), YEARS)


def test_a_band_with_no_player_lives_for_years_and_moves_gathers_and_camps_in_every_one(years: list[Year]) -> None:
    least = load_params(overrides=SMALL).units.band.population.least

    assert len(years) == YEARS
    assert all(year.population >= least for year in years)
    assert all(year.totals[name] > 0 for year in years for name in ACTIONS)


def test_the_same_seed_lives_the_same_years_from_the_start_and_from_a_restore(years: list[Year]) -> None:
    again = live(Game.create(seed=42, params=load_params(overrides=SMALL)), 1)
    restored = live(Game.restore(years[HALFWAY - 1].snapshot), YEARS - HALFWAY)

    assert again[0].hash == years[0].hash
    assert [year.hash for year in restored] == [year.hash for year in years[HALFWAY:]]


def test_a_band_with_no_food_starves_and_dies_on_schedule() -> None:
    game = Game.create(seed=42, params=load_params(overrides=NO_FOOD))
    events: list[tuple[int, str, dict[str, Any]]] = []
    while not game.over:
        result = game.step()
        events.extend((result.tick, event.key, event.values) for event in result.events)

    # Starvation begins after two short days and takes one person a day, from 15 to 4, below the least of 5.
    assert [(tick, values) for tick, key, values in events if key == BAND_STATE_BEGAN] == [
        (10, {'state': 'state-starvation'})
    ]
    assert [(tick, values) for tick, key, values in events if key == PEOPLE_LOST] == [
        (tick, {'count': 1, 'cause': 'hunger'}) for tick in range(10, 65, 5)
    ]
    assert [tick for tick, key, _ in events if key == BAND_DIED] == [60]
    assert (game.outcome, game.counters.row()[game.counters.names.index('deaths')]) == ('died', 11)
