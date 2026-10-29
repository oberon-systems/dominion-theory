# Outcrops

#biome #outcrops

Rocky outcrops: bare, broken ground in small patches, at any height. They
give a band next to nothing in the band era and are named now because
stone matters later. The model is in [the overview](overview.md).

___

## Where it appears

Outcrops follow relief, not height: the most broken 5 percent of land.
Relief is fine noise, so they come as scattered patches and not as a belt.

| Order | Rule             |
|-------|------------------|
| 40    | relief from 0.95 |

___

## Band era

| Property      | Base | Recovery | Seasons    |
|---------------|------|----------|------------|
| `water`       | 0.2  | 3 days   | none       |
| `food`        | 0.2  | 60 days  | winter 0.3 |
| `threat`      | 0.3  | none     | none       |
| `passability` | 0.5  | none     | none       |
| `stone`       | 0.8  | 90 days  | none       |
| `wood`        | 0.05 | 60 days  | none       |
| `plants`      | 0.0  | none     | none       |
| `game`        | 0.0  | none     | none       |

Resources: `water`, `forage`, `stones`, `sticks`. Colour: `#6E6259`.

Stone is not a resource yet. It is added to this biome by the era that
first uses it. The first window must hold a few outcrops: see
[Generation](generation.md#the-first-window).
