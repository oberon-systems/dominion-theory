# Band

#unit #band #stage2

A band is the first unit of the game: some tens of foraging nomads who
walk, gather, rest and nothing else. This document says what a band is
made of and gives every number it reads. Part of the stage 2 design in
[the roadmap](../roadmap.md); how a band lives through a day is told in
[Bands](../game/01_bands.md).

- [What a band holds](#what-a-band-holds)
- [Population](#population)
- [Stores](#stores)
- [Gathering](#gathering)
- [Consumption](#consumption)
- [Speed](#speed)
- [Fatigue](#fatigue)
- [States](#states)
- [What a band knows](#what-a-band-knows)
- [Parameters](#parameters)
- [Checks](#checks)
- [Open points](#open-points)

___

## What a band holds

A band is an entry of the state of a game, and its kind is an entry of
the section `units` in [the tree](../architecture/parameters.md). There
is no number of a band in the code.

| Field        | Holds                                                   |
|--------------|---------------------------------------------------------|
| `id`         | the number of the unit, 1 for the player's band         |
| `place`      | planet coordinates of its cell, with the scale          |
| `population` | how many people, a whole number                         |
| `stores`     | what it carries, per resource, in lots by day gathered  |
| `fatigue`    | how tired it is, from 0 to 1                            |
| `states`     | which of the bad states hold now; none means `normal`   |
| `action`     | what it did in the last tick                            |
| `intent`     | what the council bound it to, if anything               |
| `known`      | the cells it has seen and when                          |

Stage 2 puts one band on the map, the player's. Other bands are stage 3.

___

## Population

A band starts with 15 people and counts whole people. It dies when fewer
than 5 are left, and the game ends with it. The threshold of 150, at
which a band becomes a tribe, belongs to stage 5.

People are born at a yearly rate, counted every day: the band keeps the
fraction and a person appears when it reaches one. Nobody is born while
the band starves or thirsts. A band that camped the whole day grows three
times as fast, which is what makes a long rest worth proposing.

People die of hunger, of thirst and in chance encounters. See
[States](#states) and [Bands](../game/01_bands.md#chance-encounters).

___

## Stores

A band carries food and water, and each resource is an entry of the
section `resources`: a weight per unit and a time after which it spoils.

| Resource | Unit    | Weight | Spoils after |
|----------|---------|--------|--------------|
| `water`  | a litre | 1 kg   | 5 days       |
| `forage` | a kilo  | 1 kg   | 3 days       |

Stores are kept in lots, one per resource and day gathered. The oldest
lot is eaten first, and a lot older than its time is thrown away in the
phase `world` of the first tick of a day. A band holds at most five lots
of water and three of forage, so the state stays small.

A person carries 6 kg. A band never gathers more than it can carry: what
does not fit is left on the cell and the stock is not lowered for it.

___

## Gathering

A gathering tick is spent on one resource. What the band takes is its own
rate times the property of the cell, as
[Biomes](../biomes/overview.md#properties) defines it.

```text
taken = population * rate * value(property, cell)
```

| Resource | Property | Rate per person per tick |
|----------|----------|--------------------------|
| `forage` | `food`   | 3.0                      |
| `water`  | `water`  | 4.0                      |

The cell pays for it. A cell at full stock holds a fixed amount per
property, and the stock falls by what was taken over that amount. The
value already carries the stock, so a cell gives less with every tick and
the band is pushed on.

| Property | A full cell holds |
|----------|-------------------|
| `food`   | 200 units         |
| `water`  | 2000 units        |

A band gathers on the cell it stands on and nowhere else. It gathers only
the resources the biome lists.

___

## Consumption

People eat and drink once a day, in the phase `world` of the last tick of
the day.

| Resource | Per person per day |
|----------|--------------------|
| `forage` | 1.0                |
| `water`  | 1.0                |

So 15 people need 15 kg of food and 15 litres of water a day, 30 kg of
the 90 kg they can carry: a band holds three days of supplies at most,
and its food spoils on the third. One gathering tick in a summer forest
brings 40 kg of food, in a winter forest 16, and in the desert no day is
long enough. The cell is what gives out: a forest cell holds 200 kg, a
fortnight for 15 people, and needs a month to grow back.

What is missing is counted per resource as a share of the day's need.
That share drives hunger and thirst below.

___

## Speed

A band moves one cell per tick over open ground. Each moving tick adds
progress, and the band enters the next cell when the progress reaches 1.

```text
progress = speed * value(passability, target cell)
speed = max(slowest, base - slowdown * population / 10)
```

With a base of 1.2 and a slowdown of 0.03 a band of 15 walks at 1.155
and a band of 150 at 0.75; no band is slower than 0.3. A step along a
diagonal costs the same as a straight one. Progress above 1 is not
carried over, and all of it is lost when the band does anything but move
towards the same cell.

___

## Fatigue

Fatigue runs from 0 to 1. Moving and gathering add to it, camping takes
it away.

| Action   | Fatigue per tick |
|----------|------------------|
| `move`   | plus 0.15        |
| `gather` | plus 0.08        |
| `camp`   | minus 0.35       |

Two camps take away more than three moves add, so a band that sleeps
at night can walk for ever. A band that walks through the night
reaches the limit on the second day.

___

## States

A band is `normal` when none of the three bad states holds. They are
independent and may hold together.

| State        | Begins when                         | Does                            | Ends when                  |
|--------------|-------------------------------------|---------------------------------|----------------------------|
| `starvation` | food was short for 2 days running   | 5% of the people die every day  | a day's food is eaten in full |
| `thirst`     | water was short for 1 day           | 15% of the people die every day | a day's water is drunk in full |
| `tiredness`  | fatigue reaches 0.8                 | speed and gathering are halved  | fatigue falls to 0.3       |

A day counts as short when less than 0.75 of the need was met. Deaths
are whole people: the share is taken of the population and rounded up,
so a state that holds always costs somebody.

The beginning and the end of a state are events, and so is every death,
with its cause.

___

## What a band knows

A band sees the cells within 2 cells of its own, 25 in all. For each it
knows the biome, the river mark and the current value of every property.

It remembers what it saw for 20 days, as it was when last seen: a cell
that was stripped bare stays bare in its memory until it is seen again.
Older memories are dropped. The decision function reads nothing but what
is known, and so does the observation of the seat.

___

## Parameters

The defaults of the three sections this document fills. Durations and
flows are written as [Parameters](../architecture/parameters.md#writing-values)
asks.

```yaml
resources:
  water: {property: water, weight_kg: 1.0, spoils: {days: 5}}
  forage: {property: food, weight_kg: 1.0, spoils: {days: 3}}
```

```yaml
units:
  band:
    start:
      population: 15
      stores: {water: 15, forage: 15}
      biomes: [grass, forest, floodplain]
    population:
      least: 5
      growth_per_year: 0.3
      rest_growth: 3.0
    carry_kg: 6.0
    gathering:
      forage: 3.0
      water: 4.0
    consumption_per_day:
      forage: 1.0
      water: 1.0
    speed:
      base: 1.2
      slowdown: 0.03
      slowest: 0.3
    fatigue:
      move: 0.15
      gather: 0.08
      camp: -0.35
    states:
      short: 0.75
      starvation: {after: {days: 2}, loss_per_day: 0.05}
      thirst: {after: {days: 1}, loss_per_day: 0.15}
      tiredness: {begins: 0.8, ends: 0.3, slows: 0.5}
    sight: 2
    memory: {days: 20}
```

```yaml
eras:
  band:
    capacity: {food: 200, water: 2000}
    recovery: {food: {winter: 0.25}}
```

`eras.band.recovery` slows the recovery of a stock in a season: food
grows back at a quarter of its pace in winter. Every number here is a
first guess; the lab of the roadmap is where they are tuned.

___

## Checks

A game does not start from a band that does not add up.

- A resource names a property of every era that uses it, a positive
  weight and a time to spoil that is not zero.
- A biome lists only resources of the section `resources`.
- The start population is not below `population.least`.
- The start stores fit what the start population carries.
- A start biome exists and can be entered.
- `tiredness.ends` is below `tiredness.begins`, and both lie in 0 to 1.
- A share, a chance and a loss lie between 0 and 1.

___

## Open points

- **Gathering both at once** - a tick is spent on one resource. Whether a
  band splits its people between food and water is seen in the lab.
- **Who dies** - a band counts heads. Age and sex are not kept, so growth
  does not depend on who was lost.
- **Carrying against speed** - a loaded band walks as fast as an empty
  one.
- **Drinking on the spot** - a band on a river still drinks from its
  stores. Water from the cell at the moment of drinking would make a
  river worth camping on.
