# Generation

#map #biomes #planet #stage1

How the land is made: the planet, its layers, the rivers, the rule that
gives every cell a biome and the rule that places the first window. Part of
the stage 1 design in [the roadmap](../roadmap.md); the biomes themselves
are described in [the overview](overview.md).

- [One planet](#one-planet)
- [The size of the planet](#the-size-of-the-planet)
- [Skeleton and detail](#skeleton-and-detail)
- [Layers](#layers)
- [Shares instead of thresholds](#shares-instead-of-thresholds)
- [From layers to a biome](#from-layers-to-a-biome)
- [Rivers](#rivers)
- [The first window](#the-first-window)
- [Determinism](#determinism)
- [Parameters](#parameters)
- [What is fixed in the old generator](#what-is-fixed-in-the-old-generator)
- [Open points](#open-points)

___

## One planet

A game has one planet, and it is made once, from the seed. The map a
player sees is a window on it.

The planet is a function: give it the seed, a place and the size of a
cell, and it answers what lies there. Nothing is stored for land that
nobody looks at, and the same place answers the same at any time and
through any window. This is what lets a later era zoom out and find the
same continents under a larger cell.

___

## The size of the planet

The planet is measured in kilometres and cut into cells by the era.

| Value                     | Default   | Cells of the band era |
|---------------------------|-----------|-----------------------|
| around the equator        | 40000 km  | 4000                  |
| from pole to pole         | 20000 km  | 2000                  |
| a cell of the band era    | 10 km     | 1                     |
| the first window          | 5120 by 2560 km | 512 by 256      |

The distance from pole to pole is always half of the distance around.
4000 cells divide by five three times over, so the planet can be zoomed
out by five to a side three times and still be made of whole cells.

The map is a cylinder, not a sphere: every row is as long as the equator.
It wraps from east to west, and it ends at the poles in the north and in
the south.

___

## Skeleton and detail

The planet is made in two passes, the way a painter blocks in shapes
before the detail.

- **The skeleton** is a coarse grid over the whole planet, one node every
  100 km, worked out once when a game is created. It answers what needs
  the whole planet to be known: where the sea level lies, how values are
  spread, where the rivers run.
- **Detail** is worked out for the window only, cell by cell, from the
  same functions the skeleton sampled.

The skeleton is not part of the state of a game. It follows from the seed
and the parameters and is kept in the process, for the last few planets
asked for. A game keeps the biomes and the rivers of its window in its
snapshot, so restoring it builds no skeleton.

___

## Layers

A layer is one number for every place on the planet. Biomes are chosen
from four of them.

| Layer         | Range   | Says                                         |
|---------------|---------|----------------------------------------------|
| `elevation`   | -1 to 1 | how high the land is; the sea is below 0     |
| `relief`      | 0 to 1  | how broken the ground is, at any height      |
| `moisture`    | 0 to 1  | how wet the land is                          |
| `temperature` | 0 to 1  | how warm it is, from the pole to the equator |

- **Elevation** is noise at the scale of continents with finer noise on
  top. It decides land and sea.
- **Relief** is fine noise of its own. It is what tells a rocky outcrop
  from the grass around it at the same height.
- **Moisture** is noise at the scale of regions.
- **Temperature** is not noise. It is 1 at the equator and 0 at the poles,
  falls with height on land, and carries a small noise so that the belts
  do not run as straight lines.

Every noise layer has its own stream of the seed, so a change to one
never moves another. Noise is laid so that it closes around the planet
with no seam: every octave has a whole number of squares around, so the
largest shapes are close to `scale_km` and not exactly it.

```text
temperature = 1 - latitude - lapse * elevation + noise * belts
```

Latitude is 0 at the equator and 1 at a pole, elevation is the restated
one and counts on land only, `belts` is one octave of noise from -1 to 1,
and the result is held between 0 and 1.

___

## Shares instead of thresholds

A threshold on raw noise means nothing to a designer and breaks when the
noise changes. So three of the layers are restated as shares of the
planet before any rule reads them.

- **Sea level** is not a number of the noise. The parameter is the share
  of the planet under water, 0.6 by default, and the level follows from
  it.
- **Elevation on land** is the share of land that lies lower: 0 at the
  shore, 0.9 where only a tenth of all land is higher. Below the sea it
  runs the same way from 0 down to -1.
- **Relief and moisture** are the share of land with a lower value.

So `elevation: {min: 0.92}` reads as "the highest 8 percent of land",
whatever the noise under it. The shares are measured on the skeleton, and
a cell between nodes is read off the same tables. The sea level lies
between two nodes, so no node sits on it. Temperature is left as it is: it
already has a meaning.

___

## From layers to a biome

Every biome carries a generation rule: a range for any of the four layers,
and its place in the order. A cell gets the first biome, by order, whose
ranges all hold.

| Order | Biome      | Rule                                  | Reads as                   |
|-------|------------|---------------------------------------|----------------------------|
| 10    | `water`    | elevation up to 0                     | sea and lakes              |
| 20    | `mountain` | elevation from 0.92                   | highest 8 percent of land  |
| 30    | `tundra`   | temperature up to 0.15                | the cold belts             |
| 40    | `outcrops` | relief from 0.95                      | most broken 5 percent      |
| 50    | `hills`    | elevation from 0.68                   | the belt below mountains   |
| 60    | `desert`   | moisture up to 0.15, temperature from 0.5 | dry and warm           |
| 65    | `swamp`    | elevation up to 0.15, moisture from 0.85, temperature from 0.3 | low, wet and not cold |
| 70    | `forest`   | moisture from 0.5                     | the wetter half            |
| 90    | `grass`    | none                                  | everything else            |

- **A range is closed at both ends**, and a side left out is open.
- **All ranges of a rule must hold.** The old generator took a cell when
  any of them held.
- **One biome has no ranges** and so takes whatever the others left. A
  set of biomes without such a one is refused.
- **Orders do not repeat.** They are spaced by ten so that a new biome
  fits between two old ones without renumbering.

The numbers are the starting point. They are tuned on drawn maps during
the implementation and this table is then corrected.

___

## Rivers

A river is a line on the planet, not a biome and not a chain of cells.

Rivers are traced on the skeleton, in four steps.

1. **Rain** - every land node takes water in proportion to its moisture.
2. **Flow** - water runs from a node to the lowest of its eight
   neighbours. Hollows are filled first, so every drop reaches the sea.
3. **Gathering** - a node carries its own rain and all that flows into it.
   The nodes that carry the most, 5 percent of land by default, are river
   nodes.
4. **The line** - river nodes are joined downstream into lines, each to
   the sea or into a larger river. A node is moved off the centre of its
   square, and the line between two nodes bends by up to `meander_km`, so
   that a river does not show the grid it was traced on. How far a node
   is moved and in how many pieces a bend is drawn are constants of the
   code, not parameters.

Of two nodes that carry the same, the lower is taken first, so a river is
never cut on its way down.

A cell of any size has a river when a line crosses it. That is a mark on
the cell beside its biome: forest with a river is still forest. What the
mark does to the properties of the cell is told in
[the overview](overview.md#rivers). A cell of the biome `water` carries no
mark.

Because a river is a line, a larger cell of a later era finds the same
river in the same place.

___

## The first window

The band era is played in a window: a rectangle of the planet, 512 by 256
cells by default. It is placed where a band can live.

Places are tried in a fixed order of draws from the stream `window`, each
with its centre in the temperate north, and the first that meets every
need is taken.

| Need            | Default | Means                                |
|-----------------|---------|--------------------------------------|
| land            | 0.6     | at least this share of cells is land |
| `forest`        | 0.15    | share of cells                       |
| `hills`         | 0.05    | share of cells                       |
| `outcrops`      | 0.01    | share of cells                       |
| rivers          | 1       | this many lines cross the window     |

- **A place is judged on a coarse sample** of its cells, at most 32 by
  32 of them spread evenly, so that many places can be tried quickly.
- **The river need counts lines** that touch the rectangle of the window,
  not marked cells.
- **The latitude of a place** is that of the centre row of the window.
- **The tries are limited**, 64 by default. When none meets every need,
  the place that misses the fewest is taken, the earlier of two equals.
- **The north is not a taste.** The calendar has one set of seasons, and
  they are true for one hemisphere only.
- **A window can be put by hand**: `planet.window.x` and `planet.window.y`
  name its north-west cell, and nothing is tried. Tests and comparisons in
  the lab use this.

The window does not cross the seam where east meets west.

___

## Determinism

The same seed and the same parameters give the same planet, the same
rivers and the same window.

| Stream        | Draws                                |
|---------------|--------------------------------------|
| `elevation`   | the noise of the elevation layer     |
| `relief`      | the noise of the relief layer        |
| `moisture`    | the noise of the moisture layer      |
| `temperature` | the noise laid over the belts        |
| `rivers`      | where a node sits and how a line bends |
| `window`      | the places that are tried            |

Nothing in generation reads a clock, a global or a default seed. Cells
are worked through by coordinate, and where two neighbours of a node are
equally low the first in a fixed order of directions wins.

___

## Parameters

Generation is the section `planet` of
[the tree](../architecture/parameters.md), and the size of a cell belongs
to the era.

```yaml
planet:
  circumference_km: 40000
  skeleton_km: 100
  sea: 0.6
  elevation: {scale_km: 6000, octaves: 6, persistence: 0.5}
  relief: {scale_km: 150, octaves: 3, persistence: 0.5}
  moisture: {scale_km: 1500, octaves: 4, persistence: 0.5}
  temperature: {lapse: 0.25, noise: 0.05, scale_km: 1000}
  rivers:
    share: 0.05
    meander_km: 30
    effects:
      band:
        water: {plus: 0.5}
        food: {plus: 0.1}
        passability: {times: 0.7}
  window:
    width: 512
    height: 256
    x: null
    y: null
    latitude: {min: 0.3, max: 0.6}
    tries: 64
    needs:
      land: 0.6
      rivers: 1
      biomes: {forest: 0.15, hills: 0.05, outcrops: 0.01}
```

```yaml
eras:
  band:
    parts_per_tick: 1
    cell_km: 10
    properties: [water, food, threat, passability]
```

- **`scale_km`** is the size of the largest shapes of a layer.
- **`lapse`** is how much temperature falls from the shore to the highest
  peak.
- **`latitude`** runs from 0 at the equator to 1 at the north pole.

A tree is refused when the planet is not made of whole cells and whole
skeleton squares, when the window does not fit the planet, when only one
of `window.x` and `window.y` is given, or when a need names a biome that
does not exist.

___

## What is fixed in the old generator

| Defect                                         | Now                                        |
|------------------------------------------------|--------------------------------------------|
| mountains sat on middle heights                | mountains are the highest land             |
| a biome matched when any of its ranges held    | all ranges must hold                       |
| rivers ran down the screen, top to bottom      | rivers run downhill to the sea             |
| a river turned its cells into water            | a river is a mark beside the biome         |
| thresholds were written for another noise      | thresholds are shares of the planet        |
| the map was a rectangle with nothing around it | the map is a window on a planet            |
| the second layer was seeded with `seed + 1`    | every layer has its own stream             |

___

## Open points

- **A river is not cut into the land.** Detail is not lowered along the
  line, so a river may cross a cell of hills. Cutting a valley is added
  if drawn maps look wrong without it.
- **Lakes** - water gathers only where the land dips below the sea level.
  A hollow that is filled to route the rivers does not become a lake yet.
- **The seam** - the first window keeps clear of it. A window that grows
  in stage 5 may have to cross it.
- **The south** - a window in the southern half needs the seasons turned
  around. Nothing places a window there yet.
- **The size of the window** - 512 by 256 cells is 5120 km across, a lot
  of land for one band and five to ten others. It is set again in stage 3,
  when it is known how often bands should meet.
- **A cell of a later era** - whether a larger cell reads the planet at
  its centre or is built from the 25 cells under it where those were
  played. Stage 5 sets it; the planet answers both.
