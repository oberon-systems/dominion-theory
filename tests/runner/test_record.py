import gzip
import json
from datetime import timedelta
from pathlib import Path
from typing import Any

import fakeredis
import pytest

from dominion_theory.content import load_params
from dominion_theory.core.errors import DominionError
from dominion_theory.core.settings import Settings
from dominion_theory.engine import CallCouncil, Pass
from dominion_theory.runner import RECORD_UNREADABLE, STEP, Runner, Service, read, replay
from dominion_theory.store import ValkeyStore

SMALL = {'planet.circumference_km': 4000, 'planet.window.width': 32, 'planet.window.height': 16}
DAY = 5


@pytest.fixture
def service(tmp_path: Path) -> Service:
    raw: Any = fakeredis.FakeValkey(server=fakeredis.FakeServer(server_type='valkey'))
    store = ValkeyStore(raw, timedelta(hours=2))
    return Service(store, Settings(records_dir=tmp_path))


def play(runner: Runner, ticks: int) -> list[str]:
    hashes = []
    for tick in range(ticks):
        if tick % 3 == 0:
            runner.submit(Pass(seat='player'))
        else:
            runner.step()
        hashes.append(runner.game.state_hash())
    return hashes


def test_the_record_lies_under_the_identifier_of_the_game(service: Service, tmp_path: Path) -> None:
    runner = service.create(seed=1, overrides=SMALL, mode=STEP)

    assert runner.record_path == tmp_path / f'{runner.id}.jsonl.gz'
    assert runner.record_path.exists()


def test_the_header_names_the_game_and_its_columns(service: Service) -> None:
    runner = service.create(seed=42, overrides=SMALL, mode=STEP, seats={'player': 'scripted'})

    (header,) = read(runner.record_path)

    assert header.pop('engine')
    assert header == {
        't': 'header',
        'format': 1,
        'game': runner.id,
        'seed': 42,
        'params_hash': runner.game.params.hash,
        'params': runner.game.params.tree(),
        'seats': [{'seat': 'player', 'kind': 'scripted'}],
        'counters': ['commands_accepted', 'commands_refused', 'cells_depleted'],
        'units': [],
    }


def test_a_seat_is_held_by_a_person_unless_said(service: Service) -> None:
    runner = service.create(seed=1, overrides=SMALL, mode=STEP)

    assert read(runner.record_path)[0]['seats'] == [{'seat': 'player', 'kind': 'person'}]


def test_a_tick_writes_its_commands_itself_and_its_events(service: Service) -> None:
    runner = service.create(seed=1, overrides=SMALL, mode=STEP)
    runner.submit(CallCouncil(seat='player', proposal='rest', id='c-1'))
    for _ in range(DAY - 1):
        runner.step()

    lines = read(runner.record_path)

    assert lines[1] == {
        't': 'command',
        'tick': 1,
        'seat': 'player',
        'seq': 1,
        'command': {'id': 'c-1', 'kind': 'call-council', 'proposal': 'rest'},
        'accepted': False,
    }
    assert lines[2]['t'] == 'tick'
    assert lines[2]['tick'] == lines[2]['parts'] == 1
    assert lines[2]['counters'] == [0, 1, 0]
    assert lines[2]['units'] == []
    assert lines[3] == {
        't': 'event',
        'tick': 1,
        'key': 'command-refused',
        'values': {'id': 'c-1', 'reason': 'refused-unknown-command'},
    }
    assert [line['tick'] for line in lines if line['t'] == 'tick'] == [1, 2, 3, 4, 5]
    assert lines[-1]['key'] == 'day-started'


def test_lines_are_written_at_the_end_of_a_day_as_a_member_of_their_own(service: Service) -> None:
    runner = service.create(seed=1, overrides=SMALL, mode=STEP)
    sizes = [runner.record_path.stat().st_size]
    for _ in range(2 * DAY + 2):
        runner.step()
        sizes.append(runner.record_path.stat().st_size)

    data = runner.record_path.read_bytes()

    assert len(set(sizes)) == 3
    assert sizes[DAY - 1] < sizes[DAY] == sizes[2 * DAY - 1] < sizes[2 * DAY] == sizes[-1]
    assert [data.startswith(b'\x1f\x8b', at) for at in (0, sizes[0], sizes[DAY])] == [True, True, True]
    assert gzip.decompress(data).count(b'\n') == len(read(runner.record_path))


