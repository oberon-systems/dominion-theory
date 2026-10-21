import json
from typing import Any

import numpy as np
import pytest

from dominion_theory.content import Params, load_params
from dominion_theory.engine import Game, StepResult, Window
from dominion_theory.engine import band as bands
from dominion_theory.engine.band import Action, camp, gathering, moving, roaming
from dominion_theory.engine.stock import Stock
from dominion_theory.engine.streams import Streams
from dominion_theory.planet import biome_names

# The band does what it is told in every part of the day; the camp of the evening and the night is tested alone.
SMALL = {
    'planet.circumference_km': 4000,
    'planet.window.width': 32,
    'planet.window.height': 16,
    'encounters.chance': 0.0,
    'units.band.camp_parts': [],
    'units.band.decisions.horizon': 0,
    'units.band.unease.gain': 0.0,
    'units.band.people.birth.conceive_per_day': 0.0,
    'units.band.people.injury.per_day': 0.0,
    'units.band.people.age.per_year': 0.0,
    'units.band.people.stages.adult.dies.frailty': 0.0,
}
WEST = 100
NORTH = 50
ROWS = (
    ('grass', 'forest', 'shallows', 'shallows', 'water'),
    ('grass', 'grass', 'shallows', 'shallows', 'water'),
)
HOME = (WEST, NORTH + 1)
MEADOW = (WEST + 1, NORTH + 1)
FOREST = (WEST + 1, NORTH)
SHORE = (WEST + 2, NORTH + 1)
SHELF = (WEST + 2, NORTH)
DEEPER = (WEST + 3, NORTH + 1)
SUMMER = 100
WINTER = 350
DAY = 5
PACE = 1.2 - 0.03 * 1.5
CALENDAR = ('day-started', 'month-started', 'season-started', 'year-started')


@pytest.fixture
def params() -> Params:
    return load_params(overrides=SMALL)


def land(
    params: Params,
    at: tuple[int, int] | None = HOME,
    rows: tuple[tuple[str, ...], ...] = ROWS,
    parts: int = SUMMER,
) -> Game:
    """
    A game on a hand-made window in summer, with a band where asked.
    """
    names = biome_names(params)
    biomes = np.array([[names.index(name) for name in row] for row in rows], dtype=np.uint8)
    rivers = np.zeros(biomes.shape, dtype=np.bool_)
    game = Game(7, params, Streams(7), Window(0, WEST, NORTH, len(rows[0]), len(rows)), biomes, rivers)
    game.clock.parts = parts
    if at is not None:
        game.band = bands.start(game, *at, game.day, game.streams['people'])
        game.band.members = bands.adults(game.band.population)
        game.band.changed()
    return game


def needing(**per_day: float) -> Params:
    rates = {f'units.band.consumption_per_day.{name}': rate for name, rate in per_day.items()}
    return load_params(overrides={**SMALL, **rates})


class Dice:
    """
    A stream on which every chance comes up and every range gives its low end.
    """

    def random(self, count: int | None = None) -> Any:
        return 0.0 if count is None else np.zeros(count)

    def integers(self, low: int, high: int | None = None, size: int | None = None) -> Any:
        return (0 if high is None else low) if size is None else np.zeros(size, dtype=int)


def dice() -> Any:
    return Dice()


def do(game: Game, action: Action, times: int = 1) -> StepResult:
    game.choose = lambda _game, _band: action
    for _ in range(times):
        if game.band is not None:
            game.band.intent = None
        result = game.step()
    return result


def band(game: Game) -> bands.Band:
    assert game.band is not None
    return game.band


def told(result: StepResult) -> list[tuple[str, dict[str, Any]]]:
    return [(event.key, event.values) for event in result.events if event.key not in (*CALENDAR, 'skill-learned')]


def counted(game: Game) -> dict[str, float]:
    return dict(zip(game.counters.names, game.counters.row(), strict=True))


def carried(game: Game) -> dict[str, Any]:
    snapshot = game.snapshot()
    grids = snapshot.pop('grids')
    held: dict[str, Any] = json.loads(json.dumps(snapshot))
    held['grids'] = {name: grid.tolist() for name, grid in grids.items()}
    return held


def test_a_created_game_has_a_band_as_its_document_starts_it(params: Params) -> None:
    game = Game.create(seed=7, params=params)
    held = band(game)

    assert game.biome(*held.place) in params.units.band.start.biomes
    assert (held.id, held.population, held.fatigue, held.states, held.action) == (1, 15, 0.0, [], {'kind': 'camp'})
    assert (held.held('forage'), held.held('water')) == (15.0, 15.0)
    assert (game.over, game.outcome) == (False, None)


def test_the_band_starts_nearest_the_centre_with_the_smaller_y_then_x(params: Params) -> None:
    even = land(params, at=None, rows=(('grass',) * 4, ('grass',) * 4))
    lone = land(params, at=None, rows=(('outcrops', 'outcrops', 'outcrops', 'grass'),))

    assert even._start() == (WEST + 1, NORTH)
    assert lone._start() == (WEST + 3, NORTH)


def test_without_a_start_biome_the_band_takes_what_can_be_entered(params: Params) -> None:
    rocky = land(params, at=None, rows=(('water', 'shallows', 'outcrops', 'mountain'),))
    sea = land(params, at=None, rows=(('water', 'shallows'),))

    assert rocky._start() == (WEST + 2, NORTH)
    assert sea._start() is None


