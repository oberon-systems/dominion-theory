# Water

#biome #water

The deep sea: every cell well below the sea level. Nobody walks here in
the band era. Water near the level of the sea, a lake and the bed of a
great river are [shallows](shallows.md), and the frozen sea is
[ice](ice.md). Rivers are not this biome; they are lines over the land,
told in [Generation](generation.md#rivers). The model is in
[the overview](overview.md).

___

## Where it appears

Water is first in the order, so nothing else can claim a cell below the
sea level. By default 60 percent of the planet is water.

| Order | Rule              |
|-------|-------------------|
| 10    | elevation below 0 |

___

## Band era

| Property      | Base | Recovery | Seasons |
|---------------|------|----------|---------|
| `water`       | 1.0  | none     | none    |
| `food`        | 0.3  | 30 days  | none    |
| `threat`      | 0.2  | none     | none    |
| `passability` | 0.0  | none     | none    |

Resources: `water`. Colour: `#0077BE`.

Passability was 0.1 in the old settings while the notes on the band said
that water cannot be entered. It is 0 now, and the two agree.
