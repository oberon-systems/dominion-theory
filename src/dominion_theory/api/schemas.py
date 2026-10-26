"""
The shapes of docs/api/protocol.md: what is asked, what is answered, and the messages of the stream.
"""

from enum import StrEnum
from typing import Annotated, Any, Literal, Self

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
    draw: int = Field(default=0, ge=0, le=SEED_MAX)
    preset: str | None = None
    overrides: dict[str, Any] | None = None
    mode: Mode = 'real-time'
    seated: bool = True


class Game(BaseModel):
    id: str
    seed: int
    draw: int
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


class Place(BaseModel):
    scale: int
    x: int
    y: int


class Spot(BaseModel):
    x: int
    y: int


class Camp(BaseModel):
    kind: Literal['camp']


class Build(BaseModel):
    kind: Literal['build']


class Gather(BaseModel):
    """
    A gathering: the share of the gatherers that went to every resource.
    """

    kind: Literal['gather']
    shares: dict[str, float]


class Walk(BaseModel):
    kind: Literal['move']
    towards: str


class Roam(BaseModel):
    kind: Literal['roam']
    towards: str


Action = Annotated[Camp | Build | Gather | Walk | Roam, Field(discriminator='kind')]


class GoProposal(BaseModel):
    kind: Literal['go']
    to: Spot


class StayProposal(BaseModel):
    kind: Literal['stay-and-gather']


class WinterCampProposal(BaseModel):
    kind: Literal['winter-camp']


Proposal = Annotated[GoProposal | StayProposal | WinterCampProposal, Field(discriminator='kind')]


class Intent(BaseModel):
    """
    A proposal the player carried against the leader, held until the next council.
    """

    proposal: Proposal


class Reason(BaseModel):
    """
    Why the band does what it does; the fields of its action beside its kind are additional fields.
    """

    model_config = ConfigDict(extra='allow')
    __pydantic_extra__: dict[str, Any] = Field(init=False)

    action: Literal['camp', 'build', 'gather', 'move', 'roam']
    need: str
    score: float
    pull: Spot | None


class Site(BaseModel):
    """
    The cell of a winter camp and the share of its building done; it shelters the band at 1.
    """

    x: int
    y: int
    built: float


class Unit(BaseModel):
    """
    A band as a client sees it: docs/game/01_bands.md, What the API shows.
    """

    id: int
    kind: Literal['band']
    place: Place
    population: int
    ages: dict[str, int]
    pregnant: int
    injured: int
    wounds: dict[str, int]
    sick: int
    stores: dict[str, float]
    goods: dict[str, float]
    kit: dict[str, int]
    fatigue: float
    states: list[str]
    action: Action
    intent: Intent | None
    route: list[Spot]
    roles: dict[str, int]
    camp: Site | None
    camps: list[Spot]
    reason: Reason | None
    lore: list[str]


class Votes(BaseModel):
    """
    One option of the table: the proposal, its words as the band says them where it stands, its votes and the
    band's score of a day of it.
    """

    proposal: Proposal
    key: str
    votes: int
    score: float | None = None


class Council(BaseModel):
    """
    The council of the day while it sits: the others' votes, the option they lead with, the occasion that called
    it, the player's voice, whether a winter camp is offered and whether the player may name a place of their own.
    """

    leader: Proposal | None
    table: list[Votes]
    occasion: str | None = None
    voice: float | None = None
    winter: bool = False
    place: bool = True


class Seat(BaseModel):
    name: str
    unit: int | None
    status: float
    seated: bool
    council: Council | None


class SeatChange(BaseModel):
    """
    Only what moved in the update; a key that did not move is left out. A council of null has risen.
    """

    status: float | None = None
    council: Council | None = None


class Snapshot(BaseModel):
    seq: int
    date: Date
    window: Window
    seat: Seat
    units: list[Unit]
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
    Beside the named fields, one list per stocked property of the era, in the order of cells;
    in a map of what a band knows, one per property and seen instead, null where it knows nothing.
    """

    model_config = ConfigDict(extra='allow')
    __pydantic_extra__: dict[str, list[float | None]] = Field(init=False)

    scale: int
    x: int
    y: int
    width: int
    height: int
    biomes: list[str]
    cells: list[int | None]
    rivers: list[int | None]


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


class Known(BaseModel):
    """
    A cell as the band now remembers it: one value per property of the era, and the day it was seen.
    """

    model_config = ConfigDict(extra='allow')
    __pydantic_extra__: dict[str, float] = Field(init=False)

    x: int
    y: int
    biome: str
    river: bool
    seen: int


class Changes(BaseModel):
    units: list[Unit]
    gone: list[int]
    cells: list[Cell]
    known: list[Known]
    seat: SeatChange


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
