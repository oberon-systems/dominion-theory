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

Name = Annotated[str, Field(strict=True, pattern=r'^[a-z][a-z0-9_]*$')]
Count = Annotated[int, Field(strict=True, ge=1)]
Span = Annotated[int, Field(strict=True, ge=0)]
Side = Annotated[int, Field(strict=True, ge=4)]


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


class Era(Node):
    parts_per_tick: Count


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


class Window(Node):
    width: Side
    height: Side


class Planet(Node):
    window: Window


class Params(Node):
    """
    The resolved tree. A new section is a field here and a file in defaults.
    """

    time: Time
    eras: Eras
    planet: Planet

    @model_validator(mode='after')
    def _agree(self) -> Self:
        named = {
            'time.day_parts': list(self.time.day_parts),
            'time.seasons': [season.name for season in self.time.seasons],
        }
        for path, names in named.items():
            if len(set(names)) != len(names):
                raise DominionError(PARAMS_INVALID, path=path, found=names, expected='names that do not repeat')
        day = self.time.parts_per_day
        for name, era in self.eras:
            if day % era.parts_per_tick and era.parts_per_tick % day:
                raise DominionError(
                    PARAMS_INVALID,
                    path=f'eras.{name}.parts_per_tick',
                    found=era.parts_per_tick,
                    expected=f'a divisor or a multiple of the {day} parts of a day',
                )
        return self

    @property
    def schema_version(self) -> int:
        return SCHEMA_VERSION

    def tree(self) -> dict[str, Any]:
        return self.model_dump(mode='json')

    @cached_property
    def hash(self) -> str:
        canonical = json.dumps(self.tree(), sort_keys=True, separators=(',', ':'), ensure_ascii=True)
        return hashlib.sha256(canonical.encode()).hexdigest()
