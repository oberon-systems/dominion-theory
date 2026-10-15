import json
from typing import Any

import numpy as np
import pytest

from dominion_theory.content import Params, load_params
from dominion_theory.engine import PHASES, Command, Game, Pass, StepResult, Vote, Window
from dominion_theory.engine.clock import DAY_STARTED, MONTH_STARTED, SEASON_STARTED, YEAR_STARTED, Date
from dominion_theory.engine.game import _Tick
from dominion_theory.planet import Planet, place

SMALL = {'planet.circumference_km': 4000, 'planet.window.width': 32, 'planet.window.height': 16}
TICKS = 300


def hashes(game: Game, ticks: int = TICKS) -> list[str]:
    found = []
    for tick in range(ticks):
        if tick % 7 == 0:
            game.submit(Pass(seat='player'))
        found.append(game.step().hash)
    return found


def verdicts(result: StepResult) -> list[dict[str, Any]]:
    return [event.data() for event in result.events if event.key.startswith('command-')]


def test_overview_example_runs_as_written() -> None:
    params = load_params()

    game = Game.create(seed=42, params=params)
    game.submit(Vote(seat='player', proposal='rest'))
    result = game.step()
    copy = Game.restore(game.snapshot())

    assert [event.key for event in result.events] == ['command-refused']
    assert result.changes.keys() == {'units', 'gone', 'cells', 'known', 'seat'}
    assert (result.counters[:2], result.counters[3]) == ([0, 1], 15)
    assert copy.state_hash() == game.state_hash() == result.hash


def test_world_is_the_window_and_its_biomes(params: Params) -> None:
    game = Game.create(seed=3, params=params)

    x, y = place(3, params)
    region = Planet(3, params).read(x, y, 32, 16, params.eras.band.cell_km)

    assert game.window == Window(scale=0, x=x, y=y, width=32, height=16)
    assert game.window == Game.create(seed=3, params=params).window
    assert game.biomes.dtype == np.uint8
    assert game.rivers.dtype == np.bool_
    assert np.array_equal(game.biomes, region.biomes)
    assert np.array_equal(game.rivers, region.rivers)
    assert game.date == Date(1, 1, 1, 'morning', 'spring')


def test_window_given_by_hand_is_used() -> None:
    given = load_params(overrides={**SMALL, 'planet.window.x': 100, 'planet.window.y': 50})

    assert Game.create(seed=3, params=given).window == Window(scale=0, x=100, y=50, width=32, height=16)


def test_same_seed_gives_the_same_hash_after_every_tick(params: Params) -> None:
    first = hashes(Game.create(seed=7, params=params))

    assert first == hashes(Game.create(seed=7, params=params))
    assert len(set(first)) == TICKS


def test_other_seed_gives_other_hashes(params: Params) -> None:
    assert not set(hashes(Game.create(seed=7, params=params), 5)) & set(hashes(Game.create(seed=8, params=params), 5))


def test_other_parameters_give_other_hashes(params: Params) -> None:
    other = load_params(overrides={**SMALL, 'time.days_per_month': 12})

    assert Game.create(seed=7, params=params).state_hash() != Game.create(seed=7, params=other).state_hash()


def test_restored_game_steps_as_the_original(params: Params) -> None:
    game = Game.create(seed=11, params=params)
    hashes(game, 23)
    game.submit(Pass(seat='player', id='c-held'))
    game.submit(Command(seat='player', kind='dance', id='c-odd', fields={'steps': 3}))

    copy = Game.restore(game.snapshot())

    assert verdicts(copy.step()) == verdicts(game.step())
    assert hashes(copy, 40) == hashes(game, 40)


def test_snapshot_is_plain_data_and_arrays(params: Params) -> None:
    game = Game.create(seed=11, params=params)
    game.submit(Pass(seat='player'))
    snapshot = game.snapshot()
    grids = snapshot.pop('grids')

    carried = json.loads(json.dumps(snapshot))
    carried['grids'] = {name: grid.tolist() for name, grid in grids.items()}

    assert all(isinstance(grid, np.ndarray) for grid in grids.values())
    assert hashes(Game.restore(carried), 10) == hashes(game, 10)


def test_snapshot_does_not_share_its_arrays(params: Params) -> None:
    game = Game.create(seed=11, params=params)
    before = game.state_hash()

    for grid in game.snapshot()['grids'].values():
        grid[:] = grid == 0

    assert game.state_hash() == before


