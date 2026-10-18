from pathlib import Path

import httpx
import pytest

from dominion_theory.client import PREFIX, Api, Refused
from dominion_theory.runner import read

SMALL = {'planet.circumference_km': 4000, 'planet.window.width': 32, 'planet.window.height': 16}
START = {'year': 1, 'month': 1, 'day': 1, 'part': 'morning', 'season': 'spring'}


def test_the_language_is_the_one_of_the_profile(api: Api) -> None:
    assert api.language() == 'en'


def test_a_game_is_created_and_read(api: Api) -> None:
    created = api.create('step', seed=42, preset='harsh-winter', overrides=SMALL)

    assert (created['seed'], created['mode'], created['running'], created['date']) == (42, 'step', False, START)
    assert api.game(created['id']) == created
    assert api.snapshot(created['id'])['waiting'] == ['player']


def test_what_is_left_out_of_a_new_game_is_not_sent(api: Api) -> None:
    created = api.create('real-time', overrides=SMALL)

    assert created['mode'] == 'real-time'


def test_the_stream_gives_what_followed_the_snapshot(api: Api) -> None:
    game = api.create('step', seed=42, overrides=SMALL)['id']
    seq = api.snapshot(game)['seq']
    assert api.command(game, {'id': 'c-1', 'kind': 'pass'}) == {'id': 'c-1', 'taken': True}
    api.clock(game, 'step')

    stream = api.updates(game, seq)
    first, second = next(stream), next(stream)
    stream.close()

    assert (seq, first['seq'], second['seq']) == (0, 1, 2)
    assert first['events'] == [{'key': 'command-accepted', 'values': {'id': 'c-1'}}]
    assert first['waiting'] == ['player']


def test_the_stream_stops_when_the_game_ends(api: Api, server: str) -> None:
    game = api.create('step', seed=42, overrides=SMALL)['id']
    stream = api.updates(game, 0)
    api.clock(game, 'step')
    assert next(stream)['seq'] == 1

    httpx.delete(f'{server}{PREFIX}/games/{game}').raise_for_status()

    assert list(stream) == []


def test_a_refused_request_is_raised_as_its_message(api: Api) -> None:
    with pytest.raises(Refused) as raised:
        api.game('alpha')

    assert (raised.value.key, raised.value.values) == ('error-game-not-found', {'id': 'alpha'})


def test_a_refused_stream_is_raised_as_its_message(api: Api) -> None:
    with pytest.raises(Refused) as raised:
        next(api.updates('alpha', 0))

    assert (raised.value.key, raised.value.values) == ('error-game-not-found', {'id': 'alpha'})


def test_the_record_is_downloaded_as_it_is_written(api: Api, tmp_path: Path) -> None:
    created = api.create('step', seed=7, overrides=SMALL)
    copy = tmp_path / 'alpha.jsonl.gz'

    copy.write_bytes(api.record(created['id']))

    assert [(line['t'], line['game'], line['seed']) for line in read(copy)] == [('header', created['id'], 7)]
