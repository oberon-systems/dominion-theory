from collections.abc import Callable
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from dominion_theory.api import PREFIX
from dominion_theory.runner import read

type NewGame = Callable[..., dict[str, Any]]

TICKS = 60
COMMANDS: list[tuple[str, dict[str, Any]]] = [
    ('commands', {'id': f'c-{turn}', 'kind': 'pass'}) if turn % 4 else ('clock', {'action': 'step'})
    for turn in range(TICKS)
]


def hashes(client: TestClient, new_game: NewGame, folder: Path, **asked: Any) -> list[tuple[int, str]]:
    """
    Plays the list through the API and gives the state hash after every tick, as the record holds it.
    """
    game = new_game(**asked)['id']
    for address, body in COMMANDS:
        assert client.post(f'{PREFIX}/games/{game}/{address}', json=body).status_code == 200
    client.delete(f'{PREFIX}/games/{game}')
    copy = folder / f'{game}.jsonl.gz'
    copy.write_bytes(client.get(f'{PREFIX}/games/{game}/record').content)
    return [(line['tick'], line['hash']) for line in read(copy) if line['t'] == 'tick']


def test_one_seed_and_one_list_of_commands_give_equal_hashes_after_every_tick(
    client: TestClient, new_game: NewGame, tmp_path: Path
) -> None:
    first = hashes(client, new_game, tmp_path, seed=42, preset='harsh-winter')
    second = hashes(client, new_game, tmp_path, seed=42, preset='harsh-winter')

    assert [tick for tick, _ in first] == list(range(1, TICKS + 1))
    assert first == second
    assert len({state for _, state in first}) == TICKS


def test_another_seed_gives_other_hashes(client: TestClient, new_game: NewGame, tmp_path: Path) -> None:
    first = hashes(client, new_game, tmp_path, seed=42)
    second = hashes(client, new_game, tmp_path, seed=43)

    assert first[-1] != second[-1]
