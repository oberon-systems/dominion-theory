"""
What a band learns by living: the counters it learns by and the skills they teach, as docs/game/skills.md states them.
"""

import copy
from typing import TYPE_CHECKING, Any, Protocol

from ..content import BY_BIOME, NEW, Condition, Params
from .cells import Place

if TYPE_CHECKING:
    from .band import Band

SEEN = 'seen'
FIRST = 'first'
WALKED = 'walked'
WALKED_BY = 'walked_by'
CAMPED_BY = 'camped_by'
DAYS_IN = 'days_in'
WINTERS = 'winters'
MARCHED = 'marched'
MARCHING = 'marching'
KNOWN = 'known'
COUNTS = 'counts'
SINCE = 'since'
GO_PLACE = 'go_place'
WINTER_CAMP = 'winter_camp'
PROPOSALS = 'proposals'
GATHERS = 'gathers'
MAKES = 'makes'


class Land(Protocol):
    def inside(self, x: int, y: int) -> bool: ...

    def biome(self, x: int, y: int) -> str: ...


def fresh() -> dict[str, Any]:
    """
    The lore of a band that has learned nothing and counted nothing.
    """
    counts: dict[str, Any] = {SEEN: [], FIRST: [], WINTERS: 0, MARCHED: 0, **{name: {} for name in BY_BIOME}}
    return {KNOWN: [], COUNTS: counts, SINCE: {}, MARCHING: False}


def beside(land: Land, at: Place) -> list[str]:
    """
    The biomes of a cell and of the cells around it, each once.
    """
    found = {
        land.biome(at[0] + dx, at[1] + dy)
        for dx in (-1, 0, 1)
        for dy in (-1, 0, 1)
        if land.inside(at[0] + dx, at[1] + dy)
    }
    return sorted(found)


def _add(counts: dict[str, Any], counter: str, biomes: list[str]) -> None:
    held = counts[counter]
    for biome in biomes:
        held[biome] = held.get(biome, 0) + 1


def _seen(counts: dict[str, Any], band: Band, counter: str) -> None:
    counts[counter] = sorted({*counts[counter], *(cell['biome'] for cell in band.known.values())})


def begin(band: Band) -> None:
    """
    The first day: what the band sees is the land it was born in.
    """
    for counter in (SEEN, FIRST):
        _seen(band.lore[COUNTS], band, counter)


def entered(land: Land, band: Band) -> None:
    counts = band.lore[COUNTS]
    _add(counts, WALKED, [land.biome(*band.place)])
    _add(counts, WALKED_BY, beside(land, band.place))


def day_ends(land: Land, band: Band) -> None:
    """
    The counters of a day: the land seen, a day on the march, the day in the biome of the cell and the night
    beside it.
    """
    counts = band.lore[COUNTS]
    _seen(counts, band, SEEN)
    if band.lore[MARCHING]:
        counts[MARCHED] += 1
    band.lore[MARCHING] = False
    _add(counts, DAYS_IN, [land.biome(*band.place)])
    _add(counts, CAMPED_BY, beside(land, band.place))


def march(band: Band) -> None:
    """
    The band walked today, plainly or roaming; standing, gathering and building are no march.
    """
    band.lore[MARCHING] = True


def wintered(band: Band) -> None:
    band.lore[COUNTS][WINTERS] += 1


def known(band: Band, skill: str) -> bool:
    return skill in band.lore[KNOWN]


def opened(params: Params, band: Band, kind: str, name: str) -> bool:
    """
    Whether a proposal, a gathering, a recipe or a role is open to the band: no skill opens it, or one it knows does.
    """
    opening = [skill for skill, held in params.skills.items() if name in getattr(held.opens, kind)]
    return not opening or any(known(band, skill) for skill in opening)


def learn(params: Params, band: Band) -> list[str]:
    """
    The skills learned today, in the order of the tree. A skill whose needs are met keeps the counts of that day,
    and its condition reads what was gained since.
    """
    lore = band.lore
    learned = []
    for name, skill in params.skills.items():
        if name in lore[KNOWN] or not all(known(band, needed) for needed in skill.needs):
            continue
        if skill.needs and name not in lore[SINCE]:
            lore[SINCE][name] = copy.deepcopy(lore[COUNTS])
        if holds(skill.learned, band, lore[SINCE].get(name)):
            lore[KNOWN].append(name)
            lore[SINCE].pop(name, None)
            learned.append(name)
    return learned


def holds(condition: Condition, band: Band, base: dict[str, Any] | None = None) -> bool:
    if condition.any:
        return any(holds(held, band, base) for held in condition.any)
    if condition.all:
        return all(holds(held, band, base) for held in condition.all)
    if condition.holds:
        return all(band.held(name) >= amount for name, amount in condition.holds.items())
    return counted(condition, band.lore[COUNTS], base) >= (condition.at_least or 0.0)


def counted(condition: Condition, counts: dict[str, Any], base: dict[str, Any] | None = None) -> float:
    """
    What a counter reads: a set by its size, a tally as it is, a counter by biome summed over its biomes or, for
    the biome new, the most of any biome not seen on the first day; less what it read at the base.
    """
    counter = str(condition.counter)
    if counter not in BY_BIOME:
        return _size(counts[counter]) - (0 if base is None else _size(base[counter]))
    held, before = counts[counter], {} if base is None else base[counter]
    gained: dict[str, int] = {biome: held[biome] - before.get(biome, 0) for biome in held}
    if condition.biome == NEW:
        first = counts[FIRST]
        return max((amount for biome, amount in gained.items() if biome not in first), default=0)
    biomes = condition.biomes or (() if condition.biome is None else (condition.biome,))
    return sum(gained.get(biome, 0) for biome in biomes)


def _size(held: Any) -> int:
    return len(held) if isinstance(held, list) else int(held)
