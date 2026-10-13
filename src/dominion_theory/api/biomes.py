"""
The biomes of a game, as its current era reads them.
"""

from typing import Any

from ..engine import Game

PREFIX = 'biome-'


def described(game: Game) -> dict[str, Any]:
    """
    Every biome in generation order, with the base of each property of the era.
    """
    era = game.era
    names = game.params.eras[era].properties
    biomes = []
    for biome in game.snapshot()['biomes']:
        held = game.params.biomes[biome]
        biomes.append(
            {
                'id': biome,
                'name': {'key': f'{PREFIX}{biome}', 'values': {}},
                'colour': held.colour,
                'properties': {name: held.eras[era].properties[name].base for name in names},
                'resources': list(held.eras[era].resources),
            }
        )
    return {'era': era, 'biomes': biomes}