def test_a_game_without_a_band_steps_and_reports_none(params: Params) -> None:
    game = land(params, at=None)

    result = game.step()

    assert (result.changes['units'], result.changes['gone'], result.units) == ([], [], [])
    assert counted(game)['population'] == 0
    assert game.snapshot()['units'] == []


def test_a_band_crosses_grass_in_a_tick_and_a_forest_in_two(params: Params) -> None:
    game = land(params)

    do(game, moving('east'))
    over_grass = band(game).place
    do(game, moving('north'))
    halfway = band(game).place, band(game).progress, band(game).target
    do(game, moving('north'))

    assert over_grass == MEADOW
    assert (halfway[0], halfway[2]) == (MEADOW, FOREST)
    assert halfway[1] == pytest.approx(PACE * 0.6 * (1 - 0.5 * 0.3))
    assert (band(game).place, band(game).progress, band(game).target) == (FOREST, 0.0, None)
    assert counted(game)['moves'] == 3


def test_a_camp_keeps_the_way_into_a_cell_and_a_gather_loses_it(params: Params) -> None:
    kept, lost = land(params, at=MEADOW), land(params, at=MEADOW)

    do(kept, moving('north'))
    do(kept, camp())
    halfway = band(kept).progress, band(kept).target
    do(kept, moving('north'))
    do(lost, moving('north'))
    do(lost, gathering({'forage': 1.0}))
    do(lost, moving('north'))

    assert halfway[0] == pytest.approx(PACE * 0.6)
    assert (halfway[1], band(kept).place) == (FOREST, FOREST)
    assert band(lost).place == MEADOW
    assert band(lost).progress == pytest.approx(PACE * 0.6 * (1 - 0.5 * 0.4))


def test_the_shallows_are_never_entered(params: Params) -> None:
    game = land(params, at=MEADOW)

    refused = do(game, moving('east'))
    roamed = do(game, roaming('east'))

    assert band(game).place == MEADOW
    assert (refused.units[0][4], roamed.units[0][4]) == ('camp', 'camp')
    assert [bands.enterable(game, *at) for at in (SHORE, DEEPER, (WEST + 4, NORTH))] == [False, False, False]
    assert counted(game)['camps'] == 2


def test_a_band_by_the_shallows_gathers_from_them_when_they_give_more(params: Params) -> None:
    game = land(params, at=MEADOW, parts=WINTER)
    sources = bands.source(game, MEADOW, 'forage'), bands.source(game, HOME, 'forage')

    do(game, gathering({'forage': 1.0}))

    assert sources == ((SHELF, 1.0), (HOME, 1.0))
    assert game.cells.stock(SHELF, 'food') < 1.0
    assert game.cells.stock(MEADOW, 'food') == 1.0
    assert band(game).held('forage') == pytest.approx(15 + 15 * 3.0 * 0.5)


def test_a_new_season_changes_what_the_band_expects_of_the_land_it_remembers() -> None:
    game = land(load_params(overrides={**SMALL, 'units.band.sight': 0}), parts=WINTER - 1)
    autumn = {name: game.value(name, *MEADOW) for name in ('water', 'threat', 'passability')}
    band(game).known[MEADOW] = {'biome': 'grass', 'river': False, **autumn, 'food': 0.96 / 2, 'seen': game.day}

    result = do(game, camp())
    remembered = band(game).known[MEADOW]

    assert game.date.season == 'winter'
    assert remembered['food'] == pytest.approx(0.8 * 0.3 / 2)
    assert (remembered['water'], remembered['passability']) == (game.value('water', *MEADOW), 0.7)
    assert remembered['threat'] == autumn['threat']
    assert {'x': MEADOW[0], 'y': MEADOW[1], **remembered} in result.changes['known']


def test_a_move_out_of_the_window_is_a_camp(params: Params) -> None:
    game = land(params)

    do(game, moving('west'))

    assert (band(game).place, band(game).action) == (HOME, {'kind': 'camp'})
    assert not bands.enterable(game, WEST - 1, NORTH + 1)


def test_gathering_fills_the_stores_and_empties_the_cell(params: Params) -> None:
    game = land(params)

    first = do(game, gathering({'forage': 1.0}))
    once = band(game).held('forage')
    do(game, gathering({'water': 1.0}))
    do(game, gathering({'forage': 1.0}))

    assert once == pytest.approx(15 + 15 * 3.0 * 0.8)
    assert band(game).held('water') == pytest.approx(15 + 15 * 4.0 * 0.4 * 0.7 * (1 - 0.5 * 0.1))
    assert band(game).held('forage') == pytest.approx(90 - band(game).held('water'))
    assert bands.room(params, band(game)) == pytest.approx(0.0)
    assert first.changes['units'][0]['action'] == {'kind': 'gather', 'shares': {'forage': 1.0}}
    assert first.changes['units'][0]['place'] == {'scale': 0, 'x': WEST, 'y': NORTH + 1}
    assert first.changes['cells'][0]['food'] < 1.0
    assert counted(game)['gathers'] == 3


def test_a_cell_pays_the_share_of_its_capacity_that_was_taken(params: Params) -> None:
    game = land(params)

    do(game, gathering({'forage': 1.0}))

    assert game.cells.stock(HOME, 'food') == pytest.approx(1 - 36 / 100 + 1 / (20 * DAY))
    assert game.cells.stock(HOME, 'water') == 1.0


