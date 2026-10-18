# Bands

#game #band #stage2

The band era from the first tick to the last: where a band starts, what
it does in a day, how it moves, what the land and the seasons do to it
and how the game ends. Part of the stage 2 design in
[the roadmap](../roadmap.md). The numbers of the band are in
[Band](../units/band.md).

- [The start](#the-start)
- [A day](#a-day)
- [The actions](#the-actions)
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

The morning, the midday and the afternoon are for work: the band walks,
roams or gathers as [the decision function](decisions.md) says. The
evening and the night, the parts of `units.band.camp_parts`, are for the
camp: the band camps then whatever it wants or the council bound it to,
and a seated band holds its council in the evening.

Things that are counted by the day happen at its edges. The first tick
of a day throws away spoiled stores. The last tick feeds the people,
counts every member's hunger and thirst, and adds the day's births.

___

## The actions

| Action   | Does                                                            | Fatigue   |
|----------|-----------------------------------------------------------------|-----------|
| `move`   | walks towards one of the eight cells around                     | grows     |
| `roam`   | walks there slower, foraging the cell ahead on the way          | grows less |
| `gather` | sends the gatherers after food and water, as the need for each weighs | grows |
| `camp`   | rests where it stands                                           | falls     |
| `build`  | builds a winter camp on the cell it stands on                   | grows     |

A roaming band takes `roaming.share` of what a tick of gathering would
give, of every resource the cell ahead gives that the band is short of,
and that cell pays for it
as for a gathering; see [Band](../units/band.md#gathering). The band
picks between walking and roaming itself, but a hungry band does not
walk: hungry or thirsty, it only roams. A camp is not a thing on the map: nothing is
built and nothing is left behind. A winter camp is the one thing a band
builds, and only under the council's `winter-camp`; it is the band's
while the band stands on its cell, see
[Band](../units/band.md#winter-camp).

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
- **The way is kept overnight.** The camp of the evening and the night
  keeps the progress into the next cell, so a cell that takes longer than
  one day to cross is entered on the next. A gather loses it.
- **A river slows the crossing** and never stops it. The bed of a great
  river is water and is not crossed.

The window does not follow the band in stage 2. It is 5120 km across,
and a band walks at most 50 km a day.

___

## The shore

A band never enters water, deep or shallow: a cell is entered when its
passability is above 0, and the shallows have 0 in the band era. Boats,
a skill or the tribe era may open them later, by data alone.

A band gathers from the shallows from the land beside them. A biome
marked `shore` is a source for a band on any cell next to it, by a side
or a corner: gathering takes a resource from the cell itself or from the
shore beside it that lists the resource, whichever gives more of it, and
lowers the stock of that cell. A tie goes to the band's own cell, then
to the shores clockwise from the north. Roaming still takes from the
cell ahead only.

The band sees a cell by the shore as that good: every property a
resource of a known shore beside it feeds is the larger of the two,
while the threat and the passability stay the cell's own. The decision
function, the pull of the land, routes, the table of the council and
the verdict all read the cell so. In winter the shallows keep their
food and water while grass loses most of both, so a band winters well
on a coast.

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
          passability: {base: 0.0}
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
`camp`, 1 for `gather`, 1.2 for `roam` and 1.5 for `move`. With a chance of 0.02 a band
gathering in a forest meets something about once in twenty-five days.

When an encounter happens, its kind is drawn by weight among the kinds
that fit the biome and the action. A kind takes a share of the people,
drawn between its two bounds, and may injure a share of those left,
drawn with the same number. The share is taken of the people weighed by
how exposed their stage and age are, so the youngest children and the
elders die first; see
[Deaths](../units/band.md#deaths). A band in camp loses half the share
it would, and the wounded get a severity, heavier from an accident; see
[Shelter](../units/band.md#shelter) and
[Injuries](../units/band.md#injuries). An encounter that killed or injured
somebody leaves the band dreading its cell; see
[Dread](decisions.md#dread).

| Kind        | Where                 | During   | Weight | People lost  | Injured   |
|-------------|-----------------------|----------|--------|--------------|-----------|
| `predator`  | anywhere              | any      | 3      | 0 to 10%     | 0 to 10%  |
| `accident`  | mountain, hills, outcrops, ice | `move`, `roam` | 2 | 0 to 10% | 5 to 15% |
| `drowning`  | river cells; shallows once entered | `move`, `roam`, `gather` | 3 | 5 to 15% | none |
| `poisoning` | swamp, marsh          | `gather` | 4      | 0 to 20%     | none      |

A share that rounds to nobody is a scare: the event is reported and no
one is lost. Kinds are data, an entry each of the section `encounters`,
so a new one is a block of the tree and a message in two catalogues.

```yaml
encounters:
  chance: 0.02
  actions: {camp: 0.5, build: 1.0, gather: 1.0, roam: 1.2, move: 1.5}
  kinds:
    predator: {weight: 3, loss: {min: 0.0, max: 0.1}, injured: {min: 0.0, max: 0.1}}
    accident:
      weight: 2
      loss: {min: 0.0, max: 0.1}
      injured: {min: 0.05, max: 0.15}
      wounds: {light: 0.2, medium: 0.4, heavy: 0.4}
      biomes: [mountain, hills, outcrops, ice]
      actions: [move, roam]
    drowning:
      weight: 3
      loss: {min: 0.05, max: 0.15}
      biomes: [shallows]
      rivers: true
      actions: [move, roam, gather]
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

1. **Commands** - a `vote` is checked: the seat, the council, a second
   vote, the place and its route.
2. **Councils** - a council that sits is decided with the player's
   answer, and rises. The winner becomes the band's intent; an option the
   player carried against the leader is also judged at the next council.
3. **Decisions** - the band picks its action, among all it may take or
   among those its intent allows, along its route under a go, building
   first under a winter camp; in the tick of a council, and while it is
   tired under an intent, it camps.
4. **Actions** - the band moves, gathers, camps or builds; fatigue and what it
   knows are brought up to date; a band that stands on the place of its
   go has arrived.
5. **World** - cells recover; on the first tick of a day stores spoil;
   an encounter is drawn, under the threat a winter camp lowers; on the
   last tick of a day people eat, states
   begin and end, and the members age, die, heal, are hurt, give birth
   and conceive, in the order of [Deaths](../units/band.md#deaths). The
   share of the active parts the band camped heals faster and shelters
   from frailty. Last, the counters the band learns by are brought up to
   date and the skills they teach are learned; see
   [Skills](skills.md#counters).
6. **Calendar** - as before; when the new part of the day is
   `council.part` and an occasion calls it, the intent ends and is
   judged, and the council sits down with its table. With an empty seat
   the leader of the table binds the band and nothing sits.
7. **Report** - as before. The report gains the band in `changes` and
   one counter per thing the lab will ask about.

The counters added: `population`, `food`, `water`, `status`, `moves`,
`gathers`, `camps`, `builds`, `encounters`, `deaths`, `councils`, then one per
stage (`child`, `adult`, `elder`), `pregnant` and `injured`, and `skills`,
the skills the band knows.

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
      "id": 1,
      "kind": "band",
      "place": {"scale": 0, "x": 2301, "y": 744},
      "population": 15,
      "ages": {"child": 3, "adult": 10, "elder": 2},
      "pregnant": 1,
      "injured": 0,
      "wounds": {"light": 0, "medium": 0, "heavy": 0},
      "stores": {"water": 30.0, "forage": 22.5},
      "goods": {"stones": 4.0},
      "fatigue": 0.3,
      "states": [],
      "action": {"kind": "gather", "shares": {"forage": 0.83, "water": 0.17}},
      "intent": {"proposal": {"kind": "go", "to": {"x": 2304, "y": 742}}},
      "route": [{"x": 2302, "y": 743}, {"x": 2303, "y": 742}, {"x": 2304, "y": 742}],
      "roles": {"gatherer": 14, "nanny": 1},
      "camp": null,
      "lore": ["orientation"]
    }
  ],
  "seat": {"name": "player", "unit": 1, "status": 50.0, "seated": true, "council": null}
}
```

`ages` counts the members by stage, `pregnant` and `injured` the
members who are, `wounds` the injured by severity; the members themselves stay in the state of the game.
`route` is the cells still ahead to the place of a go, empty when the
band is not on its way. `roles` counts the members by role.
`lore` is the skills the band knows; see [Skills](skills.md).
`goods` is the goods it holds, in its stores and in the kits of its
members, per good; see [Skills](skills.md#what-the-api-shows).
`camp` is the winter camp, `{x, y, built}` with `built` the share done,
or null.
`council` is the table of the council of the day while it sits; see
[The snapshot](../api/protocol.md#the-seat). What the band knows is read as a map: the rectangle of the map address
takes `known=1` and answers only with the cells that band knows, as
it remembers them.

___

## Open points

- **Fresh and salt water** - the shallows of the sea and of a lake are
  one biome, so a band drinks at the sea shore. Telling them apart needs
  a second biome or a mark like the river's.
- **The window and the band** - a band that reaches the edge of the
  window stops there. A window that follows the band is set with the
  size of the window in stage 3.
- **Night marches** - a band never walks in the evening or the night.
  A flight from danger in the dark would need an exception to that.
- **Open water** - the biome `water` lists water but is no shore, so a
  band by a lake or the sea drinks only where the shallows lie between.
- **Shore encounters** - a band gathering from the shallows beside it
  meets the encounters of its own cell, not drowning.
- **Encounters that give** - every kind takes. Finding a carcass or a
  spring would be the same block of data with a gain in place of a loss.
