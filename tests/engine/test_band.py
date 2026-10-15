import json
from typing import Any

import numpy as np
import pytest

from dominion_theory.content import Params, load_params
from dominion_theory.engine import Game, StepResult, Window
from dominion_theory.engine import band as bands
from dominion_theory.engine.band import Action, camp, gathering, moving, roaming
from dominion_theory.engine.streams import Streams
from dominion_theory.planet import biome_names

# The band does what it is told in every part of the day; the camp of the evening and the night is tested alone.
SMALL = {
    'planet.circumference_km': 4000,
    'planet.window.width': 32,
    'planet.window.height': 16,
    'encounters.chance': 0.0,
    'units.band.camp_parts': [],
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
        result = game.step()
    return result


def band(game: Game) -> bands.Band:
    assert game.band is not None
    return game.band


def told(result: StepResult) -> list[tuple[str, dict[str, Any]]]:
    return [(event.key, event.values) for event in result.events if event.key not in CALENDAR]


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


def test_progress_is_lost_when_the_band_does_something_else(params: Params) -> None:
    game = land(params, at=MEADOW)

    do(game, moving('north'))
    do(game, camp())
    do(game, moving('north'))

    assert band(game).place == MEADOW
    assert band(game).progress == pytest.approx(PACE * 0.6)


def test_the_shallows_are_entered_at_the_shore_and_no_further() -> None:
    game = land(load_params(overrides={**SMALL, 'units.band.fatigue.move': 0.0}), at=MEADOW)

    do(game, moving('east'), 2)
    wading = band(game).place
    do(game, moving('east'))
    refused = do(game, moving('east'))

    assert wading == MEADOW
    assert band(game).place == SHORE
    assert band(game).action == {'kind': 'camp'}
    assert refused.changes['units'][0]['action'] == {'kind': 'camp'}
    assert [bands.enterable(game, *at) for at in (SHORE, DEEPER, (WEST + 4, NORTH))] == [True, False, False]
    assert counted(game)['camps'] == 1


def test_a_move_out_of_the_window_is_a_camp(params: Params) -> None:
    game = land(params)

    do(game, moving('west'))

    assert (band(game).place, band(game).action) == (HOME, {'kind': 'camp'})
    assert not bands.enterable(game, WEST - 1, NORTH + 1)


def test_gathering_fills_the_stores_and_empties_the_cell(params: Params) -> None:
    game = land(params)

    first = do(game, gathering('forage'))
    once = band(game).held('forage')
    do(game, gathering('water'))
    do(game, gathering('forage'))

    assert once == pytest.approx(15 + 15 * 3.0 * 0.8)
    assert band(game).held('water') == pytest.approx(15 + 15 * 4.0 * 0.4 * 0.7 * (1 - 0.5 * 0.1))
    assert band(game).held('forage') == pytest.approx(90 - band(game).held('water'))
    assert bands.room(params, band(game)) == pytest.approx(0.0)
    assert first.changes['units'][0]['action'] == {'kind': 'gather', 'resource': 'forage'}
    assert first.changes['units'][0]['place'] == {'scale': 0, 'x': WEST, 'y': NORTH + 1}
    assert first.changes['cells'][0]['food'] < 1.0
    assert counted(game)['gathers'] == 3


def test_a_cell_pays_the_share_of_its_capacity_that_was_taken(params: Params) -> None:
    game = land(params)

    do(game, gathering('forage'))

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

    do(game, gathering('forage'))

    assert bands.room(params, band(game)) == 0.0
    assert band(game).held('forage') == 15.0
    assert band(game).action == {'kind': 'gather', 'resource': 'forage'}
    assert len(game.cells) == 0


def test_water_that_does_not_run_out_keeps_no_cell(params: Params) -> None:
    game = land(params, at=SHORE)

    do(game, gathering('water'))

    assert band(game).held('water') == pytest.approx(15 + 60)
    assert len(game.cells) == 0


def test_fatigue_grows_with_work_and_falls_in_camp(params: Params) -> None:
    game = land(params)

    do(game, moving('east'))
    do(game, gathering('forage'))
    worked = band(game).fatigue
    do(game, camp())

    assert worked == pytest.approx(0.3 + 0.1)
    assert band(game).fatigue == pytest.approx(0.1)


def test_the_band_camps_in_the_evening_and_the_night_whatever_it_wants() -> None:
    game = land(load_params(overrides={**SMALL, 'units.band.camp_parts': ['evening', 'night']}))
    game.choose = lambda _game, _band: gathering('forage')

    kinds = [game.step().units[0][4] for _ in range(DAY)]

    assert kinds == ['gather', 'gather', 'gather', 'camp', 'camp']
    assert band(game).reason == {'action': 'camp', 'need': 'rest', 'score': 0.0, 'pull': None}


def test_fatigue_slows_the_pace_and_tiredness_begins_and_ends_in_camp(params: Params) -> None:
    game = land(params)
    before = [do(game, moving(towards)) for towards in ('east', 'west')]
    began = do(game, moving('east'))
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
        'seen': 20,
    }


