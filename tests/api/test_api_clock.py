import time
from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient

from dominion_theory.api import PREFIX

type NewGame = Callable[..., dict[str, Any]]


def clock(client: TestClient, game: str, **asked: Any) -> Any:
    return client.post(f'{PREFIX}/games/{game}/clock', json=asked)


def test_the_clock_resumes_and_pauses(client: TestClient, new_game: NewGame) -> None:
    game = new_game(mode='real-time')['id']

    with client.websocket_connect(f'{PREFIX}/games/{game}/updates?after=0') as stream:
        resumed = clock(client, game, action='resume')
        seen = [stream.receive_json()['seq'] for _ in range(3)]
        paused = clock(client, game, action='pause')
    stopped = client.get(f'{PREFIX}/games/{game}/snapshot').json()['seq']
    time.sleep(0.05)

    assert resumed.json()['running'] is True
    assert seen == [1, 2, 3]
    assert paused.json()['running'] is False
    assert client.get(f'{PREFIX}/games/{game}/snapshot').json()['seq'] == stopped
    assert client.get(f'{PREFIX}/games/{game}').json()['running'] is False


def test_a_running_game_is_not_stepped(client: TestClient, new_game: NewGame) -> None:
    game = new_game(mode='real-time')['id']
    clock(client, game, action='resume')

    refused = clock(client, game, action='step')
    clock(client, game, action='pause')
    stepped = clock(client, game, action='step')

    assert refused.status_code == 409
    assert refused.json() == {'key': 'error-clock-running', 'values': {'id': game}}
    assert stepped.status_code == 200


def test_a_step_advances_once(client: TestClient, new_game: NewGame) -> None:
    game = new_game()['id']

    stepped = clock(client, game, action='step')

    assert stepped.json()['date']['part'] == 'midday'
    assert client.get(f'{PREFIX}/games/{game}/snapshot').json()['seq'] == 1


def test_the_speed_is_a_multiplier_above_zero(client: TestClient, new_game: NewGame) -> None:
    game = new_game(mode='real-time')['id']

    assert clock(client, game, action='speed', value=2).status_code == 200
    assert clock(client, game, action='speed', value=0).status_code == 400
    assert clock(client, game, action='speed').status_code == 400


@pytest.mark.parametrize('asked', [{'action': 'alpha'}, {}, {'action': 'pause', 'speed': 2}])
def test_a_clock_request_that_cannot_be_read_is_400(
    client: TestClient, new_game: NewGame, asked: dict[str, Any]
) -> None:
    answer = clock(client, new_game()['id'], **asked)

    assert answer.status_code == 400
    assert answer.json() == {'key': 'error-request-unreadable', 'values': {}}


def test_the_clock_leaves_no_trace_in_the_game(client: TestClient, new_game: NewGame) -> None:
    game = new_game()['id']

    with client.websocket_connect(f'{PREFIX}/games/{game}/updates?after=0') as stream:
        clock(client, game, action='pause')
        clock(client, game, action='resume')
        clock(client, game, action='step')
        update = stream.receive_json()

    assert update['seq'] == 1
    assert update['events'] == []
