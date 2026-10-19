# Shallows

#biome #shallows

Water that is not deep: the shelf along a coast, a lake, the bed of a
great river. Nobody walks here, like any water, but there is more to
gather by it than by the open sea. The model is in
[the overview](overview.md).

___

## Where it appears

Shallows are the water nearest to the level of the sea: the shallowest
15 percent of it by depth. A lake and the bed of a great river stand at
that level, so they are shallows as a whole.

| Order | Rule                       |
|-------|----------------------------|
| 8     | elevation from -0.15 to 0  |

They come after ice, so a frozen shore is ice, and before the open
water, which is everything deeper.

___

## Band era

| Property      | Base | Recovery | Seasons |
|---------------|------|----------|---------|
| `water`       | 1.0  | none     | none    |
| `food`        | 0.5  | 20 days  | none    |
| `threat`      | 0.6  | none     | none    |
| `passability` | 0.0  | none     | none    |
| `stone`       | 0.0  | none     | none    |
| `wood`        | 0.0  | none     | none    |
| `plants`      | 0.0  | none     | none    |
| `game`        | 0.0  | none     | none    |

Resources: `water`, `forage`. Colour: `#3D9BD6`.

Shallows are a `shore`: a band never enters them in this era, but it
gathers their water and forage from any land cell beside them; see
[The shore](../game/01_bands.md#the-shore).

The map tool paints water darker the deeper it lies, so the shelf shows
around every coast.
