"""
The tree of parameters: every number that shapes a game, typed and frozen.
"""

import builtins
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
LAYERS = ('elevation', 'relief', 'moisture', 'temperature', 'flow')
ACTIONS = ('move', 'roam', 'gather', 'camp', 'build')
CAUSES = ('hunger', 'thirst', 'encounter', 'age', 'frailty', 'birth')
BAND = 'band'
PASSABILITY = 'passability'
ZOOM = 5
# The counters a band learns by, docs/game/skills.md: those of a set or a sum, then those kept by biome or season.
TALLIES = ('seen', 'first', 'winters', 'marched', 'births', 'crowded')
BY_BIOME = ('walked', 'walked_by', 'camped_by', 'days_in')
BY_SEASON = ('foraged_in',)
COUNTERS = TALLIES + BY_BIOME + BY_SEASON
NEW = 'new'
OPENED = ('proposals', 'gathers', 'makes', 'roles')
GATES = ('go_place', 'winter_camp')
# The goods of docs/game/skills.md: what a resource is, who holds it, whom its keep counts, whom a bonus goes to.
KINDS = ('food', 'water', 'goods')
GOODS = 'goods'
COMMON = 'common'
PERSONAL = 'personal'
HOLDERS = (COMMON, PERSONAL)
PER = ('head', 'member', 'adult', 'puller', 'hunter', 'nanny')
USES = ('eaten', 'nights', 'attacks', 'cures', 'pulled', 'hunts', 'carried')
# A bonus goes `to`, not `on`: YAML reads a key on as true.
TO = ('band', 'member')
# What a hunt brings, by name.
HUNTED = ('meat', 'hides')
# What a mind may weigh of an option, each a function of the engine: docs/lab/players.md, What a seat sees.
FEATURES = (
    'go',
    'stay',
    'winter',
    'abstain',
    'votes',
    'leader',
    'score',
    'hunger_food',
    'thirst_water',
    'calm_threat',
    'river',
    'unknown',
    'distance',
    'winter_short',
    'short_stay',
    'outvoted',
)
SEXES = ('female', 'male')

Name = Annotated[str, Field(strict=True, pattern=r'^[a-z][a-z0-9_]*$')]
Count = Annotated[int, Field(strict=True, ge=1)]
Span = Annotated[int, Field(strict=True, ge=0)]
Side = Annotated[int, Field(strict=True, ge=4)]
Share = Annotated[float, Field(strict=True, ge=0, le=1)]
Level = Annotated[float, Field(strict=True, ge=-1, le=1)]
Factor = Annotated[float, Field(strict=True, ge=0, allow_inf_nan=False)]
Amount = Annotated[float, Field(strict=True, allow_inf_nan=False)]
Positive = Annotated[float, Field(strict=True, gt=0, allow_inf_nan=False)]
Points = Annotated[float, Field(strict=True, ge=0, le=100)]
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
    capacity: dict[Name, Positive] = Field(default_factory=dict)
    recovery: dict[Name, dict[Name, Factor]] = Field(default_factory=dict)


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
    flow: Range | None = None

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
    """
    What a biome is in an era. A shore is gathered from by a band on a cell beside it.
    """

    properties: dict[Name, Property]
    resources: tuple[Name, ...]
    shore: bool = Field(default=False, strict=True)


class Biome(Node):
    colour: Colour
    generation: Generation
    eras: dict[Name, BiomeEra]


class Layer(Node):
    scale_km: Count
    octaves: Count
    persistence: Share


class Ridges(Node):
    """
    Mountain ranges: lines of a noise of their own that lift the land they cross.
    """

    scale_km: Count
    octaves: Count
    persistence: Share
    weight: Factor
    sharpness: Count


class Basins(Node):
    """
    Hollows in the land, where lakes and inland seas gather: a share of the planet, sunk by a share of its height.
    """

    scale_km: Count
    octaves: Count
    persistence: Share
    share: Share
    depth: Share


class Continents(Node):
    """
    The shape of the planet: so many continents raised around centres drawn from the seed.
    None leaves the land to the noise alone.
    """

    count: Span
    weight: Factor
    radius_km: Count
    spread: Share
    edge: Count


class Islands(Layer):
    """
    A finer noise over the whole planet, which raises islands out of any sea.
    """

    weight: Factor


class Elevation(Layer):
    continents: Continents
    islands: Islands
    ridges: Ridges
    basins: Basins


class Belt(Node):
    """
    How wet a latitude is: 0 at the equator, 1 at the north pole. With no belt south of the equator
    the two halves of the planet are alike; a latitude below 0, down to -1 at the south pole, tells them apart.
    """

    latitude: Level
    wet: Share


class Moisture(Layer):
    """
    Noise, the belts of latitude laid over it, and the drying of land far from the sea.
    """

    belt: Factor
    inland: Factor
    inland_km: Count
    heights: Factor
    belts: tuple[Belt, ...] = Field(min_length=1)

    @model_validator(mode='after')
    def _northward(self) -> Self:
        latitudes = [held.latitude for held in self.belts]
        if any(first >= second for first, second in zip(latitudes, latitudes[1:], strict=False)):
            raise ValueError('belts from south to north, no latitude twice')
        return self


