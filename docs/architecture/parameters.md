# Parameters

#architecture #parameters #stage0

Every number that shapes a game lives in one tree of named values. This
document says what goes into the tree, how a game gets its own copy and how
the code reads it. Part of the stage 0 design in
[the roadmap](../roadmap.md).

- [Why one tree](#why-one-tree)
- [Parameters and settings](#parameters-and-settings)
- [What the tree holds](#what-the-tree-holds)
- [Where the values come from](#where-the-values-come-from)
- [Checking the tree](#checking-the-tree)
- [A tree is fixed for the game](#a-tree-is-fixed-for-the-game)
- [Reading parameters in code](#reading-parameters-in-code)
- [Writing values](#writing-values)
- [Examples](#examples)
- [Open points](#open-points)

___

## Why one tree

The game is tuned by running it many times with one value changed and
comparing the results. That only works when every such value has a name,
one place and one way to be changed.

So there is no balance number in the code. A rule reads its numbers from
the tree, and a designer, a test or a batch of the lab changes the tree.

___

## Parameters and settings

Two kinds of configuration exist, and they never mix.

| Kind           | Decides                 | Belongs to | Kept in the run record |
|----------------|-------------------------|------------|------------------------|
| **Parameter**  | what happens in a game  | the game   | yes, all of them       |
| **Setting**    | how the server runs     | the server | no                     |

The length of a day, how much a band eats and the cost of a bad proposal
are parameters. The length of a tick on the screen, the address of the
database and the directory for run records are settings. The test is
simple: if changing it could change the outcome of a game, it is a
parameter.

Settings are read from the environment, with the prefix `DT_`, and have
working defaults for a local run.

___

## What the tree holds

The tree has a fixed set of top-level sections. Each later stage fills its
own: stage 0 defined the frame and `time`, stage 1 filled `planet` and
`biomes` and gave an era its cell and its properties.

| Section      | Holds                                               | Filled in     |
|--------------|-----------------------------------------------------|---------------|
| `time`       | parts of a day, days in a month, seasons            | stage 0       |
| `eras`       | per era: parts per tick, size of a cell, properties | stage 0, 1, 5 |
| `planet`     | size, the layers, the sea, rivers, the first window | stage 1       |
| `biomes`     | one entry per biome: its rule, properties per era   | stage 1       |
| `resources`  | weight, how fast each one spoils                    | stage 2       |
| `units`      | one entry per kind of unit: the band first          | stage 2       |
| `council`    | when it sits, the voice, what a vote does to status | stage 2       |
| `encounters` | chance and cost of what a band may run into         | stage 2       |
| `peoples`    | how many other bands, how they are spawned          | stage 3       |

Content and balance are the same thing here. A biome is an entry in the
tree, so adding a biome and changing how much food a forest gives are both
edits to data.

___

## Where the values come from

A game's tree is built in three layers, each laid over the one before.

1. **Defaults** - shipped with the game, one file per section. Every
   parameter has a default, so an empty request starts a playable game.
2. **A preset** - a named file with a set of changes, such as a harsher
   winter or another planet: one continent, islands only, a desert
   world. Optional.
3. **Overrides** - single values given when the game is created, each
   addressed by its path in the tree.

The result is the **resolved tree**: complete, with nothing left to look
up. Its hash is the short name of a parameter set, and two games with the
same hash were played by the same rules. The hash is the SHA-256 of the
tree written as canonical JSON; the examples in these documents shorten
it.

A preset or an override may reach any value, however deep, one item of a
list included: one season can be made longer without restating the other
three. The layers are laid over each other and compared with
[DeepDiff](https://zepworks.com/deepdiff/current/), which also answers the
question the lab asks most: what exactly differs between these two trees.
`diff(a, b)` of the `content` package gives that answer by dotted path.

The files are [YAML](https://yaml.org/): `content/defaults` holds one file
per section and `content/presets` one file per preset. The section
`biomes` is a directory instead, `content/defaults/biomes`, with one file
per biome named as the biome, so that a new biome is a new file; see
[Biomes](../biomes/overview.md#adding-a-biome).

___

## Checking the tree

The tree has a schema, and a game does not start from a tree that fails
it.

- **Unknown names are refused.** A typo in an override is an error, not a
  value silently ignored.
- **Types and ranges are checked**: a chance lies between 0 and 1, a count
  is not negative, a duration names a known unit.
- **The sections must agree**: an era's tick divides a day or covers whole
  days, a biome gives exactly the properties its era names and only
  resources that exist, the planet is made of whole cells and the first
  window fits it. [Biomes](../biomes/overview.md#checks) and
  [Generation](../biomes/generation.md#parameters) list the checks of
  their sections.
- **Names in a list do not repeat**: two seasons or two parts of a day
  with one name are refused.

An error names the path of the value, what was found and what was
expected. It is the message `error-params-invalid`, and the API answers it
with status 422.

___

## A tree is fixed for the game

Once a game is created its tree never changes. This is what makes a replay
possible and a comparison honest.

A change of era does not change the tree either. The tree holds the values
of every era from the start; the game only moves to reading another part
of it.

The tree carries a schema version. A new parameter always comes with a
default, so a preset written for an older version still loads; a renamed
or removed parameter raises the version, and the run record says which
version a game was played with.

___

## Reading parameters in code

The engine receives the resolved tree when a game is created and passes it
down. Nothing reads parameters from a global or from a file at run time.

```python
from dominion_theory.content import load_params
from dominion_theory.engine import Game

params = load_params(preset='harsh-winter', overrides={'planet.window.width': 256})
game = Game.create(seed=42, params=params)

params.time.days_per_month          # 10
params.eras['band'].parts_per_tick  # 1
params.planet.window.width          # 256
params.biomes['forest'].colour      # '#006400'
params.hash                         # 'b41f...'
```

The tree is typed and frozen: a wrong name is caught by the type checker,
and an attempt to change a value raises.

___

## Writing values

A few conventions keep the tree readable and the overrides predictable.

- **Names** are lower case with underscores. A path joins them with dots:
  `units.band.consumption.food`.
- **An item of a list** is reached by its `name` when it has one, and by
  its position otherwise: `time.seasons.winter.months`.
- **The unit is in the name** when it is not obvious: `cell_km`,
  `carry_kg`.
- **A duration** is a mapping with one calendar unit: `{days: 3}`,
  `{months: 1}`, `{parts: 2}`. See [Time](time.md).
- **A flow** is an amount per day and says so: `food_per_day`. A yearly
  rate says `per_year`.
- **A chance** is a number from 0 to 1.
- **A value that differs by era** sits under the name of the era.
- **A value that changes through the year** is a base with modifiers by
  season, so that weather can later add its own without a new shape. A
  modifier is `{plus: 0.1}` or `{times: 0.7}`.
- **A range** is a mapping with `min`, `max` or both, closed at both ends:
  `{min: 0.5}`.
- **An override reaches what the defaults write.** A side of a range or a
  season that a biome leaves out has no path; override the mapping above
  it instead: `biomes.forest.generation.moisture`.

___

## Examples

A piece of the defaults, as it would stand in the file for the council.

```yaml
council:
  part: evening
  voice:
    share: 0.5
    least: 2.0
  status:
    start: 50
    abstained: -2
    outvoted: -1
```

The whole section and its numbers are in
[Indirect control](../game/indirect_control.md#parameters).

A preset is the same shape with only what differs. This one moves a month
from summer to winter and leaves the other seasons alone.

```yaml
time:
  seasons:
    - {name: summer, months: 2}
    - {name: winter, months: 4}
```

A game is created over the API with a preset and overrides. Only paths of
the sections built so far are taken; `peoples.count` is refused until
stage 3 adds it.

```json
{
  "seed": 42,
  "preset": "harsh-winter",
  "overrides": {
    "time.seasons.autumn.months": 1,
    "planet.window.width": 256,
    "biomes.forest.eras.band.properties.food.base": 0.8
  }
}
```

___

## Open points

- **The schema version in a record** - the version is 1 and has never been
  raised, and the header of a run record does not carry it: it holds the
  whole tree and the version of the engine. The field is added with the
  first change that raises the version.
- **The reference** - a page listing every parameter with its default and
  meaning should be generated from the schema rather than written by
  hand. When it is built is not set.
