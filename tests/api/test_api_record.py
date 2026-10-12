from collections.abc import Callable
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from dominion_theory.api import PREFIX
from dominion_theory.core.settings import Settings
from dominion_theory.runner import read, record_path, replay

type NewGame = Callable[..., dict[str, Any]]

TICKS = 12


def test_the_record_downloads_and_replays_with_every_hash_matching(
    client: TestClient, new_game: NewGame, tmp_path: Path
) -> None:
    game = new_game(seed=42, preset='harsh-winter')['id']
    for turn in range(TICKS):
        asked = ('commands', {'id': f'c-{turn}', 'kind': 'pass'}) if turn % 3 else ('clock', {'action': 'step'})
        client.post(f'{PREFIX}/games/{game}/{asked[0]}', json=asked[1])
    client.delete(f'{PREFIX}/games/{game}')

    answer = client.get(f'{PREFIX}/games/{game}/record')
    copy = tmp_path / 'alpha.jsonl.gz'
    copy.write_bytes(answer.content)
    lines = read(copy)
    played = replay(copy)

    assert answer.status_code == 200
    assert answer.headers['content-type'] == 'application/gzip'
    assert f'{game}.jsonl.gz' in answer.headers['content-disposition']
    assert (lines[0]['t'], lines[0]['game'], lines[0]['seed']) == ('header', game, 42)
    assert lines[-1]['t'] == 'footer'
    assert len([line for line in lines if line['t'] == 'command']) == 8
    assert played.matched
    assert played.diverged_at is None
    assert played.game.tick == TICKS
    assert played.game.state_hash() == lines[-1]['hash']


def test_the_record_of_a_live_game_is_given_as_far_as_it_is_written(client: TestClient, new_game: NewGame) -> None:
    game = new_game()['id']

    answer = client.get(f'{PREFIX}/games/{game}/record')

    assert answer.status_code == 200
    assert answer.content


def test_a_record_that_is_gone_is_404(client: TestClient, new_game: NewGame, settings: Settings) -> None:
    game = new_game()['id']
    client.delete(f'{PREFIX}/games/{game}')
    record_path(settings.records_dir, game).unlink()

    answer = client.get(f'{PREFIX}/games/{game}/record')

    assert answer.status_code == 404
    assert answer.json() == {'key': 'error-record-unreadable', 'values': {'path': f'{game}.jsonl.gz'}}
