"""
The tree of parameters: every number that shapes a game, typed and frozen.
"""

import hashlib
import json
from functools import cached_property
from typing import Annotated, Any, Self

from pydantic import BaseModel, ConfigDict, Field, model_serializer, model_validator

from ..core.errors import DominionError

SCHEMA_VERSION = 1
PARAMS_INVALID = 'error-params-invalid'
DURATION_UNITS = ('parts', 'days', 'months', 'years')
MODIFIER_KINDS = ('plus', 'times')
LAYERS = ('elevation', 'relief', 'moisture', 'temperature')
RESOURCES = ('water', 'forage')
ZOOM = 5

Name = Annotated[str, Field(strict=True, pattern=r'^[a-z][a-z0-9_]*$')]
Count = Annotated[int, Field(strict=True, ge=1)]
Span = Annotated[int, Field(strict=True, ge=0)]
Side = Annotated[int, Field(strict=True, ge=4)]
Share = Annotated[float, Field(strict=True, ge=0, le=1)]
Level = Annotated[float, Field(strict=True, ge=-1, le=1)]
Factor = Annotated[float, Field(strict=True, ge=0, allow_inf_nan=False)]
Amount = Annotated[float, Field(strict=True, allow_inf_nan=False)]
Colour = Annotated[str, Field(strict=True, pattern=r'^#[0-9a-fA-F]{6}$')]


def _invalid(path: str, found: object, expected: str) -> DominionError:
    return DominionError(PARAMS_INVALID, path=path, found=found, expected=expected)


class Node(BaseModel):
    """
    A part of the tree: unknown names are refused and nothing changes after.
    """

    model_config = ConfigDict(extra='forbid', frozen=True)


class Duration(Node):
    """
    A span of game time in one calendar unit, such as {days: 3}.
    """

    parts: Span | None = None
    days: Span | None = None
    months: Span | None = None
    years: Span | None = None

    @model_validator(mode='after')
    def _one_unit(self) -> Self:
        given = [unit for unit in DURATION_UNITS if getattr(self, unit) is not None]
        if len(given) != 1:
            raise ValueError(f'exactly one of {", ".join(DURATION_UNITS)}')
        return self

    @model_serializer
    def _as_written(self) -> dict[str, int]:
        return {self.unit: self.amount}

    @property
    def unit(self) -> str:
        return next(unit for unit in DURATION_UNITS if getattr(self, unit) is not None)

    @property
    def amount(self) -> int:
        amount: int = getattr(self, self.unit)
        return amount


class Season(Node):
    name: Name
    months: Count


class Time(Node):
    day_parts: tuple[Name, ...] = Field(min_length=1)
    days_per_month: Count
    seasons: tuple[Season, ...] = Field(min_length=1)

    @property
    def parts_per_day(self) -> int:
        return len(self.day_parts)

    @property
    def months_per_year(self) -> int:
        return sum(season.months for season in self.seasons)

    @property
    def days_per_year(self) -> int:
        return self.months_per_year * self.days_per_month


class Modifier(Node):
    """
    One change laid over a base: {plus: x} adds, {times: x} multiplies.
    """

    plus: Amount | None = None
    times: Factor | None = None

    @model_validator(mode='after')
    def _one_kind(self) -> Self:
        if (self.plus is None) == (self.times is None):
            raise ValueError(f'exactly one of {", ".join(MODIFIER_KINDS)}')
        return self

    @model_serializer
    def _as_written(self) -> dict[str, float]:
        return {self.kind: self.amount}

    @property
    def kind(self) -> str:
        return next(kind for kind in MODIFIER_KINDS if getattr(self, kind) is not None)

    @property
    def amount(self) -> float:
        amount: float = getattr(self, self.kind)
        return amount


class Era(Node):
    parts_per_tick: Count
    cell_km: Count
    properties: tuple[Name, ...] = Field(min_length=1)


