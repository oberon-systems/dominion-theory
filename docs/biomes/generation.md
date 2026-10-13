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
- [Continents](#continents)
- [Climate](#climate)
- [Ranges](#ranges)
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
from five of them.

| Layer         | Range   | Says                                         |
|---------------|---------|----------------------------------------------|
| `elevation`   | -1 to 1 | how high the land is; the sea is below 0     |
| `relief`      | 0 to 1  | how broken the ground is, at any height      |
| `moisture`    | 0 to 1  | how wet the land is                          |
| `temperature` | 0 to 1  | how warm it is, from the pole to the equator |
| `flow`        | 0 to 1  | how much water runs through the place        |

- **Elevation** is noise at the scale of continents with finer noise on
  top. It decides land and sea. Land is then lifted along mountain
  ranges; see [Ranges](#ranges).
- **Relief** is fine noise of its own. It is what tells a rocky outcrop
  from the grass around it at the same height.
- **Moisture** is noise at the scale of regions, with a climate laid
  over it; see [Climate](#climate).
- **Temperature** is not noise. It is 1 at the equator and 0 at the poles,
  falls with height on land, and carries a small noise so that the belts
  do not run as straight lines.
- **Flow** is not noise either. It is a ribbon along every river, told in
  [Rivers](#rivers): 0 away from them, 1 on the line of the largest.

Every noise layer has its own stream of the seed, so a change to one
never moves another. Noise is laid so that it closes around the planet
with no seam: every octave has a whole number of squares around, so the
largest shapes are close to `scale_km` and not exactly it.

```text
temperature = 1 - latitude - lapse * elevation + noise * belts + warmth
```

Latitude is 0 at the equator and 1 at a pole, elevation is the restated
one and counts on land only, `belts` is one octave of noise from -1 to 1,
and the result is held between 0 and 1. `warmth` moves the whole planet:
0 by default, above it a warmer world whose ice and snow draw back to
the poles or go, below it a colder one.

___

## Continents

How many continents a planet has is a parameter, not a chance of the
noise.

`elevation.continents.count` centres are drawn from the stream
`continents`. They stand around the planet at even steps, each moved a
little, and north or south of the equator by no more than `spread` of
the way to a pole. Around every centre the land is raised as a plateau
that falls off at `radius_km`; `edge` says how steep that fall is, and
`weight` how high the plateau stands over the noise. A continent is
stretched one way or the other, so no two are alike.

The noise still shapes the shore, and a finer noise, `islands`, is laid
over the whole planet: it raises islands out of any sea, off the coast of
a continent and in mid ocean, whatever the type of the planet.

| Planet              | How                                             |
|---------------------|-------------------------------------------------|
| two large continents | the default                                    |
| one continent       | the preset `pangea`; its heart is dry           |
| four or five        | the preset `continents`                         |
| islands only        | the preset `archipelago`: no continents, more sea |

A count of 0 leaves the land to the noise alone.

A preset can go further and make another world. `dune` is a planet of
sand: a five-hundredth of it is sea, it is warm to the poles and has no ice or
snow, and the desert takes all the land that hills and mountains leave.
A handful of rivers run on the whole planet, none of them great, and
lakes are as rare. The only green is along a river: its floodplain and
its swamp are the oases. It changes numbers
of the planet and the rule of one biome, and no code.

___

## Climate

Where it is wet and where it is dry follows the planet, not the noise
alone. Three things add up to the moisture of a place.

```text
moisture = noise + belt * (2 * wet of the latitude - 1) - inland * dried
           + heights * elevation
dried    = 1 - 0.5 ^ (distance from the sea / inland_km)
```

- **The belts of latitude.** `belts` is a list of points, each a latitude
  and how wet it is; between two points the value is read on a line. By
  default the equator is wet, the subtropics are dry, the temperate belt
  is wet again and the poles are dry. The two halves of the planet are
  alike.
- **The distance from the sea.** Land dries as it lies further inland,
  and has lost half of `inland` at `inland_km`. The heart of a large
  continent is dry. The distance is measured on the skeleton, from every
  node under the sea, and read between nodes at a cell.
- **Heights.** `heights` is how much wetter the highest land is than the
  shore; 0, the default, leaves height out. With it rain falls by the
  mountains.
- **The noise** keeps a belt from running as a straight line.

Belts run from the equator, latitude 0, to the north pole, latitude 1,
and hold for the south as well. A list that names a latitude below 0,
down to -1 at the south pole, tells north from south: one pole may then
be wet and the other dry.

The sum is restated as a share of land like the other layers, so a rule
still reads "the driest 15 percent of land": the climate decides where
that land lies, not how much of it there is.

The first window is tried in the wet temperate belt.

___

## Ranges

Noise alone puts the highest land in a blot at the middle of a continent.
Mountains run in ranges, so the land is lifted along lines.

A second noise, `ridges`, is laid over the planet. Where it turns from
one sign to the other runs a line, and that line is the crest of a range.

```text
height = (elevation - sea level) * (1 + weight * crest) * (1 - depth * dip)
crest  = (1 - |ridges|) ^ sharpness
dip    = how far the noise basins stands over its brim, 0 to 1
```

- **Only land is lifted.** The sea level is measured before the ranges
  are raised, and a height below it is left alone, so no shore moves.
- **A range fades to the coast**: the lift is a share of the height the
  land already has.
- **`weight`** is how many times higher a crest stands than the land it
  rose from; 0 gives the planet without ranges.
- **`sharpness`** is how narrow a range is: the higher, the thinner.

Hills are the belt just below the mountains by height, so they lie around
every range by themselves.

**Basins** work the other way. A third noise, `basins`, sinks the land
where it is highest: `share` of the planet lies in a basin, and `depth`
is how much of its height the middle of one loses. A basin never sinks
below the sea level. Inland it is a hollow that water cannot leave
without rising, and that is where lakes and inland seas stand.

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

Every biome carries a generation rule: a range for any of the five layers,
and its place in the order. A cell gets the first biome, by order, whose
ranges all hold.

| Order | Biome      | Rule                                  | Reads as                   |
|-------|------------|---------------------------------------|----------------------------|
| 5     | `ice`      | elevation up to 0, temperature up to 0.08 | the frozen sea at the poles |
| 8     | `shallows` | elevation from -0.15 to 0             | the shelf, lakes, river beds |
| 10    | `water`    | elevation up to 0                     | the deep sea               |
| 20    | `mountain` | elevation from 0.92                   | highest 8 percent of land  |
| 25    | `snow`     | temperature up to 0.07                | the caps of the poles      |
| 30    | `tundra`   | temperature up to 0.15                | the cold belts             |
| 40    | `outcrops` | relief from 0.95                      | most broken 5 percent      |
| 50    | `hills`    | elevation from 0.68                   | the belt below mountains   |
| 52    | `swamp`    | flow from 0.45, relief up to 0.35, temperature from 0.3 | flat land beside a river |
| 53    | `floodplain` | flow from 0.45, temperature from 0.2 | the banks of a river |
| 55    | `dunes`    | elevation up to 0.2, moisture up to 0.25, temperature from 0.5 | the dry shore |
| 60    | `desert`   | moisture up to 0.15, temperature from 0.5 | dry and warm           |
| 67    | `marsh`    | elevation up to 0.25, moisture from 0.75, temperature from 0.3 | the wet shore |
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
   neighbours. Hollows are filled first, so every drop reaches the
   ocean. A body of water with less than `rivers.ocean` of all sea nodes
   is not the ocean but an inland sea: it is filled like a hollow, and a
   river leaves it.
3. **Gathering** - a node carries its own rain and all that flows into it.
   The nodes that carry the most, 4.3 percent of land by default, are river
   nodes. Each river is then followed upstream, by the largest inflow at
   every node, to the node nothing flows into: its source on a divide.
4. **The line** - river nodes are joined downstream into lines, each to
   the sea or into a larger river. A node is moved off the centre of its
   square, a point half way to the next node is pushed aside by up to
   `meander_km`, and one smooth curve is drawn through all of them, so
   that a river shows neither the grid it was traced on nor a corner. How
   far a node is moved and in how many pieces the curve is drawn between
   two points are constants of the code, not parameters.

Of two nodes that carry the same, the lower is taken first, so a river is
never cut on its way down.

So a river rises on a divide, which the ranges make a mountain crest, and
ends in the sea or in a larger river. A sea node is left at the centre of
its square, where there is water at any cell size, so a mouth never ends
on land.

**Lakes** stand in the hollows that were filled, the basins first of
all. Hollows that touch are one basin, as deep as the water had to rise
to spill out of it; the deepest basins, `rivers.lakes` as a share, hold a
lake. Its water stands `rivers.lake_full` of the way from the bottom of
the basin to its brim, so a lake lies in the lowest part of its basin and
does not drown the whole of it. A cell is lake when one of the four nodes around it holds
one and the cell lies below the water. Towards a node that stands lower
than the lake, its outlet or the sea, the level is lowered to the sea
level, so the water does not run on down the valley; elsewhere the shore
is where the land rises out of the water. It is then the biome `water`. A river runs into a lake and out of
it, and a large lake is an inland sea.

**A great river has a bed.** The nodes that carry the most of all,
`rivers.great` as a share of land, make a river `width_km` wide: the
cells within half of that from its line are the biome `water`, so it
cannot be walked across. A share of the bed, `islands`, where the ground
is most broken, stays land: islands in the stream. Every other river is a
mark on a cell that can be crossed.

**A delta.** Where a great river meets the ocean it breaks into arms:
`rivers.arms` of them fan out from the node above its last on land, as
wide at the mouth as `delta_km`, each bearing further away as it goes and forking
once. An arm ends at the first place under the sea, and one that finds no
sea is not drawn. Arms are lines like any river.

**The layer `flow`** is the size of the largest river near a place: 0
for the least of all river nodes, 1 for the one that carries the most,
falling to nothing at `valley_km` from the line. So it is a ribbon along
a river that widens as rivers join, and it covers a delta. It is what
puts [swamp](swamp.md) and [floodplain](floodplain.md) beside rivers.

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
| land            | 0.5     | at least this share of cells is land |
| `forest`        | 0.15    | share of cells                       |
| `hills`         | 0.05    | share of cells                       |
| `outcrops`      | 0.01    | share of cells                       |
| rivers          | 1       | this many lines cross the window     |

- **A place is judged on a coarse sample** of its cells, at most 32 by
  32 of them spread evenly, so that many places can be tried quickly.
- **The river need counts lines** that touch the rectangle of the window,
  not marked cells.
- **The latitude of a place** is that of the centre row of the window.
- **The tries are limited**, 128 by default. When none meets every need,
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
| `continents`  | where the continents stand           |
| `islands`     | the finer noise that raises islands  |
| `ridges`      | the noise the ranges follow          |
| `basins`      | the noise the basins follow          |
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
  elevation:
    scale_km: 3000
    octaves: 5
    persistence: 0.5
    continents: {count: 2, weight: 0.9, radius_km: 6000, spread: 0.4, edge: 4}
    islands: {scale_km: 700, octaves: 3, persistence: 0.5, weight: 0.2}
    ridges: {scale_km: 2000, octaves: 2, persistence: 0.5, weight: 3.0, sharpness: 12}
    basins: {scale_km: 800, octaves: 2, persistence: 0.5, share: 0.06, depth: 0.7}
  relief: {scale_km: 150, octaves: 3, persistence: 0.5}
  moisture:
    scale_km: 1500
    octaves: 4
    persistence: 0.5
    belt: 0.8
    inland: 0.6
    inland_km: 800
    heights: 0.0
    belts:
      - {latitude: 0.0, wet: 1.0}
      - {latitude: 0.12, wet: 0.85}
      - {latitude: 0.27, wet: 0.1}
      - {latitude: 0.38, wet: 0.45}
      - {latitude: 0.5, wet: 0.8}
      - {latitude: 0.65, wet: 0.6}
      - {latitude: 0.85, wet: 0.3}
      - {latitude: 1.0, wet: 0.2}
  temperature: {lapse: 0.25, noise: 0.05, scale_km: 1000, warmth: 0.0}
  rivers:
    share: 0.043
    great: 0.02
    lakes: 0.5
    lake_full: 0.35
    ocean: 0.02
    meander_km: 30
    width_km: 40
    valley_km: 100
    delta_km: 400
    arms: 4
    islands: 0.3
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
    latitude: {min: 0.38, max: 0.6}
    tries: 128
    needs:
      land: 0.5
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
| mountains sat on middle heights                | mountains are the highest land, in ranges  |
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
- **A river does not dry up.** Every river reaches the ocean, in a desert
  as well.
- **The size of a lake** - a hollow of one node that is shallow gives a
  pond too small to see. Lakes that show stand in the basins.
- **Green by a lake** - the layer `flow` follows rivers. A lake no river
  runs through has bare shores, which shows on a desert planet.
- **A delta is small** - an arm ends at the first water it meets, and a
  cell of 10 km cannot show a web of channels.
- **The first window is found late** on the default planet: its two
  continents lie by the equator, and many tries fall into the ocean.
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