def test_a_roaming_band_forages_the_cell_ahead_and_walks_slower(params: Params) -> None:
    game = land(params)
    before = {name: band(game).held(name) for name in ('forage', 'water')}

    result = do(game, roaming('east'))

    taken = {name: band(game).held(name) - before[name] for name in before}
    assert taken == pytest.approx({'forage': 15 * 3 * 0.8 * 0.5, 'water': 15 * 4 * 0.28 * 0.5})
    assert band(game).place == HOME
    assert band(game).progress == pytest.approx(PACE * 0.75)
    assert game.cells.stock(MEADOW, 'food') == pytest.approx(1 - 18 / 100 + 1 / (20 * DAY))
    assert band(game).fatigue == pytest.approx(0.15)
    assert counted(game)['roams'] == 1
    assert result.changes['units'][0]['action'] == {'kind': 'roam', 'towards': 'east'}


def test_a_roaming_band_takes_nothing_it_has_two_days_of(params: Params) -> None:
    game = land(params)
    band(game).stores['water'] = [[float(game.day), 45.0]]

    do(game, roaming('east'))

    assert band(game).held('water') == 45.0
    assert band(game).held('forage') == pytest.approx(15 + 15 * 3 * 0.8 * 0.5)


def test_a_roam_into_water_is_a_camp_and_takes_nothing(params: Params) -> None:
    game = land(params, at=(WEST + 3, NORTH + 1))
    before = {name: band(game).held(name) for name in ('forage', 'water')}

    do(game, roaming('east'))

    assert band(game).action == {'kind': 'camp'}
    assert {name: band(game).held(name) for name in before} == before


def test_a_loaded_band_gathers_nothing_and_leaves_the_cell_alone(params: Params) -> None:
    game = land(params)
    band(game).stores['water'] = [[20.0, 75.0]]

    do(game, gathering({'forage': 1.0}))

    assert bands.room(params, band(game)) == 0.0
    assert band(game).held('forage') == 15.0
    assert band(game).action == {'kind': 'gather', 'shares': {'forage': 1.0}}
    assert len(game.cells) == 0


def test_water_that_does_not_run_out_keeps_no_cell(params: Params) -> None:
    game = land(params, at=MEADOW)

    do(game, gathering({'water': 1.0}))

    assert band(game).held('water') == pytest.approx(15 + 60)
    assert len(game.cells) == 0


def test_fatigue_grows_with_work_and_falls_in_camp(params: Params) -> None:
    game = land(params)

    do(game, moving('east'))
    do(game, gathering({'forage': 1.0}))
    worked = band(game).fatigue
    do(game, camp())

    assert worked == pytest.approx(0.3 + 0.1)
    assert band(game).fatigue == pytest.approx(0.1)


def test_the_band_camps_in_the_evening_and_the_night_whatever_it_wants() -> None:
    game = land(load_params(overrides={**SMALL, 'units.band.camp_parts': ['evening', 'night']}))
    game.choose = lambda _game, _band: gathering({'forage': 1.0})

    kinds = [game.step().units[0][4] for _ in range(DAY)]

    assert kinds == ['gather', 'gather', 'gather', 'camp', 'camp']
    assert band(game).reason == {'action': 'camp', 'need': 'rest', 'score': 0.0, 'pull': None}


def test_fatigue_slows_the_pace_and_tiredness_begins_and_ends_in_camp(params: Params) -> None:
    game = land(params)
    before = [do(game, moving(towards)) for towards in ('east', 'west')]
    began = do(game, moving('north'))
    slowed = bands.speed(params, band(game))
    still = do(game, camp())
    ended = do(game, camp())

    assert ([told(result) for result in before], told(still)) == ([[], []], [])
    assert told(began) == [('band-state-began', {'state': 'state-tiredness'})]
    assert began.changes['units'][0]['states'] == ['tiredness']
    assert slowed == pytest.approx(PACE * (1 - 0.5 * 0.9))
    assert told(ended) == [('band-state-ended', {'state': 'state-tiredness'})]
    assert band(game).states == []


def test_the_band_knows_what_lies_within_its_sight(params: Params) -> None:
    game = land(params)
    known = band(game).known

    assert sorted(known) == sorted((WEST + x, NORTH + y) for x in range(3) for y in range(2))
    assert known[FOREST] == {
        'biome': 'forest',
        'river': False,
        'water': pytest.approx(0.6),
        'food': pytest.approx(0.9),
        'threat': pytest.approx(0.4),
        'passability': pytest.approx(0.6),
        'stone': 0.0,
        'wood': pytest.approx(0.8),
        'plants': pytest.approx(0.5),
        'game': pytest.approx(0.7),
        'seen': 20,
    }


def test_news_of_the_land_come_with_the_tick_and_old_memories_go(params: Params) -> None:
    game = land(params)
    band(game).known[WEST + 4, NORTH] = {'biome': 'water', 'river': False, 'seen': -1}

    quiet = do(game, camp())
    gathered = do(game, gathering({'forage': 1.0}))
    walked = do(game, moving('east'))

    assert quiet.changes['known'] == []
    assert (WEST + 4, NORTH) not in band(game).known
    assert [(cell['x'], cell['y']) for cell in gathered.changes['known']] == [HOME]
    assert gathered.changes['known'][0]['food'] == pytest.approx(0.8 * 0.64)
    assert {(cell['x'], cell['y']) for cell in walked.changes['known']} == {HOME, (WEST + 3, NORTH), DEEPER}


