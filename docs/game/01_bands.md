# Bands

#game #band #stage2

The band era from the first tick to the last: where a band starts, what
it does in a day, how it moves, what the land and the seasons do to it
and how the game ends. Part of the stage 2 design in
[the roadmap](../roadmap.md). The numbers of the band are in
[Band](../units/band.md).

- [The start](#the-start)
- [A day](#a-day)
- [The three actions](#the-three-actions)
- [Movement](#movement)
- [The shore](#the-shore)
- [Chance encounters](#chance-encounters)
- [Seasons](#seasons)
- [One tick of a band](#one-tick-of-a-band)
- [How a game ends](#how-a-game-ends)
- [What the API shows](#what-the-api-shows)
- [Open points](#open-points)

___

## The start

A game starts with one band, the player's, on the first window of the
planet. It stands on the cell nearest to the centre of the window whose
biome is one of `units.band.start.biomes`: grass, forest or floodplain.
Of two cells equally near, the one with the smaller y and then the
smaller x is taken.

The band has 15 people, a day of food and a day of water, no fatigue and
no state. The player's status is 50 of 100; see
[Indirect control](indirect_control.md#status).

___

## A day

A day is five ticks: morning, midday, afternoon, evening and night. The
band does one action in every tick, so the "turn of five actions" of the
old notes is a day.

Nothing fixes which action falls on which part. A band that is left to
itself comes to walk or gather by day and camp in the evening and at
night, because [the decision function](decisions.md) gives the night a
pull towards the camp.

Things that are counted by the day happen at its edges. The first tick
of a day throws away spoiled stores. The last tick feeds the people,
counts hunger and thirst, and adds the day's births.

___

## The three actions

| Action   | Does                                              | Fatigue   |
|----------|---------------------------------------------------|-----------|
| `move`   | walks towards one of the eight cells around       | grows     |
| `gather` | takes one resource from the cell it stands on     | grows     |
| `camp`   | rests where it stands                             | falls     |

A band that camped for all five ticks of a day rested that day, and
grows faster for it. A camp is not a thing on the map: nothing is built
and nothing is left behind.

___

## Movement

A band moves to one of the eight cells around it: north, north-east,
east, south-east, south, south-west, west, north-west.

- **A cell that cannot be entered is never a target**: one whose
  `passability` is 0 at that moment, and one outside the window.
- **A cell held by another band cannot be entered.** With one band on the
  map the rule does nothing until stage 3.
- **The cost is the passability of the target** and the size of the band,
  as [Band](../units/band.md#speed) states. A band of 15 enters grass in
  a tick, a forest in two, a swamp or a mountain in three.
- **A river slows the crossing** and never stops it. The bed of a great
  river is water and is not crossed.

The window does not follow the band in stage 2. It is 5120 km across,
and a band walks at most 50 km a day.

___

## The shore

Deep water is never entered. Shallows are, but only at the very shore: a
cell of a biome marked `shore` can be entered when it touches a cell of
land, by a side or a corner.

A band standing in the shallows gathers there like anywhere else: the
water is plenty and the food is good. The price is the threat, which is
high, and the encounters of the place: somebody drowns, or something in
the water takes a person.

```yaml
biomes:
  shallows:
    eras:
      band:
        shore: true
        properties:
          water: {base: 1.0}
          food: {base: 0.5, recovery: {days: 20}}
          threat: {base: 0.6}
          passability: {base: 0.3}
        resources: [water, forage]
```

Two other places are rich in water and pay for it. A river adds half of
the scale to the water of its cell, so a river in dry land is the best
water for days around. A swamp or a marsh has water everywhere, and
gathering it there may poison people.

___

## Chance encounters

An encounter is something the land does to a band. It is drawn once per
tick, in the phase `world`, from the game's stream `encounters`.

```text
chance = encounters.chance * value(threat, cell) * factor(action)
```

A camp is watched and a walking band is exposed: the factor is 0.5 for
`camp`, 1 for `gather` and 1.5 for `move`. With a chance of 0.1 a band
gathering in a forest meets something about once in five days.

When an encounter happens, its kind is drawn by weight among the kinds
that fit the biome and the action. A kind takes a share of the people,
drawn between its two bounds and rounded up to whole people.

| Kind        | Where                 | During   | Weight | People lost  |
|-------------|-----------------------|----------|--------|--------------|
| `predator`  | anywhere              | any      | 3      | 0 to 10%     |
| `accident`  | mountain, hills, outcrops, ice | `move` | 2 | 0 to 10%     |
| `drowning`  | shallows, river cells | `move`, `gather` | 3 | 5 to 15% |
| `poisoning` | swamp, marsh          | `gather` | 4      | 0 to 20%     |

A share that rounds to nobody is a scare: the event is reported and no
one is lost. Kinds are data, an entry each of the section `encounters`,
so a new one is a block of the tree and a message in two catalogues.

```yaml
encounters:
  chance: 0.1
  actions: {camp: 0.5, gather: 1.0, move: 1.5}
  kinds:
    predator: {weight: 3, loss: {min: 0.0, max: 0.1}}
    accident:
      weight: 2
      loss: {min: 0.0, max: 0.1}
      biomes: [mountain, hills, outcrops, ice]
      actions: [move]
    drowning:
      weight: 3
      loss: {min: 0.05, max: 0.15}
      biomes: [shallows]
      rivers: true
      actions: [move, gather]
    poisoning:
      weight: 4
      loss: {min: 0.0, max: 0.2}
      biomes: [swamp, marsh]
      actions: [gather]
      resources: [water]
```

___

## Seasons

A season is a modifier of properties, written per biome, as stage 1
built it for food. Stage 2 adds water and movement in the same shape and
changes no code for it.

| Season   | Food      | Water                     | Passability               |
|----------|-----------|---------------------------|---------------------------|
| `spring` | times 0.7 | times 1.2                 | times 0.8: mud and floods |
| `summer` | the base  | times 0.7 in dry biomes   | the base                  |
| `autumn` | times 1.2 | the base                  | the base                  |
| `winter` | times 0.4 | times 0.8                 | times 0.7: snow           |

The table is the temperate rule; each biome file carries its own
numbers, and the desert has no seasons at all. A property held at 0 or 1
by its base stays there: no season opens the deep sea.

Winter also slows what grows back. `eras.band.recovery` gives a
multiplier of the pace of recovery per property and season, and food
recovers at a quarter of its pace in winter. Frost, which would let a
band walk over a frozen river, stays a later item of the roadmap.

___

## One tick of a band

What stage 2 puts into the phases of
[one tick](../architecture/overview.md#one-tick).

1. **Commands** - a `call-council` is checked: the gap, the direction,
   the seat.
2. **Councils** - the vote is held. A proposal that passes becomes the
   band's intent.
3. **Decisions** - the band picks its action, among all three or among
   those its intent allows.
4. **Actions** - the band moves, gathers or camps; fatigue and what it
   knows are brought up to date.
5. **World** - cells recover; on the first tick of a day stores spoil;
   an encounter is drawn; on the last tick of a day people eat, states
   begin and end, people die and are born; an intent whose time is over
   ends; a proposal whose window closed is judged.
6. **Calendar**, 7. **Report** - as before. The report gains the band in
   `changes` and one counter per thing the lab will ask about.

The counters added: `population`, `food`, `water`, `status`, `moves`,
`gathers`, `camps`, `encounters`, `deaths`, `councils`.

___

## How a game ends

A game of stage 2 ends in one of two ways, and the index of games keeps
which.

| Outcome    | When                                           | Event           |
|------------|------------------------------------------------|-----------------|
| `died`     | fewer people than `units.band.population.least`| `band-died`     |
| `banished` | the player's status reached 0                  | `seat-banished` |

There is no victory yet: the way out of the band era is the transition
of stage 5. A long run of stage 2 is a band that is still alive.

___

## What the API shows

The snapshot gains the band and the seat; an update carries what changed
of them. Both views of the API show the same for now.

```json
{
  "units": [
    {
      "id": "band-1",
      "kind": "band",
      "place": {"scale": 0, "x": 2301, "y": 744},
      "population": 15,
      "stores": {"water": 30.0, "forage": 22.5},
      "fatigue": 0.3,
      "states": [],
      "action": {"kind": "gather", "resource": "forage"},
      "intent": null
    }
  ],
  "seat": {"name": "player", "unit": "band-1", "status": 50.0, "council_from": 40}
}
```

`council_from` is the tick from which the next council may be called.
What the band knows is read as a map: the rectangle of the map address
takes `known=band-1` and answers only with the cells that band knows, as
it remembers them.

___

## Open points

- **Fresh and salt water** - the shallows of the sea and of a lake are
  one biome, so a band drinks at the sea shore. Telling them apart needs
  a second biome or a mark like the river's.
- **The window and the band** - a band that reaches the edge of the
  window stops there. A window that follows the band is set with the
  size of the window in stage 3.
- **Night** - the night pulls towards the camp only through a weight.
  Whether walking at night should also be more dangerous is seen in the
  lab.
- **Encounters that give** - every kind takes. Finding a carcass or a
  spring would be the same block of data with a gain in place of a loss.
- **The snapshot every tick** - a band adds its memory to the snapshot,
  up to some thousands of cells. The size is measured before the store
  is changed, as the architecture overview left open.
