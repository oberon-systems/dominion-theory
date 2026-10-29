# Floodplain

#biome #floodplain

The meadows beside a river: ground the water covers in spring and feeds
all year. It is the richest open land there is and easy to walk, except
in the flood. The model is in [the overview](overview.md).

___

## Where it appears

A floodplain lies along a river, the wider the larger the river is: the
layer `flow` is high there. Small streams have none.

| Order | Rule                                  |
|-------|---------------------------------------|
| 53    | flow from 0.45, temperature from 0.2  |

It comes right after [swamp](swamp.md), which takes the flat part of the
same ribbon, and before dunes and desert, so a river through a desert
runs between green banks. In hills and mountains a river has no
floodplain: they come earlier in the order.

___

## Band era

| Property      | Base | Recovery | Seasons                            |
|---------------|------|----------|------------------------------------|
| `water`       | 0.8  | 3 days   | none                               |
| `food`        | 0.9  | 20 days  | spring 0.6, autumn 1.2, winter 0.3 |
| `threat`      | 0.2  | none     | none                               |
| `passability` | 0.9  | none     | spring 0.5                         |
| `stone`       | 0.05 | 60 days  | none                               |
| `wood`        | 0.05 | 60 days  | none                               |
| `plants`      | 0.7  | 30 days  | none                               |
| `game`        | 0.5  | 60 days  | none                               |

Resources: `water`, `forage`, `stones`, `sticks`, `herbs`, `cords`. Colour: `#9ACD32`.

It is the first biome where a season changes how the land is crossed: in
spring the river is out of its banks.
