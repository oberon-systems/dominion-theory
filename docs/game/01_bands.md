# Game Process

#game #band

Here I will try to describe game process from start and to the end (what end?).

___

## Start

At start we spawn a few [Bands](../units/band.md) in a random locations, one of bands in-direct controlling by a **Player**, other just a bots.

[Band](../units/band.md) spawns at grassland biome, at start it has next settings:

- `population`: 15
- speed: 1 location per `tick`
- `state`: normal
- `resources`:
  - water: 15
  - `food`: 30

___

## Turns

For each turn [Bands](../units/band.md) could make 5 action (500 ms), [Bands](../units/band.md) make decision in-directly, but after 5 actions, at end of the turn **Player** could ask Band to set a camp.

Often [Band](../units/band.md) move or gather resources, it set camps only for rest (once at turn as 4th and 5th `action`)

### Move Decision

[Band](../units/band.md) could move as `action` in some available nearest location with next limitations:

- location should being next to current location (N, NE, E, SE, S, SW, W, NW)
- location should be not occupied with another Band
- location should not be a water biome

More over, [Band](../units/band.md) being in normal state for make a move `action`

### Camp Decision

[Band](../units/band.md) could decide to set a camp if one of next conditions met:

- [Band](../units/band.md) have to rest
- There is enough food and water
- current location thread level is low

However, [Band](../units/band.md) could set camp at **Players** will.

### Gathering Resources

Also [Band](../units/band.md) could gather one of known resource, e.g. water or food

___

## Player Will

For [Bands](../units/band.md)  **Player** represents as a **Headman**, or *band leader*. He is a most strong person in a tribe.

**Headman** collect will points for each turn and he could spend this points for force Band decision (any).

But after each forced decision **Headman** collect less points for some period, when tribe is not in `normal` state **Headman** loss hist collected points each turn.

If **Headman** lost all will points he will be banished from [Band](../units/band.md) and *Game will be Over*.

___

## Progression

When [Band](../units/band.md)  growing up to 150+ population it transforms to Tribe (TBD).
