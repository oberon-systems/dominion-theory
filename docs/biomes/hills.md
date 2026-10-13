# Hills

#biome #hills

High, rolling land below the mountains. It gives less than the lowland and
slows a band down, but it is no wall. The model is in
[the overview](overview.md).

___

## Where it appears

Hills are a fifth of all land, the part just below the mountains: a belt
around every range, and the tops of lower country.

| Order | Rule                |
|-------|---------------------|
| 50    | elevation from 0.68 |

Mountains come earlier in the order and take the land above 0.88, so the
rule needs no upper end.

___

## Band era

| Property      | Base | Recovery | Seasons                                 |
|---------------|------|----------|-----------------------------------------|
| `water`       | 0.5  | 3 days   | none                                    |
| `food`        | 0.5  | 30 days  | spring 0.7, autumn 1.1, winter 0.3      |
| `threat`      | 0.3  | none     | none                                    |
| `passability` | 0.7  | none     | none                                    |

Resources: `water`, `forage`. Colour: `#8F9A5B`.

The first window must hold some hills: see
[Generation](generation.md#the-first-window).
