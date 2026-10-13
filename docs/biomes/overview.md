# Biomes

#map #biomes #stage1

A biome is a kind of land. This document says what a biome is made of, how
its properties are read, what a cell remembers and how a new biome is
added. Part of the stage 1 design in [the roadmap](../roadmap.md); how the
land is laid out is told in [Generation](generation.md).

- [The starting set](#the-starting-set)
- [A biome is data](#a-biome-is-data)
- [Properties](#properties)
- [Properties belong to an era](#properties-belong-to-an-era)
- [Base and modifiers](#base-and-modifiers)
- [Seasons](#seasons)
- [Rivers](#rivers)
- [What a cell remembers](#what-a-cell-remembers)
- [Checks](#checks)
- [The map in the API](#the-map-in-the-api)
- [Adding a biome](#adding-a-biome)
- [Open points](#open-points)

___

## The starting set

Nine biomes cover the planet. Six were named by the roadmap; `desert` and
`tundra` are added because a whole planet has dry and cold land, and
without them it would be grass up to the poles.

| Biome                    | What it is                              |
|--------------------------|-----------------------------------------|
| [`grass`](grass.md)      | open land, easy to cross, good forage   |
| [`forest`](forest.md)    | the richest land, slower and less safe  |
| [`hills`](hills.md)      | the belt below the mountains            |
| [`mountain`](mountain.md)| the highest land: poor, slow, dangerous |
| [`outcrops`](outcrops.md)| rocky ground, in small patches          |
| [`water`](water.md)      | sea and lakes; nobody walks here        |
| [`desert`](desert.md)    | dry and warm, nearly empty              |
| [`tundra`](tundra.md)    | the cold belts near the poles           |
| [`swamp`](swamp.md)      | low, wet, warm ground: rich and slow    |

Swamp was left out of the first set on purpose. It is the biome that
closed the stage: added last, by one data file, to prove that nothing else
has to change.

___

## A biome is data

A biome is one file of the defaults, and so an entry of the section
`biomes` in [the tree](../architecture/parameters.md). There is no class
and no line of code per biome.

```yaml
biomes:
  forest:
    colour: '#006400'
    generation:
      order: 70
      moisture: {min: 0.5}
    eras:
      band:
        properties:
          water: {base: 0.6, recovery: {days: 3}}
          food:
            base: 0.9
            recovery: {days: 30}
            seasons:
              spring: {times: 0.7}
              autumn: {times: 1.2}
              winter: {times: 0.4}
          threat: {base: 0.4}
          passability: {base: 0.6}
        resources: [water, forage]
```

| Field        | Holds                                                    |
|--------------|----------------------------------------------------------|
| the key      | the identifier: lower case, the name used everywhere     |
| `colour`     | how a client paints the biome when it has nothing better |
| `generation` | where the biome appears; see [Generation](generation.md#from-layers-to-a-biome) |
| `eras`       | per era: the properties and what can be gathered         |

The name a player reads is not in the file. It is the message
`biome-forest` in the catalogue of each language, as with every other
name the game shows.

Biomes are frozen when a game is created, with the rest of the tree. What
changes while a game runs is the state of cells, never a biome.

___

## Properties

A property is a number from 0 to 1 that says how much of something a cell
of the biome gives. It is a measure, not an amount: how many units of food
a band takes from a cell is a rule of the band, which multiplies its own
rate by the property.

| Property      | 0 means               | 1 means                      |
|---------------|-----------------------|------------------------------|
| `water`       | none to be found      | as much as anybody can carry |
| `food`        | nothing to gather     | the richest land there is    |
| `threat`      | nothing to fear       | an encounter is likely       |
| `passability` | cannot be entered     | crossed at full speed        |

___

## Properties belong to an era

Each era opens its own set of properties on the same biome. The era names
the set, and every biome gives a value for each name in it.

```yaml
eras:
  band:
    properties: [water, food, threat, passability]
```

A band reads `food` as forage. A tribe will read pasture, and a settlement
soil, and those are other numbers on the same forest. Stage 5 adds the
second era and with it the second set; nothing in the model changes.

___

## Base and modifiers

A property is a base value with modifiers laid over it. The biome gives
the base; a season, a river and the state of the cell each add a modifier.

A modifier is one of two kinds.

- **`plus`** adds to the base.
- **`times`** multiplies.

```text
value = (base + every plus) * every times * stock
```

The result is held between 0 and 1. All that is added is added first and
all that multiplies comes after, so the order in which modifiers arrive
never matters.

The value is worked out when it is asked for and stored nowhere. Weather
will later be one more source of modifiers, and needs no new shape.

___

## Seasons

A property may name a modifier per season. The first thing the seasons
change is food; water and movement wait for the band in stage 2.

| Season   | Food in the temperate biomes |
|----------|------------------------------|
| `spring` | times 0.7                    |
| `summer` | as the base                  |
| `autumn` | times 1.2                    |
| `winter` | times 0.4                    |

Each biome carries its own numbers: the desert has no seasons, and the
tundra gives next to nothing in winter. A season with no modifier leaves
the base alone.

The season is the one the calendar names, the same for the whole window;
see [Time](../architecture/time.md#seasons).

___

## Rivers

A river is a mark on a cell, beside its biome. It is a source of
modifiers and nothing more.

| Property      | A river does |
|---------------|--------------|
| `water`       | plus 0.5     |
| `food`        | plus 0.1     |
| `passability` | times 0.7    |
| `threat`      | nothing      |

So a river in the desert is the best water for days around, and a river
anywhere is slower to cross but can be crossed. The numbers are
`planet.rivers.effects`, per era.

___

## What a cell remembers

A cell has a biome, which never changes, and a state, which does. The
state is a **stock** for each property that names a `recovery`: 1 when the
cell is untouched, 0 when it is stripped bare.

- **Gathering lowers the stock.** How much is a rule of the band; stage 1
  only gives the engine the way to lower it.
- **A cell recovers by itself.** `recovery` is the time from bare to full,
  and a cell regains an equal share of it every tick, in the phase
  `world`.
- **The stock is a modifier**: it multiplies the property, as the formula
  above shows.
- **Only touched cells are kept.** A cell whose stocks are all full has no
  state at all, so a snapshot grows with the number of cells in use and
  not with the size of the map.

Properties without a `recovery`, such as `threat`, have no stock.

A cell whose stock moved in a tick is listed in `changes.cells` of the
update, and the stocks are part of the hash of the state. Every kept cell
recovers in every tick, so a cell is listed from the tick it was gathered
from until it is full again, and then dropped.

The engine lowers a stock through `Game.deplete` and reads a property
through `Game.value`; neither is a command. A stock counts as full a hair
below 1, because shares of a recovery time do not always add up to exactly
1.

___

## Checks

A game does not start from biomes that do not add up. Each failure is the
message `error-params-invalid` with the path of the value.

- Every biome gives exactly the properties its era names, for every era.
- A base lies between 0 and 1, a `times` is not negative.
- A season named by a modifier exists in `time.seasons`.
- A resource named by a biome is one the game knows.
- Orders of generation do not repeat, and one biome has no ranges.
- A range names `min`, `max` or both, and `min` is not above `max`.
- A recovery takes time: a length of zero is refused.
- A colour is written as `#rrggbb`.

___

## The map in the API

A client reads the biomes of a game and then the map in rectangles.

```text
/api/v1/games/7f3a9c1e/biomes
```

```json
{
  "era": "band",
  "biomes": [
    {
      "id": "forest",
      "name": {"key": "biome-forest", "values": {}},
      "colour": "#006400",
      "properties": {"water": 0.6, "food": 0.9, "threat": 0.4, "passability": 0.6},
      "resources": ["water", "forage"]
    }
  ]
}
```

The properties here are the bases of the current era, and the biomes come
in their order of generation. The rectangle of the map carries the rivers
and the stocks, each in the order of `cells`.

```json
{
  "scale": 0,
  "x": 2040, "y": 610, "width": 64, "height": 64,
  "biomes": ["water", "mountain", "hills", "forest", "grass"],
  "cells": [4, 4, 3, 3, 0],
  "rivers": [0, 0, 1, 0, 0],
  "water": [1.0, 1.0, 1.0, 1.0, 1.0],
  "food": [1.0, 0.8, 1.0, 0.4, 1.0]
}
```

`biomes` lists every biome of the game, so an index is the same in every
rectangle. A stock is one list per property that some biome lets recover,
`water` and `food` in the band era.

A change of a stock arrives in an update, as the whole new state of the
cell: every stock of the era, 1 for one that is full or that the biome
does not keep.

```json
{"cells": [{"x": 2301, "y": 744, "water": 1.0, "food": 0.4}]}
```

[The protocol](../api/protocol.md#the-map) holds the full description.

___

## Adding a biome

A new biome takes a data file, its name in two languages and a test.
Nothing in the engine, the generator or the API is edited.

1. Write `src/dominion_theory/content/defaults/biomes/<id>.yaml`, with an
   order that puts it before the biomes it should win against.
2. Add the message `biome-<id>` to the English and the Russian catalogue.
3. Write `docs/biomes/<id>.md` and a row in the tables of this document
   and of [Generation](generation.md#from-layers-to-a-biome).
4. Add one test: layers that meet the rule give the biome.

The tests that every biome has all its properties and its name in both
catalogues take the new file in by themselves. The tests that spell out
the whole list of biomes in order gain the new name.

[`swamp`](swamp.md) was added this way, and `make map` shows where a new
biome lands; see [Setup](../dev/setup.md#look-at-a-map).

___

## Open points

- **Resources** - a biome lists what can be gathered on it, and for now
  the game knows two names, `water` and `forage`. Stage 2 makes them
  entries of the section `resources`, with weight and spoiling.
- **Sea and lake** - both are `water`, and its property `water` is 1.
  When a band may drink from a neighbouring cell, the sea has to stop
  being drinkable.
- **Recovery by season** - a cell recovers at the same pace all year.
  Whether nothing grows back in winter is set with the band's rates in
  stage 2.
- **Seasons away from the temperate belt** - one season holds for the
  whole window. A window that reaches from the tundra to the desert needs
  the season to depend on the place.