def test_news_of_the_land_come_with_the_tick_and_old_memories_go(params: Params) -> None:
    game = land(params)
    band(game).known[WEST + 4, NORTH] = {'biome': 'water', 'river': False, 'seen': -1}

    quiet = do(game, camp())
    gathered = do(game, gathering('forage'))
    walked = do(game, moving('east'))

    assert quiet.changes['known'] == []
    assert (WEST + 4, NORTH) not in band(game).known
    assert [(cell['x'], cell['y']) for cell in gathered.changes['known']] == [HOME]
    assert gathered.changes['known'][0]['food'] == pytest.approx(0.8 * 0.64)
    assert {(cell['x'], cell['y']) for cell in walked.changes['known']} == {HOME, (WEST + 3, NORTH), DEEPER}


def test_a_lot_is_thrown_away_when_its_time_is_over(params: Params) -> None:
    stores = {'forage': [[0.0, 5.0], [2.0, 7.0]], 'water': [[0.0, 9.0]]}
    held = bands.Band(id=1, x=WEST, y=NORTH, members=bands.adults(15), stores=stores)

    bands.spoil(params, held, 3)
    after_three = held.plain()['stores']
    bands.spoil(params, held, 5)

    assert after_three == {'forage': [[2.0, 7.0]], 'water': [[0.0, 9.0]]}
    assert held.plain()['stores'] == {'forage': [], 'water': []}


def test_people_eat_the_oldest_lot_first(params: Params) -> None:
    stores = {'forage': [[0.0, 4.0], [1.0, 9.0]], 'water': [[1.0, 5.0]]}
    held = bands.Band(id=1, x=WEST, y=NORTH, members=bands.adults(10), stores=stores)

    met = bands.eat(params, held)

    assert held.stores == {'forage': [[1.0, 3.0]], 'water': []}
    assert met == {'forage': 1.0, 'water': 0.5}


def test_a_band_with_no_food_starves_on_the_day_its_document_says() -> None:
    game = land(needing(water=0.0))

    fed = told(do(game, camp(), DAY))
    short = told(do(game, camp(), DAY))
    began = told(do(game, camp(), DAY))
    held = told(do(game, camp(), DAY))
    band(game).stores['forage'] = [[float(game.day), 30.0]]
    ended = told(do(game, camp(), DAY))

    assert (fed, short) == ([], [])
    assert began == [
        ('band-state-began', {'state': 'state-starvation'}),
        ('people-lost', {'count': 1, 'cause': 'hunger'}),
    ]
    assert held == [('people-lost', {'count': 1, 'cause': 'hunger'})]
    assert ended == [('band-state-ended', {'state': 'state-starvation'})]
    assert (band(game).population, band(game).states, counted(game)['deaths']) == (13, [], 2)


def test_a_band_with_no_water_thirsts_a_day_sooner_and_loses_more() -> None:
    game = land(needing(forage=0.0))

    fed = told(do(game, camp(), DAY))
    began = told(do(game, camp(), DAY))

    assert fed == []
    assert began == [
        ('band-state-began', {'state': 'state-thirst'}),
        ('people-lost', {'count': 3, 'cause': 'thirst'}),
    ]
    assert (band(game).population, band(game).states) == (12, ['thirst'])


def test_a_created_band_is_of_adults_of_random_age_and_sex_the_first_the_player(params: Params) -> None:
    members = band(Game.create(seed=7, params=params)).members

    assert all(400 <= member.age_days < 1700 for member in members)
    assert {member.sex for member in members} == {'female', 'male'}
    assert [member.player for member in members] == [True] + [False] * 14