class Temperature(Node):
    lapse: Share
    noise: Share
    scale_km: Count
    warmth: Level


class Rivers(Node):
    share: Share
    great: Share
    lakes: Share
    lake_full: Share
    ocean: Share
    meander_km: Span
    width_km: Span
    valley_km: Count
    delta_km: Span
    arms: Span
    islands: Share
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
    elevation: Elevation
    relief: Layer
    moisture: Moisture
    temperature: Temperature
    rivers: Rivers
    window: Window


class Quality(Node):
    """
    The range the quality of a good is drawn from where it is gathered.
    """

    min: Share
    max: Share

    @model_validator(mode='after')
    def _ordered(self) -> Self:
        if self.min > self.max:
            raise ValueError('min not above max')
        return self


class Keep(Node):
    """
    How much of a good the band wants to hold: an amount for every head, member, adult, puller, hunter or nanny.
    """

    per: Name
    amount: Positive


class Bonus(Node):
    """
    What a good held lays over a path of the tree, {plus: x} or {times: x}, on the band or on its holder; a bonus
    of a sex or of seasons holds only for them.
    """

    to: Name
    path: Annotated[str, Field(strict=True, pattern=r'^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)*$')]
    plus: Amount | Duration | None = None
    times: Factor | None = None
    sex: Name | None = None
    seasons: tuple[Name, ...] = ()

    @model_validator(mode='after')
    def _one_kind(self) -> Self:
        if (self.plus is None) == (self.times is None):
            raise ValueError(f'exactly one of {", ".join(MODIFIER_KINDS)}')
        return self


class Resource(Node):
    """
    Something a band gathers, makes or carries: its kind, the property of a cell it is taken by, its weight, how
    long it keeps and, for goods, how many uses a unit serves; who holds goods, their quality by biome, the keep,
    the recipe and the bonuses they give.
    """

    kind: Name
    property: Name | None = None
    weight_kg: Positive
    spoils: Duration | None = None
    wears: dict[Name, Positive] = Field(default_factory=dict)
    held: Name = COMMON
    quality: dict[Name, Quality] = Field(default_factory=dict)
    keep: Keep | None = None
    made: dict[Name, Positive] = Field(default_factory=dict)
    sickens: Share | None = None
    reserve: bool = False
    gives: tuple[Bonus, ...] = ()

    @model_validator(mode='after')
    def _keeps_or_wears(self) -> Self:
        if self.kind not in KINDS:
            raise ValueError(f'a kind of {", ".join(KINDS)}')
        if self.spoils is not None and self.spoils.amount == 0:
            raise ValueError('a time to spoil that is not zero')
        if self.kind != GOODS and (self.spoils is None or self.wears):
            raise ValueError('a time to spoil, and no uses to wear by, for food and water')
        if self.kind == GOODS and self.spoils is None and not self.wears:
            raise ValueError('a time to spoil or the uses to wear by')
        for use in self.wears:
            if use not in USES:
                raise ValueError(f'uses to wear by of {", ".join(USES)}')
        if self.held not in HOLDERS:
            raise ValueError(f'held as one of {", ".join(HOLDERS)}')
        if self.kind != GOODS and (self.quality or self.gives or self.held != COMMON):
            raise ValueError('a holder, quality and bonuses for goods only')
        if self.kind not in (GOODS, KINDS[0]) and (self.keep or self.made):
            raise ValueError('a keep and a recipe for goods and food only')
        if self.reserve and self.kind != KINDS[0]:
            raise ValueError('a reserve of food only')
        return self

    @builtins.property
    def land(self) -> str:
        """
        The property of the land a gathered resource is taken by.
        """
        if self.property is None:
            raise ValueError('a resource that is not gathered')
        return self.property


class Border(Node):
    """
    Where a band would rather start: on a cell of a biome of `cell` beside one of `beside`, better with one of
    `stone` within `within` cells. Not `on`: YAML reads a key on as true.
    """

    cell: tuple[Name, ...] = Field(min_length=1)
    beside: tuple[Name, ...] = Field(min_length=1)
    stone: tuple[Name, ...] = ()
    within: Count = 1


class Start(Node):
    population: Count
    stores: dict[Name, Factor]
    biomes: tuple[Name, ...] = Field(min_length=1)
    stage: Name
    oldest: Duration | None = None
    border: Border | None = None


class Wellbeing(Node):
    food: Factor
    water: Factor
    safety: Factor
    rest: Factor

    @model_validator(mode='after')
    def _weighed(self) -> Self:
        if self.food + self.water + self.safety + self.rest <= 0:
            raise ValueError('at least one weight above 0')
        return self


class Population(Node):
    least: Count
    wellbeing: Wellbeing


class Vulnerability(Node):
    """
    How much a member of a stage dies or is hurt of each cause, against an adult's 1.
    """

    encounter: Factor
    frailty: Factor
    injury: Factor


