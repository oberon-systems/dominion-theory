"""
A run file of lab/runs/: the lands, draws, players and sets of parameters it plays, docs/lab/runs.md.
"""

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Annotated, Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..content import Params, load_params
from ..players import made

DRAWS = 'draws'


class Node(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)


class Lands(Node):
    first: int = Field(ge=0)
    count: int = Field(ge=1)


class Until(Node):
    people: int = Field(default=150, ge=1)
    years: float = Field(default=18, gt=0)


class Set(Node):
    preset: str | None = None
    overrides: dict[str, Any] = Field(default_factory=dict)

    def params(self) -> Params:
        return load_params(self.preset, self.overrides)


@dataclass(frozen=True)
class Planned:
    """
    One game of a run.
    """

    land: int
    draw: int
    player: str
    set: str

    @property
    def key(self) -> tuple[int, int, str, str]:
        return self.land, self.draw, self.player, self.set

    def data(self) -> dict[str, Any]:
        return asdict(self)


class Run(Node):
    lands: Lands | Annotated[list[int], Field(min_length=1)]
    draws: int = Field(ge=1)
    until: Until = Until()
    workers: int = Field(default=1, ge=1)
    players: list[str | dict[str, Any]] = Field(min_length=1)
    params: dict[str, Set] = Field(default_factory=lambda: {'default': Set()}, min_length=1)
    records: int = Field(default=0, ge=0)

    @model_validator(mode='after')
    def _seated(self) -> Run:
        names = [name for name, _, _ in self.seated]
        if len(set(names)) < len(names):
            raise ValueError(f'every player once, not {", ".join(names)}')
        for held in self.params.values():
            params = held.params()
            for _, spec, _ in self.seated:
                made(spec, params, 0)
        return self

    @property
    def seeds(self) -> list[int]:
        lands = self.lands
        return list(lands) if isinstance(lands, list) else list(range(lands.first, lands.first + lands.count))

    @property
    def seated(self) -> list[tuple[str, str | Mapping[str, Any], int]]:
        """
        Every player as its name, what makes it and the draws it plays, no more than those of the run.
        """
        found: list[tuple[str, str | Mapping[str, Any], int]] = []
        for spec in self.players:
            if isinstance(spec, str):
                found.append((spec, spec, self.draws))
                continue
            maker = {name: value for name, value in spec.items() if name != DRAWS}
            draws = min(int(spec.get(DRAWS, self.draws)), self.draws)
            found.append((str(maker.get('mind', maker)), maker, draws))
        return found

    def spec(self, player: str) -> str | Mapping[str, Any]:
        return next(spec for name, spec, _ in self.seated if name == player)

    def planned(self) -> list[Planned]:
        """
        A game per set, land, player and draw, in that order.
        """
        return [
            Planned(land, draw, name, held)
            for held in self.params
            for land in self.seeds
            for name, _, draws in self.seated
            for draw in range(draws)
        ]


def load(path: Path) -> Run:
    return Run.model_validate(yaml.safe_load(path.read_text(encoding='utf-8'))['run'])
