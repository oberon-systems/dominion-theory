from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient
from fluent.syntax import FluentParser, ast

from dominion_theory.api import PREFIX
from dominion_theory.api.biomes import described
from dominion_theory.content import load_params
from dominion_theory.engine import Game
from dominion_theory.i18n import LANGUAGES, catalogue

type NewGame = Callable[..., dict[str, Any]]

SMALL = {'planet.circumference_km': 4000, 'planet.window.width': 32, 'planet.window.height': 16}
ORDER = [
    'water',
    'mountain',
    'tundra',
    'outcrops',
    'hills',
    'swamp',
    'floodplain',
    'dunes',
    'desert',
    'marsh',
    'forest',
    'grass',
]
BASES = {'water': 0.6, 'food': 0.9, 'threat': 0.4, 'passability': 0.6}
FOREST = {
    'id': 'forest',
    'name': {'key': 'biome-forest', 'values': {}},
    'colour': '#006400',
    'properties': BASES,
    'resources': ['water', 'forage'],
}


def test_the_biomes_are_those_of_the_default_tree_in_generation_order(client: TestClient, new_game: NewGame) -> None:
    params = load_params(overrides=SMALL)
    answer = client.get(f'{PREFIX}/games/{new_game(seed=42)["id"]}/biomes')
    biomes = answer.json()['biomes']

    assert answer.status_code == 200
    assert answer.json()['era'] == 'band'
    assert [biome['id'] for biome in biomes] == ORDER
    assert biomes[10] == FOREST
    for biome in biomes:
        held = params.biomes[biome['id']]
        era = held.eras['band']
        assert biome['colour'] == held.colour
        assert biome['properties'] == {name: era.properties[name].base for name in params.eras['band'].properties}
        assert biome['resources'] == list(era.resources)


def test_an_overridden_base_is_the_one_given(client: TestClient, new_game: NewGame) -> None:
    overrides = {**SMALL, 'biomes.forest.eras.band.properties.food.base': 0.5}
    created = new_game(seed=42, overrides=overrides)

    biomes = client.get(f'{PREFIX}/games/{created["id"]}/biomes').json()['biomes']

    assert biomes[10]['properties'] == {**BASES, 'food': 0.5}
    assert biomes[11]['properties']['food'] == load_params().biomes['grass'].eras['band'].properties['food'].base


@pytest.mark.parametrize('lang', LANGUAGES)
def test_every_name_is_in_the_catalogue(lang: str) -> None:
    game = Game.create(seed=42, params=load_params(overrides=SMALL))
    written = {entry.id.name for entry in FluentParser().parse(catalogue(lang)).body if isinstance(entry, ast.Message)}

    names = [biome['name'] for biome in described(game)['biomes']]

    assert {name['key'] for name in names} <= written
    assert all(name['values'] == {} for name in names)


def test_both_views_show_the_same(client: TestClient, new_game: NewGame) -> None:
    address = f'{PREFIX}/games/{new_game(seed=42)["id"]}/biomes'

    seat = client.get(address)
    spectator = client.get(address, params={'view': 'spectator'})

    assert spectator.json() == seat.json()
    assert client.get(address, params={'view': 'alpha'}).status_code == 400


def test_an_unknown_game_has_no_biomes(client: TestClient) -> None:
    answer = client.get(f'{PREFIX}/games/alpha/biomes')

    assert answer.status_code == 404
    assert answer.json() == {'key': 'error-game-not-found', 'values': {'id': 'alpha'}}