class Reserve(Node):
    """
    The days a member of a stage lives on without food and without water once it ate and drank in full; a stage
    that grows nears the next stage's reserve over its span.
    """

    food: Positive
    water: Positive
    grows: bool = Field(default=False, strict=True)


class LifeStage(Node):
    """
    A stage of life up to an age; the last one lasts to the end. The factors weigh a member against an adult.
    A stage that settles dies by its own weights at its start and nears the next stage's, halving the difference
    every span of settles.
    """

    until: Duration | None = None
    settles: Duration | None = None
    gathers: Factor
    carries: Factor
    eats: Factor
    pace: Positive
    tires: Factor
    conceives: bool = Field(strict=True)
    votes: bool = Field(strict=True)
    dies: Vulnerability
    reserve: Reserve


class Ageing(Node):
    """
    The yearly chance of dying of age from an age on, doubling every span.
    """

    begins: Duration
    per_year: Share
    doubles: Duration

    @model_validator(mode='after')
    def _doubles(self) -> Self:
        if self.doubles.amount == 0:
            raise ValueError('a span to double that is not zero')
        return self


class Severity(Node):
    """
    How long a wound of a severity lasts in days of healing, the share of pace and gathering it leaves, and the
    share of the days left a cure leaves; a wound a cure does not shorten is not treated.
    """

    days: Count
    pace: Annotated[float, Field(strict=True, gt=0, le=1)]
    gathers: Share
    treated: Share = 1.0


class Injury(Node):
    """
    The daily chance of a member to be hurt, the severities a wound is drawn from and how much faster a day in
    camp heals it.
    """

    per_day: Share
    heal_in_camp: Annotated[float, Field(strict=True, ge=1, allow_inf_nan=False)]
    severities: dict[Name, Severity] = Field(min_length=1)
    drawn: dict[Name, Factor]


class Shelter(Node):
    """
    The share of the deaths of an encounter and of frailty a band still meets in camp.
    """

    encounter: Share
    frailty: Share


class Offered(Node):
    """
    When a winter camp is offered: in its seasons and in the days before the first of them begins.
    """

    seasons: tuple[Name, ...] = Field(min_length=1)
    before: Duration


class Drying(Node):
    """
    The food left over a day's ration that dries by itself at the end of a day of these seasons into a reserve, a
    unit of it feeding keeps of a ration, for a band that knows how to make that reserve.
    """

    of: Name
    into: Name
    keeps: Share
    seasons: tuple[Name, ...] = Field(min_length=1)


class WinterCamp(Node):
    """
    A camp built for the cold in days of work without gathering, gathered around within reach, a cell away
    giving afar of a gathering. Once built, while the band stands on its cell staying in it is worth kept more
    to the others, the threat, the spoiling and the eating are multiplied by their factors, and so is what a
    camp takes off fatigue; nothing kept in it weighs. It is never offered on land whose threat, with the dread
    of the band and what its guard leaves, reaches unsafe. Only in its seasons does a band range around it and
    keep to a built one while leaving would drop food.
    """

    offered: Offered
    seasons: tuple[Name, ...] = Field(min_length=1)
    unsafe: Share
    build: Duration
    reach: Span
    afar: Share
    kept: Factor
    threat: Share
    spoil: Share
    consumption: Share
    rest: Factor

    @model_validator(mode='after')
    def _built(self) -> Self:
        if self.build.amount == 0:
            raise ValueError('a build that takes some time')
        return self


class Pause(Node):
    min: Duration
    max: Duration


class Attended(Node):
    """
    A birth a midwife attends: the chance the child lives, and what is left of the mother's risk.
    """

    survives: Share
    mother: Factor


class Midwife(Attended):
    """
    The births the band's midwife attends, and those she attends with a herb spent on them.
    """

    herb: Attended


class Birth(Node):
    pregnancy: Duration
    pause: Pause
    conceive_per_day: Share
    stores: Duration
    child_survives: Share
    mother_dies: Share
    midwife: Midwife


class Dread(Node):
    """
    The threat an encounter that hurt the band adds to its cell in the band's eyes, gone after a span.
    """

    encounter: Share
    lasts: Duration

    @model_validator(mode='after')
    def _lasts(self) -> Self:
        if self.lasts.amount == 0:
            raise ValueError('a span that is not zero')
        return self


class Unease(Node):
    """
    What a day on a dangerous cell adds to the unease of a band, and the share of it a day takes away.
    """

    gain: Factor
    fade: Share


class Route(Node):
    """
    What a step into a cell costs a band on its way: the box searched around the band and its target, and
    the weights of the threat and of the food and water a cell lacks.
    """

    margin: Span
    threat: Factor
    hunger: Factor
    thirst: Factor


class Role(Node):
    """
    What a member does for the band: the share of a gathering it brings, and for a role that cares, one member
    of it for every so many children. A role with a share takes up to that share of the band, each member holding
    the good it needs, and lays its bonuses on the band by the share of it filled.
    """

    gathers: Factor
    cares: Count | None = None
    share: Share | None = None
    needs: Name | None = None
    gives: tuple[Bonus, ...] = ()