def test_a_lot_is_thrown_away_when_its_time_is_over(params: Params) -> None:
    stores = Stock({'forage': [[0.0, 5.0], [2.0, 7.0]], 'water': [[0.0, 9.0]]})
    held = bands.Band(id=1, x=WEST, y=NORTH, members=bands.adults(15), stores=stores)

    bands.spoil(params, held, 3)
    after_three = held.plain()['stores']
    bands.spoil(params, held, 5)

    assert after_three == {'forage': [[2.0, 7.0]], 'water': [[0.0, 9.0]]}
    assert held.plain()['stores'] == {'forage': [], 'water': []}


def test_people_eat_the_oldest_lot_first(params: Params) -> None:
    stores = Stock({'forage': [[0.0, 4.0], [1.0, 9.0]], 'water': [[1.0, 5.0]]})
    held = bands.Band(id=1, x=WEST, y=NORTH, members=bands.adults(10), stores=stores)

    met = bands.eat(params, held).met

    assert held.stores == {'forage': [[1.0, 3.0]], 'water': []}
    assert met == {'forage': 1.0, 'water': 0.5}
    assert [member.thirsty for member in held.members] == [0.0] * 5 + [1.0] * 5


@pytest.mark.parametrize(
    ('needs', 'state', 'cause'),
    [({'water': 0.0}, 'state-starvation', 'hunger'), ({'forage': 0.0}, 'state-thirst', 'thirst')],
)
def test_an_adult_who_ate_in_full_is_hungry_the_second_day_without_and_dies_on_the_third(
    needs: dict[str, float], state: str, cause: str
) -> None:
    game = land(needing(**needs))

    fed = told(do(game, camp(), DAY))
    wanting = told(do(game, camp(), DAY))
    dead = told(do(game, camp(), DAY))

    assert fed == []
    assert wanting == [('band-state-began', {'state': state})]
    assert dead == [('people-lost', {'count': 14, 'cause': cause}), ('band-died', {})]


def test_what_little_there_is_goes_to_those_nearest_death_and_the_rest_die() -> None:
    game = land(needing(water=0.0))
    do(game, camp(), 2 * DAY)
    nearest = band(game).members[10]
    nearest.hungry = 1.5
    band(game).stores['forage'] = [[float(game.day), 7.0]]

    last = told(do(game, camp(), DAY))

    assert last == [
        ('band-state-ended', {'state': 'state-starvation'}),
        ('people-lost', {'count': 8, 'cause': 'hunger'}),
    ]
    assert (band(game).population, band(game).members[-1] is nearest) == (7, True)
    assert band(game).members[0].player
    assert [member.hungry for member in band(game).members] == [0.0] * 7


def test_a_newborn_dies_after_a_day_without_and_an_adult_is_only_hungry(params: Params) -> None:
    held = bands.Band(id=1, x=WEST, y=NORTH, members=[*bands.adults(2), bands.Member(0, 'female')])

    bands.eat(params, held)
    began, ended, lost = bands.suffer(params, held, 0)

    assert (began, ended, lost) == (['starvation', 'thirst'], [], [('hunger', 1)])
    assert held.population == 2


@pytest.mark.parametrize(
    ('stage', 'age', 'days'),
    [('child', 0, 1.0), ('child', 200, 1.5), ('child', 399, 1.9975), ('adult', 400, 2.0), ('elder', 1700, 1.5)],
)
def test_a_reserve_grows_with_a_child_and_is_smaller_for_an_elder(
    params: Params, stage: str, age: int, days: float
) -> None:
    assert bands.reserve(params, stage, age, 'food') == pytest.approx(days)


def test_a_hungry_member_gathers_and_walks_as_a_weakened_one_and_does_not_conceive() -> None:
    params = load_params(overrides={**SMALL, 'units.band.people.birth.conceive_per_day': 1.0})
    held = bands.Band(id=1, x=WEST, y=NORTH, members=bands.adults(4))
    held.members[2].hungry = 1.0
    held.changed()

    counted = bands.census(params, held)
    bands.live(params, held, 10, 1.0, True, 0.0, dice())

    assert (counted.gatherers, counted.pace) == pytest.approx((3.6, 0.9))
    assert [member.pregnant_until is not None for member in held.members] == [True, False, False, False]


def test_a_created_band_is_of_adults_of_random_age_and_sex_the_first_the_player(params: Params) -> None:
    members = band(Game.create(seed=7, params=params)).members

    assert all(400 <= member.age_days < 1500 for member in members)
    assert {member.sex for member in members} == {'female', 'male'}
    assert [member.player for member in members] == [True] + [False] * 14


