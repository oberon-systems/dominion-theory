# Band

#unit #band #stage2

A band is the first unit of the game: some tens of foraging nomads who
walk, roam, gather, camp, build a winter camp and nothing else. This document says what a band is
made of and gives every number it reads. Part of the stage 2 design in
[the roadmap](../roadmap.md); how a band lives through a day is told in
[Bands](../game/01_bands.md).

- [What a band holds](#what-a-band-holds)
- [Population](#population)
- [Births](#births)
- [Deaths](#deaths)
- [Injuries](#injuries)
- [Shelter](#shelter)
- [Winter camp](#winter-camp)
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
| `members`    | its people one by one, the player among them            |
| `population` | how many members, read from `members`                   |
| `stores`     | what it carries, per resource, in lots by day gathered  |
| `fatigue`    | how tired it is, from 0 to 1                            |
| `states`     | which of the bad states hold now; none means `normal`   |
| `action`     | what it did in the last tick                            |
| `intent`     | what the council bound it to, if anything               |
| `known`      | the cells it has seen and when                          |
| `dread`      | the extra threat it sees on cells where it was struck   |
| `unease`     | how much more staying in danger makes it fear threat    |
| `route`      | the cells still ahead to the place of a go, and the day they were laid |

Stage 2 puts one band on the map, the player's. Other bands are stage 3.

___

## Population

A band is its members, kept one by one. A member has an age in days, a
sex and three marks: pregnant until a day, resting after a birth until
a day, and a wound with its severity and the days of healing it still
needs. The population is the number of members,
and a band dies when fewer than 5 are left; the game ends with it.

A band starts with 15 members: the player and 14 others, adults of a
random age from 4 to 15 years and of a random sex. None is older than
`start.oldest`, so the first elder comes as the third year begins, about
when the first child born grows up. The player is a
member who never dies, the line the player stands for; a family of the
player is a later step. Every draw of this document comes from the
stream `people` of the game, so the same seed lives the same band.

Growth is what a band lives for: it wants to continue its kind. The
threshold of 150, at which a band becomes a tribe, belongs to stage 5;
reaching it in about 18 years, the 15 to 30 minutes of a band stage at
the pace of the screen, needs about 13% a year.

### Stages

Every member is in a stage of life by its age. A stage weighs what a
member does against an adult, whose weights are all 1.

| Stage   | Ages        | Gathers | Carries | Eats | Pace | Tires | Conceives | Votes |
|---------|-------------|---------|---------|------|------|-------|-----------|-------|
| `child` | 0 to 3      | 0       | 0.25    | 0.5  | 0.7  | 1.3   | no        | no    |
| `adult` | 4 to 16     | 1       | 1       | 1    | 1    | 1     | yes       | yes   |
| `elder` | 17 and over | 0       | 0.5     | 0.7  | 0.8  | 1.3   | no        | yes   |

A band sums its members where an amount grows with the people, and
takes the mean where it is a pace. A wounded member gathers and walks
at the shares of its severity, see [Injuries](#injuries).

```text
gatherers = sum of gathers, times severity.gathers for the wounded
eaters    = sum of eats
carriers  = sum of carries
pace      = mean of pace, times severity.pace for the wounded
tires     = mean of tires
```

Gathering, eating and carrying read these sums where they read the
population before; the speed is multiplied by the mean pace and a gain
of fatigue by the mean tiring. A band of adults lives as a band of
heads did. Only the stages that vote sit in the council; see
[Indirect control](../game/indirect_control.md#the-table-of-votes).

### Wellbeing

Wellbeing is a number from 0 to 1, taken once a day, after the people
eat. It is the mean of four parts, each weighed by
`population.wellbeing`, and it drives [frailty](#deaths).

| Part     | Is                                                        |
|----------|-----------------------------------------------------------|
| `food`   | 1 minus the hunger of the band                            |
| `water`  | 1 minus the thirst of the band                            |
| `safety` | 1 minus the threat of the cell the band stands on         |
| `rest`   | 1 minus the fatigue                                       |

Hunger and thirst are the levels of [Decisions](../game/decisions.md#needs):
a band with two days of food in its stores is sated, one with less than
a day is hungry.

___

## Births

A woman of a stage that conceives, an adult, may conceive on a day when
she is neither pregnant nor resting, with the chance
`birth.conceive_per_day`. There are no pairs: a band is nearly a herd,
and one adult man in it is enough. Nobody conceives on a day when the
band cannot feed more children:

- the food in its stores, counted before the meal of the day, lasts
  fewer than `birth.days`, 2;
- starvation or thirst holds;
- there is no adult man.

A pregnancy lasts `birth.pregnancy`, 3 months. At its end the child
lives with the chance `birth.child_survives`, 0.5, and the mother dies
with `birth.mother_dies`; the player never does. The mother then rests
for a random span from `birth.pause.min` to `birth.pause.max`, one to
two months, and does not conceive. A child is born at age 0, of a
random sex.

How many children grow up is no number of the tree. It follows from
hunger, thirst, encounters and frailty, so a band that keeps to safe
and fed land raises more of them: the reason a people seeks safety.

___

## Deaths

Every cause weighs the members by the vulnerability of their stage,
`dies`, and the player's weight is always 0. The child's weights are
those of a newborn; see [Children grow safer](#children-grow-safer).

| Cause       | How many die                                            | Child | Adult | Elder |
|-------------|---------------------------------------------------------|-------|-------|-------|
| `hunger`    | `starvation.loss_per_day` of the sum of weights, a day  | 2     | 1     | 1.5   |
| `thirst`    | `thirst.loss_per_day` of the sum of weights, a day      | 2     | 1     | 1.5   |
| `encounter` | the share the encounter took of the sum of weights      | 3     | 1     | 2     |
| `frailty`   | each member by its own chance, a day                    | 1.2   | 0.05  | 0.3   |
| `age`       | each member past `age.begins` by its own chance, a day  | -     | -     | -     |
| `birth`     | a mother at the birth                                   | -     | -     | -     |

A state rounds its count up, so it costs somebody every day it holds;
an encounter rounds to the nearest, so it may be a scare. Who dies of
a count is drawn by the weights, nobody twice: a newborn is twice as
likely as an adult to die of hunger and three times of a predator.

Frailty is illness, cold and all else a band in poor shape suffers. Its
chance falls as wellbeing rises:

```text
frailty a year = dies.frailty * (1 - wellbeing) * sheltered
age a year     = age.per_year * 2 ^ ((age - age.begins) / age.doubles), at most 1
```

Both are asked every day as a share of the year. A newborn at wellbeing
0.85 dies of frailty at 0.18 a year and a child of three at 0.02, so
about four in five reach four; at wellbeing 0.5 about half do, before
hunger and predators take their share. A band in camp dies less of
frailty, see [Shelter](#shelter). Death of age begins at 0.15 a year at 17 and doubles
every two years: about half live to 20, and one in five to 22.

### Children grow safer

A stage with `settles` dies by its own weights only at its start. The
difference to the weights of the next stage halves for every `settles`
lived in the stage, so a child nears an adult as it grows. Every cause
follows it, injuries too.

```text
weight = next + (own - next) * 0.5 ^ (age in the stage / settles)
```

The child settles in 7 months:

| Age       | 0   | 7 months | 14 months | 21 months | 3 years |
|-----------|-----|----------|-----------|-----------|---------|
| encounter | 3   | 2        | 1.5       | 1.25      | 1.1     |
| hunger    | 2   | 1.5      | 1.25      | 1.13      | 1.05    |
| frailty   | 1.2 | 0.63     | 0.34      | 0.19      | 0.11    |
| injury    | 0.5 | 0.75     | 0.88      | 0.94      | 0.97    |

Where adults die at 0.22 a year, as in a hard game, about one child in
five grows up, against one in twenty-five when the weights held for the
whole stage. The reference of lives counts the children who grew up and
those who died each year.

### The order of a day

A day ends in a fixed order: the meal and the states, then age,
frailty, injuries, births and conceptions. The council answers for
hunger, thirst and encounters only; see
[Indirect control](../game/indirect_control.md#status).

___

## Injuries

A member who is not wounded is hurt on a day with the chance
`injury.per_day` times its weight `dies.injury`: 0.5 for a newborn,
nearing 1 as the child grows, 1 for an adult, 1.5 for an elder. An encounter injures as well: a kind may
carry `injured`, a share drawn with its loss and taken of the same
weights. Predators injure up to 10% of the band, accidents 5 to 15%.

A wound has a severity, drawn when the member is hurt by the weights
`injury.drawn`. A kind of encounter may carry weights of its own,
`wounds`: an accident leans heavy. The severity sets how many days of
healing the wound needs and the share of pace and gathering it leaves.

| Severity | Days | Pace | Gathers | Drawn | Drawn by an accident |
|----------|------|------|---------|-------|----------------------|
| `light`  | 10   | 0.8  | 0.7     | 0.5   | 0.2                  |
| `medium` | 15   | 0.6  | 0.4     | 0.3   | 0.4                  |
| `heavy`  | 20   | 0.4  | 0.2     | 0.2   | 0.4                  |

A wound heals at the end of every day. A day on the move heals one
day, a day wholly in camp `injury.heal_in_camp`, 2, and a day partly in
camp by the share it camped. A wound kills nobody by itself. Every new
wound is the event `people-injured`.

```text
healed a day = 1 + (heal_in_camp - 1) * camped
```

___

## Shelter

A band in camp is sheltered: it keeps its weak by the fire. Shelter is
the camp action in any part of the day, the evening and the night
included, not the council's stay. It counts in no decision: the
decision function and the council do not read it.

- An encounter met in camp takes `shelter.encounter`, 0.5, of the share
  of the people it would take. It hurts as many.
- Frailty at the end of a day is multiplied by `sheltered`.
- Hunger, thirst, age and birth are untouched.

```text
camped    = active parts of the day the band camped / active parts of the day
sheltered = 1 - (1 - shelter.frailty) * camped
```

The active parts are those not named by `camp_parts`: the morning, the
midday and the afternoon. A band that rests all day halves its frailty;
a band that walks all day has none of it.

___

## Winter camp

A winter camp is the council's answer `winter-camp`, offered through the
winter and the last 10 days of the autumn. The band builds it on the cell
it stands on with the action `build`: `winter_camp.build`, 2 days of the
active parts, 6 ticks, with no gathering; while it starves or thirsts
it gathers instead, and the share built waits for it. Before game
d67475ee a band whose stores fell under a day already stopped building,
which in winter was nearly always, so a camp lost was never built again. The band holds the camp as its
cell and the share built, `camp: {x, y, built}`.

Once built, while the band stands on that cell, whatever its intent:

| Effect                               | Factor                     |
|--------------------------------------|----------------------------|
| the threat of encounters and of wellbeing, and the threat the band sees | `winter_camp.threat`, 0.5 |
| the age of a lot against its time to spoil | `winter_camp.spoil`, 0.5 |
| what the people eat and drink, and so the days the stores last | `winter_camp.consumption`, 0.8 |
| what a camp takes off fatigue        | `winter_camp.rest`, 1.5    |
| what staying in it is worth to the others, added | `winter_camp.kept`, 0.2 |

Gathering goes on, and the shelter of a camp holds as it does anywhere.
A band that steps into another cell loses the camp, built or not, and a
band that builds on another cell starts anew. The camp is left with the
first season that does not offer it, the spring: its effects and its
reach end there, so a camp never becomes a home for the whole year.

### The reach of a camp

A band ranges while it is bound to a winter camp or stands on its camp,
built or not: from the evening the camp is chosen, the days of the build
included. A ranging band gathers each resource from the best cell within
`winter_camp.reach`, 1: its own and the 8 around it. A cell around counts
when the band can enter it and it lists the resource, and it gives
`winter_camp.afar`, 1.0, of a gathering; the cell gathered from pays its
stock. The band itself does not move.

Before game 864bd5ae a camp gathered its own cell alone: in winter that
cell was stripped in days, the band starved on it and never finished the
build, and the others judged the camp by the bare cell and wanted to go.

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

An adult carries 6 kg, a child a quarter of it and an elder half. A
band never gathers more than it can carry: what does not fit is left on
the cell and the stock is not lowered for it.

___

## Gathering

A gathering tick is spent on one resource. What the band takes is its own
rate times the property of the cell, as
[Biomes](../biomes/overview.md#properties) defines it.

```text
taken = gatherers * rate * value(property, cell)
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
| `food`   | 100 units         |
| `water`  | 2000 units        |

A band gathers on the cell it stands on and nowhere else, but for a
roaming band, which forages the cell ahead as it walks into it. It
gathers only the resources the biome lists. A roaming band is short of a
resource while the days of it in the stores are below the top level of
[Decisions](../game/decisions.md#needs), 2: it does not fill its carry
with water it has enough of and leave no room for food.

| Roaming    | Is                                                        |
|------------|-----------------------------------------------------------|
| `speed`    | the share of the walking pace, 0.75                       |
| `share`    | the share of a gathering tick taken of every resource the band is short of, 0.5 |
| `hunger`   | the need at which a band only roams, 0.8: a hungry band   |

A full forest feeds a band of 15 four or five days before it gives too
little and the band is pushed on.

___

## Consumption

People eat and drink once a day, in the phase `world` of the last tick of
the day.

| Resource | Per person per day |
|----------|--------------------|
| `forage` | 1.0                |
| `water`  | 1.0                |

The amounts are per adult, and a child eats half and an elder 0.7 of
them. So 15 adults need 15 kg of food and 15 litres of water a day, 30 kg of
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
speed = max(slowest, base - slowdown * population / 10) * efficiency * pace
```

With a base of 1.2 and a slowdown of 0.03 a band of 15 walks at 1.155
and a band of 150 at 0.75; no band is slower than 0.3. A step along a
diagonal costs the same as a straight one. Progress above 1 is not
carried over. A camp keeps the progress, so a cell the band cannot cross
in the active parts of one day is entered on the next; a gather, or a
step towards another cell, loses all of it.

___

## Fatigue

Fatigue runs from 0 to 1. Walking, roaming and gathering add to it,
camping takes it away. A band works in the morning, at midday and in
the afternoon and camps in the evening and the night, the parts named
by `camp_parts`; it never walks or gathers then.

| Action    | Fatigue per tick |
|-----------|------------------|
| `move`    | plus 0.3         |
| `roam`    | plus 0.15        |
| `gather`  | plus 0.1         |
| `camp`    | minus 0.3        |
| `build`   | plus 0.15        |

A gain is multiplied by the mean tiring of the members, so a band of
many children and elders tires sooner. Fatigue weighs in no decision. It takes from what the band can do: its
pace and every gathering, roaming's share included, are multiplied by

```text
efficiency = 1 - fatigue.slows * fatigue
```

so a band at fatigue 1 walks and gathers at half. The two camps of the
evening and the night take away 0.6 a day. Three ticks of walking add
0.9, so a band that marches day after day slows down; three of roaming
add 0.45 and three of gathering 0.3, so a band that roams or gathers is
rested by the morning.

___

## States

A band is `normal` when none of the three bad states holds. They are
independent and may hold together.

| State        | Begins when                         | Does                            | Ends when                  |
|--------------|-------------------------------------|---------------------------------|----------------------------|
| `starvation` | food was short for 2 days running   | 5% of the people die every day  | a day's food is eaten in full |
| `thirst`     | water was short for 1 day           | 15% of the people die every day | a day's water is drunk in full |
| `tiredness`  | fatigue reaches 0.8                 | nobody is born                  | fatigue falls to 0.3       |

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
Older memories are dropped.

A band knows what the seasons do to its land. When a season starts, every
remembered cell is expected as the new season makes it: the share of its
stock that the band saw is kept, and the seasonal modifiers of the new
season replace those of the old. A meadow seen full in summer is
remembered as a winter meadow once winter comes, not as a summer one. The
cells whose memory changed go out in `known` of that update. The decision function reads nothing but what
is known, and so does the observation of the seat.

In the reference runs a band remembers 25 to 50 cells, up to 7 KB of the
snapshot; `known` and `snapshot` in `tests/runner/lives.json` follow it.

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
      stage: adult
      oldest: {years: 15}
    population:
      least: 5
      wellbeing: {food: 1.0, water: 1.0, safety: 1.0, rest: 1.0}
    people:
      stages:
        child:
          until: {years: 4}
          settles: {months: 7}
          gathers: 0.0
          carries: 0.25
          eats: 0.5
          pace: 0.7
          tires: 1.3
          conceives: false
          votes: false
          dies: {hunger: 2.0, thirst: 2.0, encounter: 3.0, frailty: 1.2, injury: 0.5}
        adult:
          until: {years: 17}
          gathers: 1.0
          carries: 1.0
          eats: 1.0
          pace: 1.0
          tires: 1.0
          conceives: true
          votes: true
          dies: {hunger: 1.0, thirst: 1.0, encounter: 1.0, frailty: 0.05, injury: 1.0}
        elder:
          gathers: 0.0
          carries: 0.5
          eats: 0.7
          pace: 0.8
          tires: 1.3
          conceives: false
          votes: true
          dies: {hunger: 1.5, thirst: 1.5, encounter: 2.0, frailty: 0.3, injury: 1.5}
      age: {begins: {years: 17}, per_year: 0.15, doubles: {years: 2}}
      injury:
        per_day: 0.002
        heal_in_camp: 2.0
        severities:
          light: {days: 10, pace: 0.8, gathers: 0.7}
          medium: {days: 15, pace: 0.6, gathers: 0.4}
          heavy: {days: 20, pace: 0.4, gathers: 0.2}
        drawn: {light: 0.5, medium: 0.3, heavy: 0.2}
      birth:
        pregnancy: {months: 3}
        pause: {min: {months: 1}, max: {months: 2}}
        conceive_per_day: 0.05
        days: 2.0
        child_survives: 0.5
        mother_dies: 0.05
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
    roaming: {speed: 0.75, share: 0.5, hunger: 0.8}
    fatigue:
      move: 0.3
      roam: 0.15
      gather: 0.1
      camp: -0.3
      build: 0.15
      slows: 0.5
    camp_parts: [evening, night]
    states:
      short: 0.75
      starvation: {after: {days: 2}, loss_per_day: 0.05}
      thirst: {after: {days: 1}, loss_per_day: 0.15}
      tiredness: {begins: 0.8, ends: 0.3}
    sight: 2
    memory: {days: 20}
    dread: {encounter: 0.3, lasts: {days: 20}}
    unease: {gain: 0.1, fade: 0.2}
    route: {margin: 4, threat: 2.0, hunger: 1.0, thirst: 1.0}
    shelter: {encounter: 0.5, frailty: 0.5}
    winter_camp:
      offered: {seasons: [winter], before: {days: 10}}
      build: {days: 2}
      reach: 1
      afar: 1.0
      kept: 0.2
      threat: 0.5
      spoil: 0.5
      consumption: 0.8
      rest: 1.5
```

`dread` and `unease` are told in [Decisions](../game/decisions.md#dread),
`route` in [The route](../game/decisions.md#the-route).

```yaml
eras:
  band:
    capacity: {food: 100, water: 2000}
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
- Every stage but the last has an age `until`, and the ages rise; the
  last has none.
- Only a stage before the last settles, over at least a day.
- At least one stage conceives, and the start stage is one that ends.
- `birth.pause.min` is not above `birth.pause.max`.
- `injury.drawn` and the `wounds` of an encounter name only severities
  of `injury.severities`, and some weight is above 0.
- `injury.heal_in_camp` is not below 1.
- The start stores fit what the start population carries.
- A start biome exists and can be entered.
- `tiredness.ends` is below `tiredness.begins`, and both lie in 0 to 1.
- Every name of `camp_parts` is one of `time.day_parts`.
- Every season of `winter_camp.offered` is one of `time.seasons`, and
  `winter_camp.build` is not zero.
- A share, a chance and a loss lie between 0 and 1.

___

## Open points

- **Gathering both at once** - a tick is spent on one resource. Whether a
  band splits its people between food and water is seen in the lab.
- **The player's family** - the player is one member who never dies. A
  family that carries the player's line, an heir taking the seat, is a
  later step.
- **A start of adults only** - a band starts without children or elders,
  so for four years no new adult joins it. A start with every stage is
  to be weighed in the lab.
- **Carrying against speed** - a loaded band walks as fast as an empty
  one.
- **Drinking on the spot** - a band on a river still drinks from its
  stores. Water from the cell at the moment of drinking would make a
  river worth camping on.