class Leaves(Node):
    """
    A member of a role that cares leaves the children to gather, one a day, while a member went short of food or
    water that day; one comes back a day while the stores of both still feed the band `back` days.
    """

    back: Duration


class Weakened(Node):
    """
    The share of pace and gathering a hungry or thirsty member keeps.
    """

    pace: Annotated[float, Field(strict=True, gt=0, le=1)]
    gathers: Share


class Sickness(Node):
    """
    How long a sick member stays sick, the share of pace and gathering it keeps, and how much more it dies of
    frailty.
    """

    lasts: Duration
    pace: Annotated[float, Field(strict=True, gt=0, le=1)]
    gathers: Share
    frailty: Factor


class Exposure(Node):
    """
    What the goods of a member leave of its weight for a cause of death; 1 without them.
    """

    encounter: Factor
    frailty: Factor


class Fed(Node):
    """
    What a ration of meat alone makes of a member: its weight for frailty, the pace its wounds heal and its carry.
    """

    frailty: Factor
    heals: Factor
    carries: Factor


class Diet(Node):
    """
    The share of meat in the rations of a member: the food that is meat, the share of its past share a day keeps,
    and what meat alone does; a share of meat does that share of it.
    """

    meat: Name
    keeps: Share
    full: Fed


class People(Node):
    stages: dict[Name, LifeStage] = Field(min_length=1)
    age: Ageing
    injury: Injury
    birth: Birth
    weakened: Weakened
    roles: dict[Name, Role] = Field(min_length=1)
    leaves: Leaves
    sickness: Sickness
    exposure: Exposure
    diet: Diet


class Speed(Node):
    base: Positive
    slowdown: Factor
    slowest: Positive


class Fatigue(Node):
    """
    What a tick of each action adds, and the share of its pace and its gathering a band loses at fatigue 1.
    """

    move: Amount
    roam: Amount
    gather: Amount
    camp: Amount
    build: Amount
    slows: Share


class Roaming(Node):
    """
    Walking while foraging: slower than a walk, taking a share of a gathering tick of all the cell ahead gives;
    a band whose hunger or thirst reaches hunger only roams.
    """

    speed: Share
    share: Share
    hunger: Share


class Tiredness(Node):
    begins: Share
    ends: Share

    @model_validator(mode='after')
    def _ends_below(self) -> Self:
        if self.ends >= self.begins:
            raise ValueError('ends below begins')
        return self


class States(Node):
    tiredness: Tiredness


class Weights(Node):
    hunger: Factor
    thirst: Factor
    goods: Factor
    safety: Factor
    move: Factor
    momentum: Factor
    intent: Factor
    back: Factor
    visited: Share


class Stage(Node):
    """
    One level of hunger or thirst: the need it gives from the days in the stores up.
    """

    days: Factor
    need: Share


class Decisions(Node):
    levels: dict[Name, Stage]
    distance: Factor
    distance_known: Factor
    horizon: Span
    unknown: dict[Name, Share]
    unknown_seasons: dict[Name, dict[Name, Factor]] = Field(default_factory=dict)
    idle: Factor
    wander: Duration
    weights: Weights

    @model_validator(mode='after')
    def _levelled(self) -> Self:
        days = [level.days for level in self.levels.values()]
        if 0 not in days or len(set(days)) != len(days):
            raise ValueError('levels with days that differ, one of them 0')
        return self


class Threat(Node):
    """
    What the guard of the band leaves of the threat of encounters and of the safety of wellbeing, in camp and on
    the march; goods held lower it.
    """

    camp: Factor
    march: Factor


class Mastery(Node):
    """
    How a maker's experience of a good becomes mastery, half of it at `half` goods made, and the share of the
    materials' quality a maker with none gives a good.
    """

    half: Positive
    floor: Share


class Making(Node):
    """
    The makers of a good in a camp part, the most experienced first, and what each makes of it.
    """

    per_part: Factor
    hands: Count
    mastery: Mastery


class Hunting(Node):
    """
    The meat a hunter brings in a tick on a cell of full game, and the hides a kilo of meat gives.
    """

    meat: Factor
    hides: Factor


class Band(Node):
    start: Start
    population: Population
    people: People
    carry_kg: Positive
    carry_water_kg: Factor
    gathering: dict[Name, Factor]
    gathering_beside: Share
    consumption_per_day: dict[Name, Factor]
    speed: Speed
    roaming: Roaming
    fatigue: Fatigue
    camp_parts: tuple[Name, ...]
    making: Making
    hunting: Hunting
    states: States
    sight: Span
    memory: Duration | None = None
    decisions: Decisions
    dread: Dread
    unease: Unease
    route: Route
    shelter: Shelter
    winter_camp: WinterCamp
    drying: Drying
    threat: Threat


class Units(Node):
    """
    One field per kind of unit, read by name as well: units['band'].
    """

    band: Band

    def __getitem__(self, name: str) -> Band:
        if name not in type(self).model_fields:
            raise KeyError(name)
        unit: Band = getattr(self, name)
        return unit


