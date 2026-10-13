# Swamp

#biome #swamp

Low, wet, warm ground that stands in water. It never runs dry and it
feeds well, but it is the slowest land to cross that can be crossed at
all, and it is not safe. The model is in [the overview](overview.md).

___

## Where it appears

A swamp is the wettest 15 percent of land where that land is also low,
within the lowest 15 percent above the shore, and not cold. So it lies
on wet coasts and in the mouths of rivers, in small patches.

| Order | Rule                                                           |
|-------|----------------------------------------------------------------|
| 65    | elevation up to 0.15, moisture from 0.85, temperature from 0.3 |

It is ordered before forest, which would take the same land. Wet low land
in the cold stays forest or becomes tundra.

___

## Band era

| Property      | Base | Recovery | Seasons                            |
|---------------|------|----------|------------------------------------|
| `water`       | 0.9  | 3 days   | none                               |
| `food`        | 0.7  | 30 days  | spring 0.7, autumn 1.1, winter 0.3 |
| `threat`      | 0.6  | none     | none                               |
| `passability` | 0.3  | none     | none                               |

Resources: `water`, `forage`. Colour: `#4A6B5D`.

Swamp is the biome that closed stage 1: it was added by its data file,
its name in two catalogues, this document and one test, with no line of
the engine, the generator or the API changed.
