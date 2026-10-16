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
LAYERS = ('elevation', 'relief', 'moisture', 'temperature', 'flow')
ACTIONS = ('move', 'roam', 'gather', 'camp')
CAUSES = ('hunger', 'thirst', 'encounter', 'age', 'frailty', 'birth')
BAND = 'band'
PASSABILITY = 'passability'
ZOOM = 5

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


class Resource(Node):
    """
    Something a band gathers and carries: the property of a cell it is taken by, its weight, how long it keeps.
    """

    property: Name
    weight_kg: Positive
    spoils: Duration

    @model_validator(mode='after')
    def _keeps_for_a_time(self) -> Self:
        if self.spoils.amount == 0:
            raise ValueError('a time to spoil that is not zero')
        return self


class Start(Node):
    population: Count
    stores: dict[Name, Factor]
    biomes: tuple[Name, ...] = Field(min_length=1)
    stage: Name
    oldest: Duration | None = None


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

    hunger: Factor
    thirst: Factor
    encounter: Factor
    frailty: Factor
    injury: Factor


class LifeStage(Node):
    """
    A stage of life up to an age; the last one lasts to the end. The factors weigh a member against an adult.
    """

    until: Duration | None = None
    gathers: Factor
    carries: Factor
    eats: Factor
    pace: Positive
    tires: Factor
    conceives: bool = Field(strict=True)
    votes: bool = Field(strict=True)
    dies: Vulnerability


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


class Injury(Node):
    per_day: Share
    lasts: Duration
    gathers: Share
    pace: Annotated[float, Field(strict=True, gt=0, le=1)]


class Pause(Node):
    min: Duration
    max: Duration


class Birth(Node):
    pregnancy: Duration
    pause: Pause
    conceive_per_day: Share
    days: Factor
    child_survives: Share
    mother_dies: Share


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


class People(Node):
    stages: dict[Name, LifeStage] = Field(min_length=1)
    age: Ageing
    injury: Injury
    birth: Birth


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
    slows: Share


class Roaming(Node):
    """
    Walking while foraging: slower than a walk, taking a share of a gathering tick of all the cell ahead gives;
    a band whose hunger or thirst reaches hunger only roams.
    """

    speed: Share
    share: Share
    hunger: Share


class Hardship(Node):
    after: Duration
    loss_per_day: Share


class Tiredness(Node):
    begins: Share
    ends: Share

    @model_validator(mode='after')
    def _ends_below(self) -> Self:
        if self.ends >= self.begins:
            raise ValueError('ends below begins')
        return self


class States(Node):
    short: Share
    starvation: Hardship
    thirst: Hardship
    tiredness: Tiredness


class Weights(Node):
    hunger: Factor
    thirst: Factor
    safety: Factor
    move: Factor
    momentum: Factor
    intent: Factor


class Stage(Node):
    """
    One level of hunger or thirst: the need it gives from the days in the stores up.
    """

    days: Factor
    need: Share


class Decisions(Node):
    levels: dict[Name, Stage]
    distance: Factor
    horizon: Span
    unknown: dict[Name, Share]
    idle: Factor
    wander: Duration
    weights: Weights

    @model_validator(mode='after')
    def _levelled(self) -> Self:
        days = [level.days for level in self.levels.values()]
        if 0 not in days or len(set(days)) != len(days):
            raise ValueError('levels with days that differ, one of them 0')
        return self


class Band(Node):
    start: Start
    population: Population
    people: People
    carry_kg: Positive
    gathering: dict[Name, Factor]
    consumption_per_day: dict[Name, Factor]
    speed: Speed
    roaming: Roaming
    fatigue: Fatigue
    camp_parts: tuple[Name, ...]
    states: States
    sight: Span
    memory: Duration
    decisions: Decisions
    dread: Dread
    unease: Unease
    route: Route


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
    disaster: Share
    slack: Factor


class Status(Node):
    start: Points
    abstained: Amount
    outvoted: Amount
    go_worked: Amount
    go_failed: Amount
    go_disaster: Amount
    go_even: Amount
    stay_worked: Amount
    stay_failed: Amount
    stay_disaster: Amount
    stay_even: Amount
    death: Amount
    birth: Amount


class Council(Node):
    part: Name
    spread: Positive
    voice: Voice
    judgement: Judgement
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
    with neither it fits anywhere. Actions and resources left empty fit any.
    """

    weight: Positive
    loss: Loss
    injured: Loss = Loss(min=0.0, max=0.0)
    biomes: tuple[Name, ...] = ()
    rivers: bool = Field(default=False, strict=True)
    actions: tuple[Name, ...] = ()
    resources: tuple[Name, ...] = ()


class Encounters(Node):
    chance: Share
    actions: dict[Name, Factor]
    kinds: dict[Name, Encounter]


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
                    if resource not in self.resources:
                        raise _invalid(f'{path}.{era}.resources', resource, f'one of {", ".join(self.resources)}')
                if given.shore and PASSABILITY in given.properties and given.properties[PASSABILITY].base == 0:
                    below = f'{path}.{era}.properties.{PASSABILITY}.base'
                    raise _invalid(below, 0.0, 'a shore that can be entered')
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
                if resource.property not in held.properties:
                    expected = f'a property of the era {era}: {", ".join(held.properties)}'
                    raise _invalid(f'resources.{name}.property', resource.property, expected)

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
        for part in band.camp_parts:
            if part not in self.time.day_parts:
                expected = f'one of {", ".join(self.time.day_parts)}'
                raise _invalid('units.band.camp_parts', part, expected)
        for prop in band.decisions.unknown:
            for era, held in self.eras:
                if prop not in held.properties:
                    expected = f'a property of the era {era}: {", ".join(held.properties)}'
                    raise _invalid('units.band.decisions.unknown', prop, expected)
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
