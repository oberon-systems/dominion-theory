# Ice

#biome #ice

The sea frozen over at the poles. Unlike open water it can be walked, slowly
and with nothing to live on but the ice itself. The model is in
[the overview](overview.md).

___

## Where it appears

Ice is water where it is coldest: the caps of the sea at both poles, and
a lake that lies as far north or south.

| Order | Rule                                         |
|-------|----------------------------------------------|
| 5     | elevation up to 0, temperature up to 0.08    |

It is the first biome of all in the order, so it is judged before open
water. It does not melt: a biome never changes. Water that freezes by
season is a matter of later stages; see [the roadmap](../roadmap.md).

___

## Band era

| Property      | Base | Recovery | Seasons |
|---------------|------|----------|---------|
| `water`       | 0.3  | 3 days   | none    |
| `food`        | 0.05 | 90 days  | none    |
| `threat`      | 0.5  | none     | none    |
| `passability` | 0.5  | none     | none    |

Resources: `water`. Colour: `#CFE8F5`.