def test_the_footer_says_how_the_game_ended(service: Service) -> None:
    runner = service.create(seed=1, overrides=SMALL, mode=STEP)
    play(runner, DAY + 2)

    ended = runner.end('alpha')
    lines = read(runner.record_path)

    assert lines[-1] == {'t': 'footer', 'outcome': 'alpha', 'tick': DAY + 2, 'hash': ended.hash}
    assert [line['tick'] for line in lines if line['t'] == 'tick'] == list(range(1, DAY + 3))


def test_the_replay_example_of_the_documents_runs_as_written(service: Service) -> None:
    runner = service.create(seed=7, preset='harsh-winter', overrides=SMALL, mode=STEP)
    hashes = play(runner, 4 * DAY + 3)
    runner.end()

    result = replay(str(runner.record_path))

    assert result.matched is True
    assert result.diverged_at is None
    assert result.game.tick == 4 * DAY + 3
    assert result.game.state_hash() == hashes[-1]
    assert result.game.params.hash == runner.game.params.hash


def test_a_record_cut_off_in_the_middle_of_a_day_replays_to_the_last_full_day(service: Service) -> None:
    runner = service.create(seed=7, overrides=SMALL, mode=STEP)
    hashes = play(runner, 3 * DAY)
    whole = runner.record_path.read_bytes()
    runner.record_path.write_bytes(whole[:-20])

    result = replay(runner.record_path)

    assert result.matched is True
    assert result.game.tick == 2 * DAY
    assert result.game.state_hash() == hashes[2 * DAY - 1]


def test_a_record_with_no_footer_replays_what_was_written(service: Service) -> None:
    runner = service.create(seed=7, overrides=SMALL, mode=STEP)
    play(runner, DAY + 3)

    result = replay(runner.record_path)

    assert result.matched is True
    assert result.game.tick == DAY


def test_a_changed_parameter_does_not_replay_against_the_defaults(service: Service) -> None:
    runner = service.create(seed=7, overrides={**SMALL, 'time.days_per_month': 9}, mode=STEP)
    play(runner, DAY + 1)
    runner.end()

    result = replay(runner.record_path, params=load_params(overrides=SMALL))

    assert result.matched is False
    assert result.diverged_at == 1
    assert result.game.tick == DAY + 1
    assert replay(runner.record_path).matched is True


def test_a_changed_hash_names_the_first_tick_that_differs(service: Service, tmp_path: Path) -> None:
    runner = service.create(seed=7, overrides=SMALL, mode=STEP)
    play(runner, DAY)
    lines = read(runner.record_path)
    next(line for line in lines if line['t'] == 'tick' and line['tick'] == 3)['hash'] = 'alpha'
    path = tmp_path / 'alpha.jsonl.gz'
    path.write_bytes(gzip.compress('\n'.join(json.dumps(line) for line in lines).encode()))

    result = replay(path)

    assert result.matched is False
    assert result.diverged_at == 3
    assert result.game.tick == DAY


def test_a_reader_skips_the_kinds_it_does_not_know(service: Service) -> None:
    runner = service.create(seed=7, overrides=SMALL, mode=STEP)
    play(runner, DAY)
    with runner.record_path.open('ab') as file:
        file.write(gzip.compress(b'{"t":"alpha","tick":5}\n'))

    assert replay(runner.record_path).matched is True


@pytest.mark.parametrize('content', [b'', b'alpha', gzip.compress(b'{"t":"tick","tick":1,"hash":"alpha"}\n')])
def test_a_file_that_is_no_record_is_refused(tmp_path: Path, content: bytes) -> None:
    path = tmp_path / 'alpha.jsonl.gz'
    path.write_bytes(content)

    with pytest.raises(DominionError) as error:
        replay(path)

    assert error.value.message() == {'key': RECORD_UNREADABLE, 'values': {'path': str(path)}}