class Eras(Node):
    """
    One field per era, read by name as well: eras['band'].
    """

    band: Era

    def __getitem__(self, name: str) -> Era:
        if name not in type(self).model_fields:
            raise KeyError(name)
        era: Era = getattr(self, name)
        return era


class Range(Node):
    """
    A closed range over a layer; a side left out is open.
    """

    min: Level | None = None
    max: Level | None = None

    @model_validator(mode='after')
    def _ordered(self) -> Self:
        if self.min is None and self.max is None:
            raise ValueError('min, max or both')
        if self.min is not None and self.max is not None and self.min > self.max:
            raise ValueError('min not above max')
        return self

    def holds(self, value: float) -> bool:
        return (self.min is None or value >= self.min) and (self.max is None or value <= self.max)


class Generation(Node):
    order: Span
    elevation: Range | None = None
    relief: Range | None = None
    moisture: Range | None = None
    temperature: Range | None = None

    @property
    def ranges(self) -> dict[str, Range]:
        return {layer: found for layer in LAYERS if (found := getattr(self, layer)) is not None}


class Property(Node):
    base: Share
    recovery: Duration | None = None
    seasons: dict[Name, Modifier] = Field(default_factory=dict)

    @model_validator(mode='after')
    def _recovers_in_time(self) -> Self:
        if self.recovery is not None and self.recovery.amount == 0:
            raise ValueError('a recovery that takes time')
        return self


class BiomeEra(Node):
    properties: dict[Name, Property]
    resources: tuple[Name, ...]


class Biome(Node):
    colour: Colour
    generation: Generation
    eras: dict[Name, BiomeEra]


class Layer(Node):
    scale_km: Count
    octaves: Count
    persistence: Share


class Temperature(Node):
    lapse: Share
    noise: Share
    scale_km: Count


class Rivers(Node):
    share: Share
    meander_km: Span
    effects: dict[Name, dict[Name, Modifier]]


class Latitude(Node):
    """
    A belt of the northern half: 0 at the equator, 1 at the pole.
    """

    min: Share
    max: Share

    @model_validator(mode='after')
    def _ordered(self) -> Self:
        if self.min > self.max:
            raise ValueError('min not above max')
        return self


class Needs(Node):
    land: Share
    rivers: Span
    biomes: dict[Name, Share]


class Window(Node):
    width: Side
    height: Side
    x: Span | None
    y: Span | None
    latitude: Latitude
    tries: Count
    needs: Needs


class Planet(Node):
    circumference_km: Count
    skeleton_km: Count
    sea: Share
    elevation: Layer
    relief: Layer
    moisture: Layer
    temperature: Temperature
    rivers: Rivers
    window: Window