def test_children_and_elders_gather_nothing_eat_less_and_walk_slower(params: Params) -> None:
    members = [*bands.adults(2), bands.Member(0, 'male'), bands.Member(1800, 'female')]
    held = bands.Band(id=1, x=WEST, y=NORTH, members=members, stores={})
    held.members[1].injured_until = 9

    counted = bands.census(params, held)

    assert counted.counts == {'child': 1, 'adult': 2, 'elder': 1}
    assert (counted.gatherers, counted.eaters, counted.carriers) == pytest.approx((1.2, 3.2, 2.75))
    assert counted.pace == pytest.approx((1.0 + 0.4 + 0.7 + 0.8) / 4)
    assert (counted.voters, counted.injured, counted.pregnant) == (3, 1, 0)


def test_the_dead_are_drawn_from_the_exposed_and_never_the_player(params: Params) -> None:
    held = bands.Band(id=1, x=WEST, y=NORTH, members=[*bands.adults(1), bands.Member(0, 'female')], stores={})

    lost, injured = bands.struck(params, held, 1.0, 0.0, 0, np.random.default_rng(7))

    assert (lost, injured, held.population, held.members[0].player) == (1, 0, 1, True)
    assert bands.vulnerable(params, held, 'thirst') == [0.0]


def test_the_old_and_the_frail_die_and_the_hurt_are_injured_while_the_player_lives() -> None:
    ageing = {'units.band.people.age.per_year': 0.5, 'units.band.people.injury.per_day': 0.5}
    params = load_params(overrides={**SMALL, **ageing})
    held = bands.Band(id=1, x=WEST, y=NORTH, members=[*bands.adults(2, 2000), bands.Member(0, 'female')], stores={})

    lived = bands.live(params, held, 10, 0.5, False, dice())

    assert lived.lost == [('age', 1), ('frailty', 1)]
    assert (held.population, held.members[0].player, held.members[0].age_days) == (1, True, 2001)
    assert (lived.injured, held.members[0].injured_until) == (1, 30)


def test_a_fed_band_conceives_and_gives_birth_with_a_pause_after() -> None:
    params = load_params(overrides={**SMALL, 'units.band.people.birth.conceive_per_day': 1.0})
    held = bands.Band(id=1, x=WEST, y=NORTH, members=bands.adults(4), stores={})

    bands.live(params, held, 10, 1.0, True, dice())
    pregnant = [member.pregnant_until for member in held.members]
    held.members[0].pregnant_until = held.members[2].pregnant_until = 11
    born = bands.live(params, held, 11, 1.0, True, dice())

    assert pregnant == [40, None, 40, None]
    assert (born.born, born.lost, held.population) == (2, [('birth', 1)], 5)
    assert (held.members[-1].age_days, held.members[0].rest_until) == (0, 21)


def test_nobody_conceives_in_a_hungry_band_or_one_without_a_man() -> None:
    params = load_params(overrides={**SMALL, 'units.band.people.birth.conceive_per_day': 1.0})
    women = bands.Band(id=1, x=WEST, y=NORTH, members=bands.adults(3)[0::2], stores={})
    hungry = bands.Band(id=1, x=WEST, y=NORTH, members=bands.adults(4), stores={})

    bands.live(params, women, 10, 1.0, True, dice())
    bands.live(params, hungry, 10, 1.0, bands.fed(params, hungry), dice())

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

    result = do(game, gathering('forage'))

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
            'deaths': 0,
            'encounters': 0,
            'status': 50.0,
            'councils': 0,
            'child': 0,
            'adult': 15,
            'elder': 0,
            'pregnant': 0,
            'injured': 0,
        }
    )


def test_a_restored_game_carries_the_band_in_the_middle_of_a_day(params: Params) -> None:
    game = land(params)
    do(game, gathering('forage'), 2)
    do(game, moving('north-east'))
    do(game, camp(), 4)

    copy = Game.restore(carried(game))
    copy.choose = game.choose

    assert copy.state_hash() == game.state_hash()
    assert band(copy).plain() == json.loads(json.dumps(band(game).plain()))
    assert [copy.step().hash for _ in range(3 * DAY)] == [game.step().hash for _ in range(3 * DAY)]


def test_a_snapshot_of_the_format_before_the_band_is_refused(params: Params) -> None:
    snapshot = land(params).snapshot()

    assert snapshot['format'] == 9
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