def test_children_gather_nothing_elders_little_both_eat_less_and_walk_slower(params: Params) -> None:
    members = [*bands.adults(2), bands.Member(0, 'male'), bands.Member(1800, 'female')]
    held = bands.Band(id=1, x=WEST, y=NORTH, members=members)
    held.members[1].wound = {'severity': 'heavy', 'left': 9.0}

    counted = bands.census(params, held)

    assert counted.counts == {'child': 1, 'adult': 2, 'elder': 1}
    assert (counted.gatherers, counted.eaters, counted.carriers) == pytest.approx((1.0 + 0.2 + 0.4, 3.2, 2.75))
    assert counted.pace == pytest.approx((1.0 + 0.4 + 0.7 + 0.8) / 4)
    assert (counted.voters, counted.injured, counted.pregnant) == (3, 1, 0)
    assert counted.wounds == {'light': 0, 'medium': 0, 'heavy': 1}


@pytest.mark.parametrize(
    ('severity', 'pace', 'gathers'), [('light', 0.8, 0.7), ('medium', 0.6, 0.4), ('heavy', 0.4, 0.2)]
)
def test_a_wound_slows_and_keeps_from_gathering_by_its_severity(
    params: Params, severity: str, pace: float, gathers: float
) -> None:
    held = bands.Band(id=1, x=WEST, y=NORTH, members=bands.adults(2))
    held.members[1].wound = {'severity': severity, 'left': 1.0}

    counted = bands.census(params, held)

    assert (counted.pace, counted.gatherers) == pytest.approx(((1.0 + pace) / 2, 1.0 + gathers))


def test_the_dead_are_drawn_from_the_exposed_and_never_the_player(params: Params) -> None:
    held = bands.Band(id=1, x=WEST, y=NORTH, members=[*bands.adults(1), bands.Member(0, 'female')])

    lost, injured, _ = bands.struck(params, held, 0, 1.0, 0.0, {}, np.random.default_rng(7))

    assert (lost, injured, held.population, held.members[0].player) == (1, 0, 1, True)
    assert bands.vulnerable(params, held, 'encounter') == [0.0]


def test_a_child_is_most_exposed_at_birth_and_nears_an_adult_as_it_grows(params: Params) -> None:
    children = [bands.Member(age, 'female') for age in (0, 70, 140, 210)]
    members = [*bands.adults(2), *children, bands.Member(1800, 'male')]
    held = bands.Band(id=1, x=WEST, y=NORTH, members=members)

    assert bands.vulnerable(params, held, 'encounter') == pytest.approx([0.0, 1.0, 3.0, 2.0, 1.5, 1.25, 2.0])
    assert bands.vulnerable(params, held, 'frailty')[2:6] == pytest.approx([1.2, 0.6, 0.3, 0.15])
    assert bands._injurable(params, held)[2:6] == pytest.approx([0.5, 0.75, 0.875, 0.9375])


def test_the_old_and_the_frail_die_and_the_hurt_are_injured_while_the_player_lives() -> None:
    ageing = {'units.band.people.age.per_year': 0.5, 'units.band.people.injury.per_day': 0.5}
    params = load_params(overrides={**SMALL, **ageing})
    held = bands.Band(id=1, x=WEST, y=NORTH, members=[*bands.adults(2, 2000), bands.Member(0, 'female')])

    lived = bands.live(params, held, 10, 0.5, False, 0.0, dice())

    assert lived.lost == [('age', 1), ('frailty', 1)]
    assert (held.population, held.members[0].player, held.members[0].age_days) == (1, True, 2001)
    assert (lived.injured, held.members[0].wound) == (1, {'severity': 'light', 'left': 10.0})


@pytest.mark.parametrize(('weights', 'severity'), [({}, 'medium'), ({'light': 0.0, 'heavy': 1.0}, 'heavy')])
def test_the_severity_of_a_wound_is_drawn_by_the_weights_of_its_cause(weights: dict[str, float], severity: str) -> None:
    usual = {'units.band.people.injury.drawn.light': 0.0, 'units.band.people.injury.drawn.heavy': 0.0}
    params = load_params(overrides={**SMALL, **usual})
    held = bands.Band(id=1, x=WEST, y=NORTH, members=bands.adults(4))

    _, injured, _ = bands.struck(params, held, 0, 0.0, 1.0, weights, np.random.default_rng(7))

    assert injured == 4
    assert {member.wound['severity'] for member in held.members if member.wound} == {severity}


@pytest.mark.parametrize(('camped', 'days'), [(0.0, 20), (0.5, 14), (1.0, 10)])
def test_a_wound_heals_a_day_a_day_and_twice_as_fast_in_camp(params: Params, camped: float, days: int) -> None:
    held = bands.Band(id=1, x=WEST, y=NORTH, members=bands.adults(2))
    held.members[1].wound = {'severity': 'heavy', 'left': 20.0}

    lasted = 0
    while held.members[1].wound is not None:
        bands.live(params, held, 10 + lasted, 1.0, False, camped, dice())
        lasted += 1

    assert lasted == days
    assert bands.census(params, held).injured == 0


@pytest.mark.parametrize(('camped', 'shelter', 'lost'), [(0.0, 0.5, 3), (1.0, 0.0, 0), (0.5, 0.0, 3)])
def test_a_band_in_camp_dies_less_of_frailty(camped: float, shelter: float, lost: int) -> None:
    frail = {'units.band.people.stages.adult.dies.frailty': 200.0, 'units.band.shelter.frailty': shelter}
    params = load_params(overrides={**SMALL, **frail})
    held = bands.Band(id=1, x=WEST, y=NORTH, members=bands.adults(4))

    class Even(Dice):
        def random(self, count: int | None = None) -> Any:
            return np.full(count, 0.999) if count else 0.0

    even: Any = Even()
    lived = bands.live(params, held, 10, 0.0, False, camped, even)

    assert dict(lived.lost).get('frailty', 0) == lost


