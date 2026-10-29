# Hills

#biome #hills

High, rolling land below the mountains. It gives less than the lowland and
slows a band down, but it is no wall. The model is in
[the overview](overview.md).

___

## Where it appears

Hills are about a quarter of all land, the part just below the mountains: a belt
around every range, and the tops of lower country.

| Order | Rule                |
|-------|---------------------|
| 50    | elevation from 0.68 |

Mountains come earlier in the order and take the land above 0.92, so the
rule needs no upper end.

___

## Band era

| Property      | Base | Recovery | Seasons                            |
|---------------|------|----------|------------------------------------|
| `water`       | 0.5  | 3 days   | none                               |
| `food`        | 0.5  | 30 days  | spring 0.7, autumn 1.1, winter 0.3 |
| `threat`      | 0.3  | none     | none                               |
| `passability` | 0.7  | none     | none                               |
| `stone`       | 0.5  | 90 days  | none                               |
| `wood`        | 0.05 | 60 days  | none                               |
| `plants`      | 0.0  | none     | none                               |
| `game`        | 0.3  | 60 days  | none                               |

Resources: `water`, `forage`, `stones`, `sticks`. Colour: `#8F9A5B`.

The first window must hold some hills: see
[Generation](generation.md#the-first-window).
