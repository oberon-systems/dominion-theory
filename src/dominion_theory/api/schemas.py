"""
The shapes of docs/api/protocol.md: what is asked, what is answered, and the messages of the stream.
"""

from enum import StrEnum
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, model_validator

SEED_MAX = 2**63 - 1

Mode = Literal['step', 'real-time']


class View(StrEnum):
    SEAT = 'seat'
    SPECTATOR = 'spectator'


class Asked(BaseModel):
    """
    A body a client sends: a name it does not know is a request that cannot be read.
    """

    model_config = ConfigDict(extra='forbid')


class Message(BaseModel):
    key: str
    values: dict[str, Any]


class Date(BaseModel):
    year: int
    month: int
    day: int
    part: str
    season: str


class Window(BaseModel):
    scale: int
    x: int
    y: int
    width: int
    height: int


class Health(BaseModel):
    status: Literal['ok'] = 'ok'


class Profile(BaseModel):
    id: str
    name: str
    language: str


class ProfileChange(Asked):
    name: str | None = Field(default=None, min_length=1, max_length=64)
    language: str | None = None


class Presets(BaseModel):
    presets: list[str]


class NewGame(Asked):
    seed: int | None = Field(default=None, ge=0, le=SEED_MAX)
    preset: str | None = None
    overrides: dict[str, Any] | None = None
    mode: Mode = 'real-time'


class Game(BaseModel):
    id: str
    seed: int
    params_hash: str
    mode: str
    running: bool
    date: Date


class Row(BaseModel):
    """
    One game of the index. Times are Unix seconds.
    """

    id: str
    seed: int
    params_hash: str
    preset: str | None
    started_at: int
    finished_at: int | None
    outcome: str | None
    last_tick: int


class Games(BaseModel):
    games: list[Row]


class Snapshot(BaseModel):
    seq: int
    date: Date
    window: Window
    seat: dict[str, Any]
    units: list[dict[str, Any]]
    waiting: list[str]


class Biome(BaseModel):
    id: str
    name: Message
    colour: str
    properties: dict[str, float]
    resources: list[str]


class Biomes(BaseModel):
    era: str
    biomes: list[Biome]


class Map(BaseModel):
    """
    Beside the named fields, one list of stocks per stocked property of the era, in the order of cells.
    """

    model_config = ConfigDict(extra='allow')
    __pydantic_extra__: dict[str, list[float]] = Field(init=False)

    scale: int
    x: int
    y: int
    width: int
    height: int
    biomes: list[str]
    cells: list[int]
    rivers: list[int]


class Taken(BaseModel):
    id: str
    taken: Literal[True] = True


class ClockRequest(Asked):
    action: Literal['pause', 'resume', 'speed', 'step']
    value: float | None = Field(default=None, gt=0)

    @model_validator(mode='after')
    def _speed_has_a_value(self) -> Self:
        if self.action == 'speed' and self.value is None:
            raise ValueError('speed takes a value')
        return self


class Cell(BaseModel):
    """
    The whole new state of a cell: its place and one stock per stocked property of the era.
    """

    model_config = ConfigDict(extra='allow')
    __pydantic_extra__: dict[str, float] = Field(init=False)

    x: int
    y: int


class Changes(BaseModel):
    units: list[dict[str, Any]]
    gone: list[int]
    cells: list[Cell]
    seat: dict[str, Any]


class Update(BaseModel):
    seq: int
    date: Date
    events: list[Message]
    changes: Changes
    waiting: list[str]


class Resync(BaseModel):
    resync: Literal[True]
    seq: int


STREAM: TypeAdapter[Update | Resync] = TypeAdapter(Update | Resync)


def stream_schema() -> dict[str, Any]:
    return {
        '$schema': 'https://json-schema.org/draft/2020-12/schema',
        'title': 'A message of the stream of updates',
        **STREAM.json_schema(),
    }