def test_a_day_in_camp_heals_a_wound_by_two_days_and_a_day_of_work_by_one(params: Params) -> None:
    game = land(params)
    band(game).members[1].wound = {'severity': 'heavy', 'left': 20.0}
    band(game).changed()

    do(game, camp(), DAY)
    camped = dict(band(game).members[1].wound or {})
    do(game, camp(), 2)
    do(game, gathering({'forage': 1.0}), DAY - 2)

    assert camped == {'severity': 'heavy', 'left': 18.0}
    assert (band(game).members[1].wound, band(game).camped) == ({'severity': 'heavy', 'left': 16.6}, 0)


def test_a_fed_band_conceives_and_gives_birth_with_a_pause_after() -> None:
    params = load_params(overrides={**SMALL, 'units.band.people.birth.conceive_per_day': 1.0})
    held = bands.Band(id=1, x=WEST, y=NORTH, members=bands.adults(4))

    bands.live(params, held, 10, 1.0, True, 0.0, dice())
    pregnant = [member.pregnant_until for member in held.members]
    held.members[0].pregnant_until = held.members[2].pregnant_until = 11
    born = bands.live(params, held, 11, 1.0, True, 0.0, dice())

    assert pregnant == [40, None, 40, None]
    assert (born.born, born.lost, held.population) == (2, [('birth', 1)], 5)
    assert (held.members[-1].age_days, held.members[0].rest_until) == (0, 21)


class Drawn:
    """
    A stream that draws the numbers given, then the low end of every range.
    """

    def __init__(self, *numbers: float) -> None:
        self.numbers = list(numbers)

    def random(self) -> float:
        return self.numbers.pop(0)

    def integers(self, low: int, high: int | None = None) -> int:
        return low if high is not None else 0


@pytest.mark.parametrize(
    ('known', 'herbs', 'born', 'mothers'),
    [(False, 1.0, 0, [1]), (True, 0.0, 0, [1]), (True, 1.0, 1, [])],
)
def test_the_oldest_woman_attends_a_birth_once_midwifery_is_known_and_a_herb_helps_more(
    params: Params, known: bool, herbs: float, born: int, mothers: list[int]
) -> None:
    members = [bands.Member(1000, 'male', player=True), bands.Member(1000, 'female'), bands.Member(1900, 'female')]
    members[1].pregnant_until = 10
    held = bands.Band(id=1, x=WEST, y=NORTH, members=members, stores=Stock({'herbs': [[0.0, herbs]]}))
    if known:
        held.lore['known'] += ['herbs', 'midwifery']

    drawn: Any = Drawn(0.58, 0.03)
    found = bands._births(params, held, 10, drawn)

    assert found == (born, mothers)
    assert held.held('herbs') == (0.0 if known else herbs)
    assert held.lore['counts']['births'] == 1


def test_an_encounter_leaves_dread_and_a_dangerous_day_unease_and_both_fade() -> None:
    params = load_params()
    held = bands.Band(id=1, x=WEST, y=NORTH, members=bands.adults(4))

    bands.frighten(params, held)
    bands.unsettle(params, held, 0.4)
    uneasy, dreaded = held.unease, held.dread[held.place]
    bands.unsettle(params, held, 0.0)

    assert (uneasy, dreaded) == pytest.approx((0.1 * 0.7, 0.3 - 0.015))
    assert held.unease == pytest.approx(uneasy * 0.8 + 0.1 * dreaded)
    assert held.dread[held.place] == pytest.approx(0.3 - 0.03)


def test_nobody_conceives_in_a_hungry_band_or_one_without_a_man() -> None:
    params = load_params(overrides={**SMALL, 'units.band.people.birth.conceive_per_day': 1.0})
    women = bands.Band(id=1, x=WEST, y=NORTH, members=bands.adults(3)[0::2])
    hungry = bands.Band(id=1, x=WEST, y=NORTH, members=bands.adults(4))

    bands.live(params, women, 10, 1.0, True, 0.0, dice())
    bands.live(params, hungry, 10, 1.0, bands.fed(params, hungry), 0.0, dice())

    assert [member.pregnant_until for member in women.members + hungry.members] == [None] * 6


def test_a_band_that_falls_below_its_least_dies_and_the_game_is_over() -> None:
    game = land(needing(forage=0.0))

    for _ in range(12 * DAY):
        last = do(game, camp())
        if game.over:
            break
    after = game.step()

    assert told(last)[-1] == ('band-died', {})
    assert (last.changes['units'], last.changes['gone'], last.units) == ([], [1], [])
    assert (game.over, game.outcome, game.band) == (True, 'died', None)
    assert (after.changes['gone'], counted(game)['population'], game.snapshot()['units']) == ([], 0, [])
    assert Game.restore(carried(game)).outcome == 'died'