def test_unreadable_snapshot_is_refused(params: Params) -> None:
    snapshot = Game.create(seed=11, params=params).snapshot()

    assert snapshot['format'] == 6
    with pytest.raises(ValueError, match='format 1'):
        Game.restore({**snapshot, 'format': 1})


def test_pass_is_accepted(params: Params) -> None:
    game = Game.create(seed=1, params=params)
    game.submit(Pass(seat='player', id='c-1'))

    result = game.step()

    assert verdicts(result) == [{'key': 'command-accepted', 'values': {'id': 'c-1'}}]
    assert verdicts(game.step()) == []


def test_repeated_command_id_is_judged_once(params: Params) -> None:
    game = Game.create(seed=1, params=params)
    game.submit(Pass(seat='player', id='c-1'))
    game.submit(Pass(seat='player', id='c-1'))

    first = game.step()
    game.submit(Pass(seat='player', id='c-1'))

    assert len(verdicts(first)) == 1
    assert verdicts(game.step()) == []
    assert game.counters.names == (
        'commands_accepted',
        'commands_refused',
        'cells_depleted',
        'population',
        'food',
        'water',
        'moves',
        'roams',
        'gathers',
        'camps',
        'deaths',
        'encounters',
        'status',
        'councils',
    )
    assert game.counters.row()[:2] == [1, 0]


def test_unknown_kind_is_refused_with_a_reason(params: Params) -> None:
    game = Game.create(seed=1, params=params)
    game.submit(Command.read('player', {'id': 'c-2', 'kind': 'dance', 'steps': 3}))

    assert verdicts(game.step()) == [
        {'key': 'command-refused', 'values': {'id': 'c-2', 'reason': 'refused-unknown-command'}},
    ]


def test_unknown_seat_is_refused(params: Params) -> None:
    game = Game.create(seed=1, params=params)
    game.submit(Pass(seat='alpha', id='c-3'))

    assert verdicts(game.step()) == [
        {'key': 'command-refused', 'values': {'id': 'c-3', 'reason': 'refused-unknown-seat'}},
    ]


def test_commands_are_judged_by_seat_then_in_the_order_sent(params: Params) -> None:
    game = Game.create(seed=1, params=params)
    for seat, name in [('player', 'c-b'), ('alpha', 'c-z'), ('player', 'c-a'), ('player', None)]:
        game.submit(Pass(seat=seat, id=name))

    assert [verdict['values']['id'] for verdict in verdicts(game.step())] == ['c-z', 'c-b', 'c-a', 'player-3']


def test_boundary_events_come_in_the_documented_order(params: Params) -> None:
    game = Game.create(seed=1, params=params)
    results = [game.step() for _ in range(500)]

    assert [result.events for result in results[:4]] == [[], [], [], []]
    assert [event.data() for event in results[4].events] == [
        {'key': DAY_STARTED, 'values': {'year': 1, 'month': 1, 'day': 2}},
    ]
    assert [event.key for event in results[99].events] == [DAY_STARTED, MONTH_STARTED, SEASON_STARTED]
    assert [event.data() for event in results[499].events] == [
        {'key': DAY_STARTED, 'values': {'year': 2, 'month': 1, 'day': 1}},
        {'key': MONTH_STARTED, 'values': {'year': 2, 'month': 1, 'season': 'spring'}},
        {'key': SEASON_STARTED, 'values': {'year': 2, 'season': 'spring'}},
        {'key': YEAR_STARTED, 'values': {'year': 2, 'seasons': game.clock.schedule(2).plan()}},
    ]
    assert (results[499].tick, results[499].parts, results[499].date) == (500, 500, Date(2, 1, 1, 'morning', 'spring'))


def test_verdicts_come_before_the_boundaries(params: Params) -> None:
    game = Game.create(seed=1, params=params)
    for _ in range(4):
        game.step()
    game.submit(Pass(seat='player', id='c-1'))

    assert [event.key for event in game.step().events] == ['command-accepted', DAY_STARTED]


def test_phases_run_in_the_documented_order(params: Params, monkeypatch: pytest.MonkeyPatch) -> None:
    ran: list[str] = []

    def watched(name: str) -> None:
        phase = getattr(Game, f'_{name}')

        def run(game: Game, tick: _Tick) -> None:
            ran.append(name)
            phase(game, tick)

        monkeypatch.setattr(Game, f'_{name}', run)

    for name in PHASES:
        watched(name)
    Game.create(seed=1, params=params).step()

    assert PHASES == ('commands', 'councils', 'decisions', 'actions', 'world', 'calendar', 'report')
    assert ran == list(PHASES)
