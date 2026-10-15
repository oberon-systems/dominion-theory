from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient

from dominion_theory.api import PREFIX
from dominion_theory.api.commands import read_command
from dominion_theory.core.errors import DominionError
from dominion_theory.engine.band import DIRECTIONS

from .conftest import SMALL

type NewGame = Callable[..., dict[str, Any]]

EVENING = 3

STAY = {'id': 'c-1', 'kind': 'vote', 'proposal': {'kind': 'stay-and-gather'}}
MALFORMED: list[dict[str, Any]] = [
    {'kind': 'pass'},
    {'id': '', 'kind': 'pass'},
    {'id': 7, 'kind': 'pass'},
    {'id': 'c-1'},
    {'id': 'c-1', 'kind': 'alpha'},
    {'id': 'c-1', 'kind': ['pass']},
    {'id': 'c-1', 'kind': 'pass', 'proposal': {'kind': 'stay-and-gather'}},
    {'id': 'c-1', 'kind': 'vote'},
    {'id': 'c-1', 'kind': 'vote', 'proposal': 'stay-and-gather'},
    {'id': 'c-1', 'kind': 'vote', 'proposal': {'kind': 'rest'}},
    {'id': 'c-1', 'kind': 'vote', 'proposal': {'kind': 'alpha'}},
    {'id': 'c-1', 'kind': 'vote', 'proposal': {'kind': 'move'}},
    {'id': 'c-1', 'kind': 'vote', 'proposal': {'kind': 'move', 'towards': 'up'}},
    {'id': 'c-1', 'kind': 'vote', 'proposal': {'kind': 'move', 'towards': ['east']}},
    {'id': 'c-1', 'kind': 'vote', 'proposal': {'kind': 'stay-and-gather', 'towards': 'east'}},
    {'id': 'c-1', 'kind': 'vote', 'proposal': {'kind': 'abstain', 'towards': 'east'}},
    {**STAY, 'unit': 1},
]


@pytest.mark.parametrize('envelope', MALFORMED)
def test_a_malformed_command_is_refused(envelope: dict[str, Any]) -> None:
    with pytest.raises(DominionError) as raised:
        read_command('player', envelope)

    assert raised.value.message() == {'key': 'error-command-invalid', 'values': {}}


@pytest.mark.parametrize(
    'envelope',
    [
        {'id': 'c-1', 'kind': 'pass'},
        STAY,
        {'id': 'c-1', 'kind': 'vote', 'proposal': {'kind': 'abstain'}},
        *({'id': 'c-1', 'kind': 'vote', 'proposal': {'kind': 'move', 'towards': way}} for way in DIRECTIONS),
    ],
)
def test_a_well_formed_command_is_read(envelope: dict[str, Any]) -> None:
    command = read_command('player', envelope)

    assert command.seat == 'player'
    assert command.envelope() == envelope


def test_a_pass_in_step_mode_advances_the_game_and_its_verdict_is_an_event(
    client: TestClient, new_game: NewGame
) -> None:
    game = new_game()['id']

    with client.websocket_connect(f'{PREFIX}/games/{game}/updates?after=0') as stream:
        answer = client.post(f'{PREFIX}/games/{game}/commands', json={'id': 'c-1', 'kind': 'pass'})
        update = stream.receive_json()

    assert answer.status_code == 200
    assert answer.json() == {'id': 'c-1', 'taken': True}
    assert update['seq'] == 1
    assert update['date']['part'] == 'midday'
    assert update['events'] == [{'key': 'command-accepted', 'values': {'id': 'c-1'}}]
    assert update['waiting'] == ['player']


def test_a_repeated_command_id_is_taken_once(client: TestClient, new_game: NewGame) -> None:
    game = new_game()['id']
    address = f'{PREFIX}/games/{game}/commands'

    answers = [client.post(address, json={'id': 'c-1', 'kind': 'pass'}) for _ in range(2)]

    assert [answer.json() for answer in answers] == [{'id': 'c-1', 'taken': True}] * 2
    assert client.get(f'{PREFIX}/games/{game}/snapshot').json()['seq'] == 1


def test_a_command_the_rules_refuse_is_not_an_error_of_the_api(client: TestClient, new_game: NewGame) -> None:
    game = new_game(seated=True, overrides={**SMALL, 'council.voice.least': 20.0})['id']

    nowhere = {'id': 'c-1', 'kind': 'vote', 'proposal': {'kind': 'move', 'towards': 'east'}}

    with client.websocket_connect(f'{PREFIX}/games/{game}/updates?after=0') as stream:
        for tick in range(EVENING):
            client.post(f'{PREFIX}/games/{game}/commands', json={'id': f'p-{tick}', 'kind': 'pass'})
        answer = client.post(f'{PREFIX}/games/{game}/commands', json=nowhere)
        update = [stream.receive_json() for _ in range(EVENING + 1)][-1]

    assert answer.json() == {'id': 'c-1', 'taken': True}
    assert update['events'][0] == {
        'key': 'command-refused',
        'values': {'id': 'c-1', 'reason': 'refused-no-such-direction'},
    }


def test_a_command_that_fails_its_check_is_422(client: TestClient, new_game: NewGame) -> None:
    game = new_game()['id']
    address = f'{PREFIX}/games/{game}/commands'

    malformed = client.post(address, json={'id': 'c-1', 'kind': 'alpha'})
    unreadable = client.post(address, json=['pass'])

    assert malformed.status_code == 422
    assert malformed.json() == {'key': 'error-command-invalid', 'values': {}}
    assert unreadable.status_code == 400
    assert client.get(f'{PREFIX}/games/{game}/snapshot').json()['seq'] == 0