def test_a_tick_carries_the_row_of_the_band(params: Params) -> None:
    game = land(params)

    result = do(game, gathering({'forage': 1.0}))

    assert game.unit_columns == ('id', 'x', 'y', 'state', 'action', 'people', 'food', 'water')
    assert result.units == [[1, WEST, NORTH + 1, 'normal', 'gather', 15, pytest.approx(51.0), 15.0]]
    assert counted(game) == pytest.approx(
        {
            'commands_accepted': 0,
            'commands_refused': 0,
            'cells_depleted': 1,
            'population': 15,
            'food': 51.0,
            'water': 15.0,
            'moves': 0,
            'roams': 0,
            'gathers': 1,
            'camps': 0,
            'builds': 0,
            'deaths': 0,
            'encounters': 0,
            'status': 50.0,
            'councils': 0,
            'child': 0,
            'adult': 15,
            'elder': 0,
            'pregnant': 0,
            'injured': 0,
            'skills': 0,
            'hunters': 0,
            'sick': 0,
        }
    )


def test_a_restored_game_carries_the_band_in_the_middle_of_a_day(params: Params) -> None:
    game = land(params)
    band(game).members[1].wound = {'severity': 'light', 'left': 3.5}
    band(game).changed()
    do(game, gathering({'forage': 1.0}), 2)
    do(game, moving('north-east'))
    do(game, camp(), 4)

    copy = Game.restore(carried(game))
    copy.choose = game.choose

    assert copy.state_hash() == game.state_hash()
    assert band(copy).plain() == json.loads(json.dumps(band(game).plain()))
    assert [copy.step().hash for _ in range(3 * DAY)] == [game.step().hash for _ in range(3 * DAY)]


def test_a_snapshot_of_the_format_before_the_band_is_refused(params: Params) -> None:
    snapshot = land(params).snapshot()

    assert snapshot["format"] == 27
    with pytest.raises(ValueError, match='format 2'):
        Game.restore({**snapshot, 'format': 2})


@pytest.mark.parametrize(('parts', 'pace'), [(SUMMER, 1.0), (WINTER, 0.25)])
def test_food_grows_back_slower_in_winter(params: Params, parts: int, pace: float) -> None:
    game = land(params, at=None, parts=parts)
    game.deplete(*FOREST, 'food', 0.5)
    game.deplete(*FOREST, 'water', 0.5)

    game.step()

    assert game.cells.stock(FOREST, 'food') == pytest.approx(0.5 + pace / (30 * DAY))
    assert game.cells.stock(FOREST, 'water') == pytest.approx(0.5 + 1 / (3 * DAY))


def built(game: Game, at: tuple[int, int] = HOME) -> None:
    band(game).camp = {'x': at[0], 'y': at[1], 'built': 1.0}


def test_a_winter_camp_is_built_in_two_days_of_work_without_gathering(params: Params) -> None:
    game = land(params)

    do(game, bands.building(), 2 * DAY - 1)
    unfinished = (dict(band(game).camp or {}), bands.sheltered(band(game)))
    last = do(game, bands.building())

    assert unfinished == ({'x': WEST, 'y': NORTH + 1, 'built': pytest.approx(0.9)}, False)
    assert band(game).camp == {'x': WEST, 'y': NORTH + 1, 'built': 1.0}
    assert bands.sheltered(band(game))
    assert last.units[0][4] == 'build'
    assert counted(game)['builds'] == 2 * DAY
    assert game.cells.stock(HOME, 'food') == 1.0


def test_a_band_in_its_winter_camp_eats_less_and_its_stores_spoil_slower(params: Params) -> None:
    stores = Stock({'forage': [[0.0, 20.0]], 'water': [[0.0, 20.0]]})
    held = bands.Band(id=1, x=WEST, y=NORTH, members=bands.adults(10), stores=stores)
    held.camp = {'x': WEST, 'y': NORTH, 'built': 1.0}

    bands.eat(params, held)
    days = bands.held_days(params, held, 'food')
    bands.spoil(params, held, 5)
    kept = held.plain()['stores']
    bands.spoil(params, held, 6)

    assert kept == {'forage': [[0.0, 12.0]], 'water': [[0.0, 12.0]]}
    assert held.plain()['stores'] == {'forage': [], 'water': [[0.0, 12.0]]}
    assert days == pytest.approx(12.0 / 8.0)


def test_a_band_in_its_winter_camp_rests_deeper_and_meets_less_threat(params: Params) -> None:
    game = land(params)
    built(game)
    band(game).fatigue = 0.6

    do(game, camp())

    assert band(game).fatigue == pytest.approx(0.6 - 0.3 * 1.5)
    assert game._threat(band(game)) == pytest.approx(game.value('threat', *HOME) * 0.5)


def test_a_band_that_leaves_its_cell_loses_its_winter_camp_and_builds_anew_elsewhere(params: Params) -> None:
    game = land(params)
    built(game)

    do(game, moving('east'))
    left = band(game).camp
    built(game, HOME)
    do(game, bands.building())

    assert (band(game).place, left) == (MEADOW, None)
    assert band(game).camp == {'x': WEST + 1, 'y': NORTH + 1, 'built': pytest.approx(0.1)}
    assert not bands.sheltered(band(game))


def test_a_winter_camp_is_carried_by_the_snapshot(params: Params) -> None:
    game = land(params)
    do(game, bands.building(), 3)

    copy = Game.restore(carried(game))

    assert band(copy).camp == band(game).camp
    assert copy.state_hash() == game.state_hash()


def gathered(game: Game) -> float:
    before = band(game).held('forage')
    do(game, gathering({'forage': 1.0}))
    return band(game).held('forage') - before