class Voice(Node):
    share: Share
    least: Annotated[float, Field(strict=True, gt=1, allow_inf_nan=False)]


class Judgement(Node):
    slack: Factor


class Status(Node):
    start: Points
    abstained: Amount
    outvoted: Amount
    go_worked: Amount
    go_failed: Amount
    go_even: Amount
    stay_worked: Amount
    stay_failed: Amount
    stay_even: Amount
    camp_worked: Amount
    camp_failed: Amount
    camp_even: Amount
    death: Amount
    birth: Amount


class Council(Node):
    part: Name
    spread: Positive
    voice: Voice
    judgement: Judgement
    memory: Duration
    status: Status
    blamed: tuple[Name, ...]


class Loss(Node):
    """
    The share of the people an encounter takes, drawn between the two bounds.
    """

    min: Share
    max: Share

    @model_validator(mode='after')
    def _ordered(self) -> Self:
        if self.min > self.max:
            raise ValueError('min not above max')
        return self


class Encounter(Node):
    """
    A kind of encounter. It fits a cell of one of its biomes, or one with a river when rivers is set;
    with neither it fits anywhere. Actions and resources left empty fit any; wounds left empty are drawn as
    units.band.people.injury.drawn. One that sickens leaves sick instead of dead those a cure held saves.
    """

    weight: Positive
    loss: Loss
    injured: Loss = Loss(min=0.0, max=0.0)
    wounds: dict[Name, Factor] = {}
    biomes: tuple[Name, ...] = ()
    rivers: bool = Field(default=False, strict=True)
    actions: tuple[Name, ...] = ()
    resources: tuple[Name, ...] = ()
    sickens: bool = Field(default=False, strict=True)


class Encounters(Node):
    chance: Share
    actions: dict[Name, Factor]
    kinds: dict[Name, Encounter]


class Condition(Node):
    """
    What teaches a skill, one of four: a counter of the band at least so high, of one biome, the sum of several
    or, with biome new, the most of those not seen on the first day; the resources held at once; any or all of
    other conditions.
    """

    counter: Name | None = None
    biome: Name | None = None
    biomes: tuple[Name, ...] = ()
    season: Name | None = None
    at_least: Positive | None = None
    holds: dict[Name, Positive] = Field(default_factory=dict)
    knows: tuple[Name, ...] = ()
    any: tuple[Condition, ...] = ()
    all: tuple[Condition, ...] = ()

    @model_validator(mode='after')
    def _one_kind(self) -> Self:
        kinds = [self.counter is not None, bool(self.holds), bool(self.knows), bool(self.any), bool(self.all)]
        if sum(kinds) != 1:
            raise ValueError('exactly one of counter, holds, knows, any, all')
        if (self.counter is None) != (self.at_least is None):
            raise ValueError('at_least with a counter and only with one')
        if self.biome is not None and self.biomes:
            raise ValueError('biome or biomes, not both')
        if self.counter is None and (self.biome is not None or self.biomes or self.season is not None):
            raise ValueError('biomes and a season only with a counter')
        return self

    def walk(self) -> list[Condition]:
        """
        This condition and every one below it.
        """
        return [self, *(held for below in (*self.any, *self.all) for held in below.walk())]


class Opens(Node):
    proposals: tuple[Name, ...] = ()
    gathers: tuple[Name, ...] = ()
    makes: tuple[Name, ...] = ()
    roles: tuple[Name, ...] = ()


class Skill(Node):
    """
    What a band learns by living: learned when its condition holds and the skills it needs are known, counted
    from the day they were; it opens proposals, gatherings, recipes and roles.
    """

    learned: Condition
    needs: tuple[Name, ...] = ()
    opens: Opens = Opens()


class Mind(Node):
    """
    A player of the seat that scores every option by its weights times the features it names: docs/lab/players.md,
    The mind. `trained` tells the reader how the weights were found.
    """

    features: tuple[Name, ...] = Field(min_length=1)
    weights: tuple[Amount, ...]
    trained: dict[Name, str | int | float] = Field(default_factory=dict)

    @model_validator(mode='after')
    def _weighed(self) -> Self:
        if any(name not in FEATURES for name in self.features) or len(set(self.features)) < len(self.features):
            raise ValueError(f'each of {", ".join(FEATURES)} at most once')
        if len(self.weights) != len(self.features):
            raise ValueError('as many weights as features')
        return self


