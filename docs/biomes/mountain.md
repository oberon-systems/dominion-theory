# Mountain

#biome #mountain

The highest land. A band can cross it, slowly and at a cost: there is
little to eat, little to drink and much to fear. The model is in
[the overview](overview.md).

___

## Where it appears

Mountains are the highest 12 percent of land, wherever it lies.

| Order | Rule                |
|-------|---------------------|
| 20    | elevation from 0.88 |

Only water comes before it in the order, so a peak is a mountain even in
the cold belts and in the desert.

___

## Band era

| Property      | Base | Recovery | Seasons      |
|---------------|------|----------|--------------|
| `water`       | 0.2  | 3 days   | none         |
| `food`        | 0.2  | 60 days  | winter 0.2   |
| `threat`      | 0.7  | none     | none         |
| `passability` | 0.3  | none     | none         |

Resources: `water`, `forage`. Colour: `#8B8989`.

The old generator put mountains on middle heights, next to the shore.
That is the defect this rule fixes.
