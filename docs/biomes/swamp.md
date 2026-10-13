# Swamp

#biome #swamp

Flat, warm ground that stands in water: the delta of a river, its banks
on a plain, the shore of a lake. It never runs dry and it feeds well, but
it is the slowest land to cross that can be crossed at all, and it is not
safe. The model is in [the overview](overview.md).

___

## Where it appears

A swamp is where the most water runs through, the tenth of land with
the largest flow, when the ground there is flat and not cold. So it lies
in the mouths of rivers, along the large ones on a plain and at lakes.

| Order | Rule                                                  |
|-------|-------------------------------------------------------|
| 65    | flow from 0.9, relief up to 0.5, temperature from 0.3 |

It is ordered before forest, which would take the same land, and after
hills, so a river in high country cuts no swamp. The layer `flow` is told
in [Generation](generation.md#rivers).

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