def test_a_band_around_its_winter_camp_gathers_the_richest_cell_in_reach(params: Params) -> None:
    alone, ranging = land(params), land(params)
    for game in (alone, ranging):
        game.cells.lower(HOME, 'food', 0.9)
    band(ranging).camp = {'x': WEST, 'y': NORTH + 1, 'built': 0.0}

    taken = gathered(alone), gathered(ranging)
    near = [at for at in bands.around(HOME, 1) if alone.inside(*at)]

    assert alone.cells.stock(HOME, 'food') < 0.1
    assert all(alone.cells.stock(at, 'food') == 1.0 for at in near)
    assert ranging.cells.stock(HOME, 'food') == pytest.approx(0.1, abs=0.01)
    assert any(ranging.cells.stock(at, 'food') < 1.0 for at in near)
    assert taken[1] > taken[0]


def test_a_cell_away_from_the_camp_gives_afar_of_a_gathering() -> None:
    taken = []
    for afar in (1.0, 0.5):
        game = land(load_params(overrides={**SMALL, 'units.band.winter_camp.afar': afar}))
        game.cells.lower(HOME, 'food', 0.9)
        band(game).camp = {'x': WEST, 'y': NORTH + 1, 'built': 0.0}
        taken.append(gathered(game))

    assert taken[1] == pytest.approx(taken[0] * 0.5)


def test_the_cells_in_reach_are_the_rings_around_a_place() -> None:
    assert bands.around((5, 5), 0) == []
    assert bands.around((5, 5), 1) == [(5, 4), (6, 4), (6, 5), (6, 6), (5, 6), (4, 6), (4, 5), (4, 4)]
    assert len(bands.around((5, 5), 2)) == 24


def test_gatherers_split_between_resources_take_a_share_of_each(params: Params) -> None:
    alone, shared = land(params), land(params)
    before = band(alone).held('forage'), band(alone).held('water')

    do(alone, gathering({'forage': 1.0}))
    do(shared, gathering({'forage': 0.5, 'water': 0.5}))
    forage = band(alone).held('forage') - before[0]

    assert band(shared).action == {'kind': 'gather', 'shares': {'forage': 0.5, 'water': 0.5}}
    assert band(shared).held('forage') - before[0] == pytest.approx(forage / 2)
    assert band(shared).held('water') > before[1]


def test_a_nanny_cares_for_every_five_children_and_gathers_half(params: Params) -> None:
    women = [bands.Member(1000, 'female'), bands.Member(1200, 'female'), bands.Member(900, 'female')]
    women[2].pregnant_until = 50
    children = [bands.Member(100, 'male') for _ in range(6)]
    held = bands.Band(id=1, x=WEST, y=NORTH, members=[*bands.adults(1), *women, *children])

    bands.assign(params, held)

    assert [member.role for member in held.members[:4]] == ['gatherer', 'gatherer', 'nanny', 'nanny']
    assert bands.roles(params, held) == {'gatherer': 8, 'nanny': 2, 'hunter': 0}
    assert bands.census(params, held).gatherers == pytest.approx(3.0)


def test_the_first_nanny_is_a_woman_the_second_an_elder_and_elders_gather_but_do_not_pull(params: Params) -> None:
    elder = bands.Member(bands.bounds(params, 'adult')[1] + 10, 'male')
    women = [bands.Member(1000, 'female'), bands.Member(1200, 'female')]
    children = [bands.Member(100, 'male') for _ in range(6)]
    held = bands.Band(id=1, x=WEST, y=NORTH, members=[*bands.adults(1), elder, *women, *children])

    bands.assign(params, held)

    assert [member.role for member in held.members[:4]] == ['gatherer', 'nanny', 'gatherer', 'nanny']
    assert bands.census(params, held).gatherers == pytest.approx(1.0 + 0.4 * 0.5 + 1.0 + 0.5)
    working = bands.Band(id=1, x=WEST, y=NORTH, members=[*bands.adults(1), elder])
    bands.assign(params, working)
    assert bands.census(params, working).gatherers == pytest.approx(1.4)
    assert bands.eligible(params, working, 'puller') == [0]


def test_nannies_leave_the_children_one_a_day_while_someone_goes_short(params: Params) -> None:
    women = [bands.Member(1000, 'female'), bands.Member(1200, 'female'), bands.Member(900, 'female')]
    women[2].pregnant_until = 50
    children = [bands.Member(100, 'male') for _ in range(6)]
    children[0].hungry = 0.5
    held = bands.Band(id=1, x=WEST, y=NORTH, members=[*bands.adults(1), *women, *children])
    freed = []

    for _ in range(3):
        bands.free(params, held)
        bands.assign(params, held)
        freed.append((held.freed, [member.role for member in held.members[1:4]]))
    children[0].hungry = 0.0
    bands.free(params, held)
    stayed = held.freed
    held.stores = Stock({'forage': [[0.0, 1000.0]], 'water': [[0.0, 1000.0]]})
    bands.free(params, held)
    bands.assign(params, held)

    assert freed == [
        (1, ['gatherer', 'gatherer', 'nanny']),
        (2, ['gatherer', 'gatherer', 'gatherer']),
        (2, ['gatherer', 'gatherer', 'gatherer']),
    ]
    assert stayed == 2
    assert held.freed == 1
    assert [member.role for member in held.members[1:4]] == ['gatherer', 'gatherer', 'nanny']