class Params(Node):
    """
    The resolved tree. A new section is a field here and a file in defaults.
    """

    time: Time
    eras: Eras
    planet: Planet
    biomes: dict[Name, Biome]

    @model_validator(mode='after')
    def _agree(self) -> Self:
        self._check_names()
        self._check_ticks()
        self._check_biomes()
        self._check_generation()
        self._check_planet()
        self._check_window()
        return self

    def _check_names(self) -> None:
        named = {
            'time.day_parts': list(self.time.day_parts),
            'time.seasons': [season.name for season in self.time.seasons],
        }
        for era, held in self.eras:
            named[f'eras.{era}.properties'] = list(held.properties)
        for name, biome in self.biomes.items():
            for era, given in biome.eras.items():
                named[f'biomes.{name}.eras.{era}.resources'] = list(given.resources)
        for path, names in named.items():
            if len(set(names)) != len(names):
                raise _invalid(path, names, 'names that do not repeat')

    def _check_ticks(self) -> None:
        day = self.time.parts_per_day
        for name, era in self.eras:
            if day % era.parts_per_tick and era.parts_per_tick % day:
                expected = f'a divisor or a multiple of the {day} parts of a day'
                raise _invalid(f'eras.{name}.parts_per_tick', era.parts_per_tick, expected)

    def _check_biomes(self) -> None:
        eras: dict[str, Era] = dict(self.eras)
        seasons = [season.name for season in self.time.seasons]
        for name, biome in self.biomes.items():
            path = f'biomes.{name}.eras'
            if set(biome.eras) != set(eras):
                raise _invalid(path, sorted(biome.eras), f'the eras {", ".join(eras)}')
            for era, given in biome.eras.items():
                wanted = eras[era].properties
                if set(given.properties) != set(wanted):
                    found = sorted(given.properties)
                    raise _invalid(f'{path}.{era}.properties', found, f'the properties {", ".join(wanted)}')
                for resource in given.resources:
                    if resource not in RESOURCES:
                        raise _invalid(f'{path}.{era}.resources', resource, f'one of {", ".join(RESOURCES)}')
                for prop, held in given.properties.items():
                    for season in held.seasons:
                        if season not in seasons:
                            below = f'{path}.{era}.properties.{prop}.seasons'
                            raise _invalid(below, season, f'one of {", ".join(seasons)}')

    def _check_generation(self) -> None:
        orders = {name: biome.generation.order for name, biome in self.biomes.items()}
        if len(set(orders.values())) != len(orders):
            raise _invalid('biomes', orders, 'orders of generation that do not repeat')
        rest = [name for name, biome in self.biomes.items() if not biome.generation.ranges]
        if len(rest) != 1:
            raise _invalid('biomes', rest, 'exactly one biome with no ranges')

    def _check_planet(self) -> None:
        planet = self.planet
        around = planet.circumference_km
        eras: dict[str, Era] = dict(self.eras)
        for era, held in eras.items():
            if around % (2 * held.cell_km):
                expected = f'a size that cuts the {around} km around the planet and half of it into whole cells'
                raise _invalid(f'eras.{era}.cell_km', held.cell_km, expected)
        if around % (2 * planet.skeleton_km):
            expected = f'a size that cuts the {around} km around the planet and half of it into whole squares'
            raise _invalid('planet.skeleton_km', planet.skeleton_km, expected)
        cell = self.eras.band.cell_km
        if around // cell % ZOOM:
            raise _invalid('planet.circumference_km', around, f'a multiple of {ZOOM} cells of {cell} km')
        for era, effects in planet.rivers.effects.items():
            if era not in eras:
                raise _invalid('planet.rivers.effects', era, f'one of {", ".join(eras)}')
            for prop in effects:
                if prop not in eras[era].properties:
                    expected = f'one of {", ".join(eras[era].properties)}'
                    raise _invalid(f'planet.rivers.effects.{era}', prop, expected)
        for name in planet.window.needs.biomes:
            if name not in self.biomes:
                raise _invalid('planet.window.needs.biomes', name, f'one of {", ".join(sorted(self.biomes))}')

    def _check_window(self) -> None:
        window = self.planet.window
        across = self.planet.circumference_km // self.eras.band.cell_km
        down = across // 2
        if window.width > across:
            raise _invalid('planet.window.width', window.width, f'up to the {across} cells around the planet')
        if window.height > down:
            raise _invalid('planet.window.height', window.height, f'up to the {down} cells from pole to pole')
        if window.x is None or window.y is None:
            if window.x is not None or window.y is not None:
                found = {'x': window.x, 'y': window.y}
                raise _invalid('planet.window', found, 'x and y given together or both left out')
            return
        if window.x + window.width > across:
            raise _invalid('planet.window.x', window.x, f'up to {across - window.width}, clear of the seam')
        if window.y + window.height > down:
            raise _invalid('planet.window.y', window.y, f'up to {down - window.height}, clear of the pole')

    @property
    def schema_version(self) -> int:
        return SCHEMA_VERSION

    def tree(self) -> dict[str, Any]:
        return self.model_dump(mode='json')

    @cached_property
    def hash(self) -> str:
        canonical = json.dumps(self.tree(), sort_keys=True, separators=(',', ':'), ensure_ascii=True)
        return hashlib.sha256(canonical.encode()).hexdigest()
