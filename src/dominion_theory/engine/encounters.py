"""
Chance encounters: what the land does to a band, as docs/game/01_bands.md states it.
"""

import numpy as np

from ..content import Encounter, Params
from .band import GATHER, Action

DRAWS = 3


def fits(kind: Encounter, biome: str, river: bool, action: Action) -> bool:
    """
    Whether a kind of encounter can happen on such a cell during such an action.
    """
    placed = kind.biomes or kind.rivers
    if placed and biome not in kind.biomes and not (kind.rivers and river):
        return False
    if kind.actions and action['kind'] not in kind.actions:
        return False
    gathered = action.get('resource') if action['kind'] == GATHER else None
    return not kind.resources or gathered in kind.resources


def strike(
    params: Params,
    population: int,
    biome: str,
    river: bool,
    threat: float,
    action: Action,
    rng: np.random.Generator,
) -> tuple[str, int] | None:
    """
    The encounter of a tick, if any: its kind and the people it takes. Three numbers are drawn
    in every tick whatever comes of them, so the stream never depends on what happened before.
    """
    happens, which, share = (float(drawn) for drawn in rng.random(DRAWS))
    rules = params.encounters
    if happens >= rules.chance * threat * rules.actions.get(action['kind'], 1.0):
        return None
    kinds = {name: kind for name, kind in sorted(rules.kinds.items()) if fits(kind, biome, river, action)}
    if not kinds:
        return None
    at = which * sum(kind.weight for kind in kinds.values())
    name = next(reversed(kinds))
    for candidate, kind in kinds.items():
        at -= kind.weight
        if at < 0:
            name = candidate
            break
    loss = kinds[name].loss
    taken = loss.min + share * (loss.max - loss.min)
    return name, min(int(population * taken + 0.5), population)