class Params(Node):
    """
    The resolved tree. A new section is a field here and a file in defaults.
    """

    time: Time
    eras: Eras
    planet: Planet
    biomes: dict[Name, Biome]
    resources: dict[Name, Resource]
    units: Units
    council: Council
    encounters: Encounters
    skills: dict[Name, Skill]
    # A tree written before the minds were has none.
    minds: dict[Name, Mind] = Field(default_factory=dict)

    @model_validator(mode='after')
    def _agree(self) -> Self:
        self._check_names()
        self._check_ticks()
        self._check_biomes()
        self._check_generation()
        self._check_planet()
        self._check_window()
        self._check_resources()
        self._check_eras()
        self._check_band()
        self._check_council()
        self._check_encounters()
        self._check_skills()
        for name, resource in self.resources.items():
            self._check_goods(name, resource)
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
                gathered = [name for name, held in self.resources.items() if held.property is not None]
                for resource in given.resources:
                    if resource not in gathered:
                        raise _invalid(f'{path}.{era}.resources', resource, f'one of {", ".join(gathered)}')
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

    def _check_resources(self) -> None:
        eras: dict[str, Era] = dict(self.eras)
        for name, resource in self.resources.items():
            for era, held in eras.items():
                if resource.property is not None and resource.property not in held.properties:
                    expected = f'a property of the era {era}: {", ".join(held.properties)}'
                    raise _invalid(f'resources.{name}.property', resource.property, expected)

    def _check_goods(self, name: str, resource: Resource) -> None:
        path, seasons = f'resources.{name}', [season.name for season in self.time.seasons]
        if resource.keep is not None and resource.keep.per not in PER:
            raise _invalid(f'{path}.keep.per', resource.keep.per, f'one of {", ".join(PER)}')
        for biome in resource.quality:
            given = self.biomes.get(biome)
            prop = resource.property
            held = None if given is None or prop is None else given.eras[BAND].properties[prop]
            if held is None or held.base <= 0:
                raise _invalid(f'{path}.quality', biome, f'a biome that gives the property {resource.property}')
        for material in resource.made:
            if material not in self.resources or material == name:
                others = [held for held in self.resources if held != name]
                raise _invalid(f'{path}.made', material, f'one of {", ".join(others)}')
        for bonus in resource.gives:
            if bonus.to not in TO or (bonus.to == TO[1] and resource.held != PERSONAL):
                raise _invalid(f'{path}.gives.to', bonus.to, f'one of {", ".join(TO)}, a member for personal goods')
            if bonus.sex is not None and bonus.sex not in SEXES:
                raise _invalid(f'{path}.gives.sex', bonus.sex, f'one of {", ".join(SEXES)}')
            for season in bonus.seasons:
                if season not in seasons:
                    raise _invalid(f'{path}.gives.seasons', season, f'one of {", ".join(seasons)}')
            if not self._holds_number(bonus):
                expected = 'a path of the tree that holds a number, or a span for a plus of a span'
                raise _invalid(f'{path}.gives.path', bonus.path, expected)

    def _holds_number(self, bonus: Bonus) -> bool:
        node: Any = self
        for name in bonus.path.split('.'):
            if isinstance(node, dict):
                node = node.get(name)
            else:
                node = getattr(node, name) if isinstance(node, BaseModel) and name in type(node).model_fields else None
        span = isinstance(node, Duration)
        number = isinstance(node, int | float) and not isinstance(node, bool)
        return (span or number) and (bonus.plus is None or isinstance(bonus.plus, Duration) == span)

    def _check_eras(self) -> None:
        seasons = [season.name for season in self.time.seasons]
        for era, held in self.eras:
            for section in ('capacity', 'recovery'):
                for prop in getattr(held, section):
                    if prop not in held.properties:
                        raise _invalid(f'eras.{era}.{section}', prop, f'one of {", ".join(held.properties)}')
            for prop, paces in held.recovery.items():
                for season in paces:
                    if season not in seasons:
                        raise _invalid(f'eras.{era}.recovery.{prop}', season, f'one of {", ".join(seasons)}')

    def _check_band(self) -> None:
        band, known = self.units.band, ', '.join(self.resources)
        for section in ('gathering', 'consumption_per_day'):
            for resource in getattr(band, section):
                if resource not in self.resources:
                    raise _invalid(f'units.band.{section}', resource, f'one of {known}')
        for resource in band.gathering:
            if self.resources[resource].property is None:
                raise _invalid('units.band.gathering', resource, 'a resource gathered by a property of the land')
        for resource in HUNTED:
            if resource not in self.resources:
                raise _invalid('resources', sorted(self.resources), f'the resources {", ".join(HUNTED)} a hunt brings')
        start = band.start
        if start.population < band.population.least:
            expected = f'at least the {band.population.least} people of population.least'
            raise _invalid('units.band.start.population', start.population, expected)
        for resource in start.stores:
            if resource not in self.resources:
                raise _invalid('units.band.start.stores', resource, f'one of {known}')
        weight = sum(amount * self.resources[resource].weight_kg for resource, amount in start.stores.items())
        carried = start.population * band.carry_kg
        if weight > carried:
            raise _invalid('units.band.start.stores', dict(start.stores), f'up to the {carried:g} kg the band carries')
        for name in start.biomes:
            if name not in self.biomes:
                raise _invalid('units.band.start.biomes', name, f'one of {", ".join(sorted(self.biomes))}')
            walked = self.biomes[name].eras[BAND].properties.get(PASSABILITY)
            if walked is not None and walked.base == 0:
                raise _invalid('units.band.start.biomes', name, 'a biome that can be entered')
        border = start.border
        named = () if border is None else (('cell', border.cell), ('beside', border.beside), ('stone', border.stone))
        for field, names in named:
            for name in names:
                if name not in self.biomes:
                    raise _invalid(f'units.band.start.border.{field}', name, f'one of {", ".join(sorted(self.biomes))}')
            if field == 'cell' and any(name not in start.biomes for name in names):
                raise _invalid('units.band.start.border.cell', list(names), 'biomes of units.band.start.biomes')
        for part in band.camp_parts:
            if part not in self.time.day_parts:
                expected = f'one of {", ".join(self.time.day_parts)}'
                raise _invalid('units.band.camp_parts', part, expected)
        seasons = [season.name for season in self.time.seasons]
        for path, listed in (
            ('units.band.winter_camp.offered.seasons', band.winter_camp.offered.seasons),
            ('units.band.winter_camp.seasons', band.winter_camp.seasons),
            ('units.band.drying.seasons', band.drying.seasons),
        ):
            for wanted in listed:
                if wanted not in seasons:
                    raise _invalid(path, wanted, f'one of {", ".join(seasons)}')
        drying = band.drying
        for field, name in (('of', drying.of), ('into', drying.into)):
            if name not in self.resources:
                raise _invalid(f'units.band.drying.{field}', name, f'one of {", ".join(self.resources)}')
        if not self.resources[drying.into].reserve:
            raise _invalid('units.band.drying.into', drying.into, 'a reserve of food')
        for prop in band.decisions.unknown:
            for era, held in self.eras:
                if prop not in held.properties:
                    expected = f'a property of the era {era}: {", ".join(held.properties)}'
                    raise _invalid('units.band.decisions.unknown', prop, expected)
        for season, factors in band.decisions.unknown_seasons.items():
            if season not in seasons:
                raise _invalid('units.band.decisions.unknown_seasons', season, f'one of {", ".join(seasons)}')
            for prop in factors:
                if prop not in band.decisions.unknown:
                    expected = f'one of {", ".join(band.decisions.unknown)}'
                    raise _invalid(f'units.band.decisions.unknown_seasons.{season}', prop, expected)
        self._check_people()

    def _check_people(self) -> None:
        people, path = self.units.band.people, 'units.band.people'
        names = list(people.stages)
        last = names[-1]
        until = 0
        for name, stage in people.stages.items():
            if (stage.until is None) != (name == last):
                raise _invalid(f'{path}.stages.{name}.until', stage.until, 'an age for every stage but the last')
            if stage.until is not None:
                if self.days(stage.until) <= until:
                    raise _invalid(f'{path}.stages.{name}.until', stage.until, 'an age above the stage before')
                until = self.days(stage.until)
            if stage.settles is not None and (name == last or self.days(stage.settles) <= 0):
                expected = 'a span above 0 on a stage before the last'
                raise _invalid(f'{path}.stages.{name}.settles', stage.settles.model_dump(), expected)
            if stage.reserve.grows and name == last:
                raise _invalid(f'{path}.stages.{name}.reserve.grows', True, 'a stage before the last')
        if not any(stage.conceives for stage in people.stages.values()):
            raise _invalid(f'{path}.stages', names, 'a stage that conceives')
        start = self.units.band.start.stage
        if start not in names[:-1]:
            raise _invalid('units.band.start.stage', start, f'one of {", ".join(names[:-1])}')
        oldest = self.units.band.start.oldest
        youngest = 0
        for name, stage in people.stages.items():
            if name == start:
                break
            youngest = self.days(stage.until) if stage.until is not None else youngest
        if oldest is not None and self.days(oldest) <= youngest:
            raise _invalid('units.band.start.oldest', oldest.model_dump(), 'an age above the start of the start stage')
        pause = people.birth.pause
        if self.days(pause.min) > self.days(pause.max):
            raise _invalid(f'{path}.birth.pause', pause.model_dump(), 'min not above max')
        self._check_wounds(f'{path}.injury.drawn', people.injury.drawn)
        common = [name for name, role in people.roles.items() if role.cares is None and role.share is None]
        if len(common) != 1:
            raise _invalid(f'{path}.roles', common, 'exactly one role that cares for nobody and has no share')
        eaten = self.resources.get(people.diet.meat)
        if eaten is None or eaten.kind != KINDS[0]:
            foods = [name for name, resource in self.resources.items() if resource.kind == KINDS[0]]
            raise _invalid(f'{path}.diet.meat', people.diet.meat, f'one of {", ".join(foods)}')
        for name, role in people.roles.items():
            needed = None if role.needs is None else self.resources.get(role.needs)
            if role.needs is not None and (needed is None or needed.held != PERSONAL):
                personal = [held for held, resource in self.resources.items() if resource.held == PERSONAL]
                raise _invalid(f'{path}.roles.{name}.needs', role.needs, f'one of {", ".join(personal)}')
            for bonus in role.gives:
                if bonus.to != TO[0] or bonus.sex is not None:
                    raise _invalid(f'{path}.roles.{name}.gives.to', bonus.to, f'{TO[0]}, of no sex')
                if not self._holds_number(bonus):
                    expected = 'a path of the tree that holds a number, or a span for a plus of a span'
                    raise _invalid(f'{path}.roles.{name}.gives.path', bonus.path, expected)

    def _check_wounds(self, path: str, weights: dict[str, float]) -> None:
        severities = self.units.band.people.injury.severities
        for name in weights:
            if name not in severities:
                raise _invalid(path, name, f'one of {", ".join(severities)}')
        if sum(weights.values()) <= 0:
            raise _invalid(path, dict(weights), 'at least one weight above 0')

    def _check_council(self) -> None:
        if self.council.part not in self.time.day_parts:
            raise _invalid('council.part', self.council.part, f'one of {", ".join(self.time.day_parts)}')
        for cause in self.council.blamed:
            if cause not in CAUSES:
                raise _invalid('council.blamed', cause, f'one of {", ".join(CAUSES)}')

    def _check_encounters(self) -> None:
        for action in self.encounters.actions:
            if action not in ACTIONS:
                raise _invalid('encounters.actions', action, f'one of {", ".join(ACTIONS)}')
        known = {'biomes': sorted(self.biomes), 'actions': list(ACTIONS), 'resources': list(self.resources)}
        for kind, held in self.encounters.kinds.items():
            for section, names in known.items():
                for name in getattr(held, section):
                    if name not in names:
                        raise _invalid(f'encounters.kinds.{kind}.{section}', name, f'one of {", ".join(names)}')
            if held.wounds:
                self._check_wounds(f'encounters.kinds.{kind}.wounds', held.wounds)

    def _check_skills(self) -> None:
        skills = self.skills
        for name, skill in skills.items():
            path = f'skills.{name}'
            for needed in skill.needs:
                if needed not in skills:
                    raise _invalid(f'{path}.needs', needed, f'one of {", ".join(skills)}')
            for condition in skill.learned.walk():
                self._check_condition(f'{path}.learned', condition)
            known = {
                'proposals': GATES,
                'gathers': tuple(self.resources),
                'makes': tuple(self.resources),
                'roles': tuple(self.units.band.people.roles),
            }
            for section, names in known.items():
                for opened in getattr(skill.opens, section):
                    if opened not in names:
                        raise _invalid(f'{path}.opens.{section}', opened, f'one of {", ".join(names)}')
        for name in skills:
            self._check_needs(name, ())

    def _check_condition(self, path: str, condition: Condition) -> None:
        counter = condition.counter
        if counter is not None and counter not in COUNTERS:
            raise _invalid(f'{path}.counter', counter, f'one of {", ".join(COUNTERS)}')
        biomes = (*condition.biomes, *(() if condition.biome is None else (condition.biome,)))
        if counter in (*TALLIES, *BY_SEASON) and biomes:
            raise _invalid(f'{path}.biome', list(biomes), f'no biome for the counter {counter}')
        if counter in BY_BIOME and not biomes:
            raise _invalid(f'{path}.biome', None, f'a biome for the counter {counter}')
        seasons = [season.name for season in self.time.seasons]
        if counter in BY_SEASON and condition.season not in seasons:
            raise _invalid(f'{path}.season', condition.season, f'one of {", ".join(seasons)}')
        if counter not in BY_SEASON and condition.season is not None:
            raise _invalid(f'{path}.season', condition.season, f'no season for the counter {counter}')
        for skill in condition.knows:
            if skill not in self.skills:
                raise _invalid(f'{path}.knows', skill, f'one of {", ".join(self.skills)}')
        for biome in biomes:
            if biome not in self.biomes and (biome != NEW or condition.biomes):
                raise _invalid(f'{path}.biome', biome, f'one of {", ".join(sorted(self.biomes))}, or {NEW} alone')
        for resource in condition.holds:
            if resource not in self.resources:
                raise _invalid(f'{path}.holds', resource, f'one of {", ".join(self.resources)}')

    def _check_needs(self, name: str, above: tuple[str, ...]) -> None:
        if name in above:
            raise _invalid(f'skills.{above[0]}.needs', name, 'skills that do not need themselves through others')
        for needed in self.skills[name].needs:
            self._check_needs(needed, (*above, name))

    def parts(self, duration: Duration) -> int:
        """
        A duration in parts of a day, by the calendar of this tree.
        """
        day = self.time.parts_per_day
        month = day * self.time.days_per_month
        units = {'parts': 1, 'days': day, 'months': month, 'years': month * self.time.months_per_year}
        return duration.amount * units[duration.unit]

    def days(self, duration: Duration) -> int:
        return self.parts(duration) // self.time.parts_per_day

    @property
    def schema_version(self) -> int:
        return SCHEMA_VERSION

    def tree(self) -> dict[str, Any]:
        return self.model_dump(mode='json')

    @cached_property
    def hash(self) -> str:
        canonical = json.dumps(self.tree(), sort_keys=True, separators=(',', ':'), ensure_ascii=True)
        return hashlib.sha256(canonical.encode()).hexdigest()
