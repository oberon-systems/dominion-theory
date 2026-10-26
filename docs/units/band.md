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
- [Hunger and thirst](#hunger-and-thirst)
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
| `stores`     | what it carries, per resource, in lots by day gathered and, for goods, quality |
| `fatigue`    | how tired it is, from 0 to 1                            |
| `states`     | which of the bad states hold now; none means `normal`   |
| `action`     | what it did in the last tick                            |
| `intent`     | what the council bound it to, if anything               |
| `known`      | the cells it has seen and when                          |
| `dread`      | the extra threat it sees on cells where it was struck   |
| `unease`     | how much more staying in danger makes it fear threat    |
| `route`      | the cells still ahead to the place of a go, and the day they were laid |
| `camp`       | the cell of its winter camp and the share of it built   |

Stage 2 puts one band on the map, the player's. Other bands are stage 3.
What a band learns, `lore`, and the goods its members hold, `kit`, are
told in [Skills](../game/skills.md#stocks-and-holders). A member's `kit`
is a stock like `stores`: it weighs in the load of the band, and the kit
of a member who dies goes back to the stores.

___

## Population

A band is its members, kept one by one. A member has an age in days, a
sex and four marks: pregnant until a day, resting after a birth until
a day, a wound with its severity and the days of healing it still
needs, and the days of a sickness left; see
[Sickness and herbs](../game/skills.md#sickness-and-herbs). It also
keeps the share of meat in its rations, its [diet](#diet). The population is the number of members,
and a band dies when fewer than 5 are left; the game ends with it.

A band starts with 15 members: the player and 14 others, adults of a
random age from 4 to 12 years and of a random sex. None is older than
`start.oldest`, so the first elder comes as the sixth year begins, when
the first children born are grown. The player is a
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
| `elder` | 17 and over | 0.4     | 0.5     | 0.7  | 0.8  | 1.3   | no        | yes   |

A band sums its members where an amount grows with the people, and
takes the mean where it is a pace. A wounded member gathers and walks
at the shares of its severity, see [Injuries](#injuries), a hungry
or thirsty one at `people.weakened`, 0.6, see
[Hunger and thirst](#hunger-and-thirst), and a sick one at
`people.sickness`, 0.5 of its gathering and 0.7 of its pace.

```text
gatherers = sum of gathers, times severity.gathers for the wounded, times weakened.gathers for the hungry,
            times sickness.gathers for the sick, times the gathers of the role
eaters    = sum of eats
carriers  = sum of carries
pace      = mean of pace, times severity.pace for the wounded, times weakened.pace for the hungry,
            times sickness.pace for the sick
tires     = mean of tires
```

Gathering, eating and carrying read these sums where they read the
population before; the speed is multiplied by the mean pace and a gain
of fatigue by the mean tiring. A band of adults lives as a band of
heads did. Only the stages that vote sit in the council; see
[Indirect control](../game/indirect_control.md#the-table-of-votes).

### Roles

Every member has a role. Carers, never the player, are called as
nannies until every child is cared for, each for the `cares` of the
role, 5, or 8 while it holds a sling: 6 children call two nannies, or
one with a sling. The first is a woman of a stage
that conceives, the pregnant and the resting first, then the oldest;
the second and the third are the elders first, either sex, the oldest
first, then the women. So an elder keeps the children and an adult
woman goes out to gather. A nanny keeps the
children by the camp and gathers half of what a gatherer does. Everyone
else is a gatherer. The roles are laid anew at the end of every day.

| Role       | Gathers | One for every |
|------------|---------|---------------|
| `gatherer` | 1       | -             |
| `nanny`    | 0.5     | 5 children, 8 with a sling |
| `hunter`   | 1       | 5 members, each holding a spear |

A nanny that gathered nothing took a third of the hands of a band with
more children than adults: the headless band of seed 7 had 16 children,
11 adults and 4 nannies in its third winter and starved.

A band that runs short sends its nannies to gather, one a day. At the
end of a day, after eating, while a member went short of food or water,
one more nanny leaves the children, until none is left. While the
stores of both still feed the band `people.leaves.back` days (1), one
comes back a day. The last nanny of the order leaves first, so the
pregnant and the resting stay. In a band whose gatherers died, the
nannies kept the children while everyone starved; now they go out.

A band rarely holds more than 2 days at the end of a day, so a nanny
sent out while the stores fed less than a day came back only once they
fed 3 days, which meant she almost never came back.

The role `hunter` opens with the skill of spears and takes the men
first, after the nannies; who hunts and when is told in
[Skills](../game/skills.md#hunting).

Children are gatherers who gather nothing for their stage, and elders
gather 0.4. Elders neither pull a litter nor hunt: those are the work of
adults. A role is meant to grow with the doing - a member who fetches water for
long fetches it better - once a tribe shares its work more finely.

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

### Diet

Every member keeps the share of meat in its rations, from 0 to 1. A day
the band eats, the share of `diet.meat` in the food it ate that day
comes into the share of every member, the same for all:

```text
meat = meat * diet.keeps + meat today * (1 - diet.keeps)
```

`diet.keeps` is 0.8, so a band that turns to meat alone has a share of
0.5 after three days and 0.9 after ten; a day the band ate nothing
leaves the share as it was. The share does `diet.full` in its measure:

| Effect     | `full` | At a share of 0.5 | Of                                |
|------------|--------|-------------------|-----------------------------------|
| `frailty`  | 0.85   | 0.925             | the frailty weight, see [Deaths](#deaths) |
| `heals`    | 1.25   | 1.125             | the days a wound heals a day, see [Injuries](#injuries) |
| `carries`  | 1.1    | 1.05              | the carry of the member, see [Stores](#stores) |

```text
effect = 1 + (full - 1) * meat
```

Raw meat still sickens, see
[Sickness and herbs](../game/skills.md#sickness-and-herbs): a band fed
on meat is stronger and heals faster, and needs herbs to stay well. A
record keeps the share of every member as `meat`, and the replay shows
it.

___

## Births

A woman of a stage that conceives, an adult, may conceive on a day when
she is neither pregnant nor resting. There are no pairs: a band is
nearly a herd, and one adult man in it is enough. The chance follows the
food the band holds, the whole year round:

```text
chance = birth.conceive_per_day * min(days the food in the stores lasts / birth.stores, 1)
```

`birth.stores` is 3 months, a winter: a band that could live through a
winter on its stores conceives at the full chance, one with half of that
at half, one with nothing in store not at all. The food is counted
before the meal of the day, the dried reserve with it. Nobody conceives
while starvation or thirst holds, or with no adult man.

A pregnancy lasts `birth.pregnancy`, 3 months. At its end the child
lives with the chance `birth.child_survives`, 0.5, and the mother dies
with `birth.mother_dies`; the player never does. The mother then rests
for a random span from `birth.pause.min` to `birth.pause.max`, one to
two months, and does not conceive. A child is born at age 0, of a
random sex.

Once the band knows `midwifery`, its oldest woman but the mother attends
every birth. A herb held is spent on it; see
[Skills](../game/skills.md#the-skills).

| Birth                         | The child lives | The mother dies       |
|-------------------------------|-----------------|-----------------------|
| alone                         | 0.5             | 0.05                  |
| attended                      | 0.55            | 0.05 x 0.75 = 0.0375  |
| attended, a herb spent on it  | 0.6             | 0.05 x 0.5 = 0.025    |

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
| `hunger`    | every member with nothing left of its food, a day       | -     | -     | -     |
| `thirst`    | every member with nothing left of its water, a day      | -     | -     | -     |
| `encounter` | the share the encounter took of the sum of weights      | 3     | 1     | 2     |
| `frailty`   | each member by its own chance, a day                    | 1.2   | 0.05  | 0.3   |
| `age`       | each member past `age.begins` by its own chance, a day  | -     | -     | -     |
| `birth`     | a mother at the birth                                   | -     | -     | -     |

Hunger and thirst take every member whose reserve ran out; see
[Hunger and thirst](#hunger-and-thirst). An encounter rounds to the
nearest, so it may be a scare. Who dies of its count is drawn by the
weights, nobody twice: a newborn is three times as likely as an adult
to die of a predator.

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
frailty, see [Shelter](#shelter). A sick member weighs
`sickness.frailty`, twice, for frailty, and the goods of a member lower
its weights by `people.exposure`, 1 for both causes without them:
clothes leave 0.8 of an encounter and, in winter, 0.7 of frailty, and a
spear 0.8 of an encounter, both together 0.64; see
[Bonuses](../game/skills.md#bonuses). Meat lowers the frailty weight by
the [diet](#diet), to 0.85 on meat alone. Death of age begins at 0.15 a year at 17 and doubles
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
| frailty   | 1.2 | 0.63     | 0.34      | 0.19      | 0.11    |
| injury    | 0.5 | 0.75     | 0.88      | 0.94      | 0.97    |

Where adults die at 0.22 a year, as in a hard game, about one child in
five grows up, against one in twenty-five when the weights held for the
whole stage. The reference of lives counts the children who grew up and
those who died each year.

### The order of a day

A day ends in a fixed order: the meal, the sick of raw meat and the
states, the cures of herbs, then age, frailty, injuries, births and
conceptions. The council answers for
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
wound is the event `people-injured`. A member fed on meat heals faster by its [diet](#diet), 1.25 times on
meat alone. A herb cuts the days left of a
light wound to its `treated`, 0.5, once; a severity without it is not
treated. See [Sickness and herbs](../game/skills.md#sickness-and-herbs).
A member hurt on a day is drawn by `injury.per_day` with the bonuses of
its own kit laid over: clothes leave 0.7 of it.

```text
healed a day = (1 + (heal_in_camp - 1) * camped) * heals of the diet
```

___

## Shelter

A band in camp is sheltered: it keeps its weak by the fire. Shelter is
the camp action in any part of the day, the evening and the night
included, not the council's stay. It counts in no decision: the
decision function and the council do not read it.

- An encounter met while the band stands by its camp - it camps, builds
  or gathers on its cell - takes `shelter.encounter`, 0.5, of the share
  of the people it would take. It hurts as many. The camp is there and
  the gatherers work around it; only a band that walks or roams is out
  in the open. A kind that names the actions it strikes in, as a
  drowning or a poisoning, comes to the deed, not to the camp, and is
  not sheltered.
- Frailty at the end of a day is multiplied by `sheltered`.
- Hunger, thirst, age and birth are untouched.

```text
camped    = active parts of the day the band camped / active parts of the day
sheltered = 1 - (1 - shelter.frailty) * camped
```

The active parts are those not named by `camp_parts`: the morning, the
midday and the afternoon. A band that rests all day halves its frailty;
a band that walks all day has none of it.

### The guard

`threat` is what the guard of the band leaves of the threat it meets:
`threat.camp` in the ticks it stands by its camp - it camps, builds or
gathers - and `threat.march` in the ticks it walks or roams, both 1.0. It multiplies the threat of the encounters and the
threat in the safety of wellbeing, after `winter_camp.threat`. Goods
held lower it: sticks lay `threat.camp` times 0.8, clothes both times
0.9 by the members holding them, and the hunters both times 0.8 by the
share of their quota filled; see [Bonuses](../game/skills.md#bonuses). What the band sees of the land,
its unease and its decisions are not changed.

___

## Winter camp

A winter camp is the council's answer `winter-camp`, offered on any day
to a band that knows how to winter and never on land whose threat with
the band's dread and guard reaches `winter_camp.unsafe`, 0.5. It wins
the vote only in its season, the winter and the second half of the
autumn, `before` 10 days; see
[Indirect control](../game/indirect_control.md#the-table-of-votes). The band builds it on the cell
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
| the days a lot ages, a day in the camp counting as half | `winter_camp.spoil`, 0.5 |
| what the people eat and drink, and so the days the stores last | `winter_camp.consumption`, 0.8 |
| what a camp takes off fatigue        | `winter_camp.rest`, 1.5    |
| what staying in it is worth to the others, added | `winter_camp.kept`, 0.2 |

Gathering goes on, and the shelter of a camp holds as it does anywhere.
A lot ages slower only for the days it spends in the camp: a lot dried
in the autumn and kept in the camp through the winter is as old in the
spring as those days make it, not older. Before game 1d862e91 the factor
was laid over the whole age of a lot, so the spring that ended the camp
spoiled the reserve left in one day.

A band that steps into another cell loses the camp, built or not, and a
band that builds on another cell starts anew. The camp stands while the
band stays on it, and its effects above hold in any season; its keep in
the vote and the lower threat the band sees in it count only in its
season, so in the spring the band leaves the land it ate bare over the
winter. The decision to winter ends with the first season that does not
offer a camp, so the spring calls the council.

The band remembers every camp it built, `camps`, and the map marks them.
In the season of the camp the council names the nearest of them as a
place to go. A band bound to winter on a camp of its own does not build:
it puts the camp in order in the evening, a camp part it spends in camp
anyway, and the camp stands from that evening on.

### The reserve for the winter

A band that knows `drying` stocks without work. At the end of every day
of the spring, the summer and the autumn, `drying.seasons`, the forage
left over tomorrow's ration dries by itself into `dried`, a food marked
`reserve`: a unit of forage gives a unit of dried at half the weight,
which feeds `drying.keeps`, 0.7, of a ration, since nobody in the band
is a master of it. Nothing is dried in the winter. There is no keep: all
that is left over piles up, held back only by the carry outside a camp
and by its time to spoil, 4 months. The reserve is eaten after every
other food.

Nothing kept in a built winter camp the band stands on weighs: the
stores and the kits lie in the camp, so the band gathers as much as its
land gives. When the band leaves its camp its members wear their clothes
and carry their weapons, and the litters carry the food and the water.
Of the stores it leaves behind first the spare goods - sticks, stones,
hides and the rest - then fresh food, then the reserve, then water, the
oldest lots first, until a day's ration still fits on the carry; what is
left stays in the camp and is lost to the band. In seed 4 of the lives a
band that carried all its spare goods out of a camp had no room to
gather and starved in a forest. Before game 1d862e91 a band went into the winter with two
days of food; a band that came out of a stocked camp with all its
reserve on its back could carry no water and died of thirst in spring.

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

A band carries food, water and goods, and each resource is an entry of
the section `resources`: a kind, a weight per unit, a time after which
it spoils and, for goods, the uses it wears out by.

| Resource     | Kind    | Unit     | Weight | Spoils after       | Wears out by                                   |
|--------------|---------|----------|--------|--------------------|------------------------------------------------|
| `water`      | `water` | a litre  | 1 kg   | 5 days             | -                                              |
| `forage`     | `food`  | a kilo   | 1 kg   | 3 days             | -                                              |
| `stones`     | `goods` | a stone  | 0.5 kg | -                  | 300 food eaten x quality                       |
| `sticks`     | `goods` | a stick  | 1 kg   | 1 year             | 400 heads a night in camp, 1 an attack in camp |
| `herbs`      | `goods` | a bunch  | 0.1 kg | 2 months           | 1 a cure                                       |
| `cords`      | `goods` | a cord   | 0.1 kg | 6 months           | - (spent in what is made)                      |
| `litters`    | `goods` | a litter | 4 kg   | -                  | 70 days pulled x quality                       |
| `meat`       | `food`  | a kilo   | 1 kg   | 2 days             | -                                              |
| `spears`     | `goods` | a spear  | 1.5 kg | -                  | 80 hunts x quality                             |
| `hides`      | `goods` | a hide   | 2 kg   | 12 months          | - (spent in what is made)                      |
| `clothes`    | `goods` | a suit   | 2 kg   | 12 months          | -                                              |
| `waterskins` | `goods` | a skin   | 0.5 kg | 6 months           | -                                              |

Stores are kept in lots, one per resource and day gathered. The oldest
lot is eaten first, and a lot older than its time is thrown away in the
phase `world` of the first tick of a day. A band holds at most five lots
of water and three of forage, so the state stays small. A lot of goods
with a quality is `[day, amount, quality]`, and serves that share of its
uses; it spoils by its time whatever its quality. A good held and not used does not
wear. The goods spoiled and worn out are told in whole units by the
events `goods-spoiled` and `goods-worn`; the rest of a unit waits in the
band's `spoiled` and `worn`. In a winter camp goods spoil at the pace
food does there.

An adult carries 6 kg, a child a quarter of it and an elder half, and
a member fed on meat more by its [diet](#diet), a tenth on meat alone. A
member who pulls a litter carries more, a man twice and a woman half
again, net of the litter: its 4 kg weigh in the load and are carried
on top, see [Bonuses](../game/skills.md#bonuses). A member holding a
waterskin carries 3 kg of water beside its load, `carry_water_kg`, and
the water of a band whose adults and elders all hold one keeps 1.5 times
as long. A band never gathers
more than it can carry: what does not fit is left on the cell and the
stock is not lowered for it.

The goods a band learns to gather and make - stones, sticks, herbs,
cords, meat and the personal goods of its members - are resources of
the same stores, with wear and quality; see
[Skills](../game/skills.md#goods). The kits of the members weigh in the
load: the free carry is what the members carry less the stores and the
kits.

___

## Gathering

A gathering tick sends the gatherers after every resource the band wants,
each share of them as the need for it weighs:

```text
share of a resource = weights.<need> * need / the sum of them all
taken               = gatherers * share * rate * value(property, its cell)
```

So a band with water for a day and food for two sends most of its
gatherers for water and some for food, and a band with neither sends
them for both. A need of 0 gets nobody. Every share takes its resource
from its own cell - the cell the band stands on, a shore beside it, for
goods any cell beside it at `gathering_beside` of what it gives, the
reach of a winter camp - and the same share of the free carrying weight,
so a band can no longer fill its carry with food and leave no room for
water. Before game b54a7608 a tick was spent on one resource: a band dying
of thirst beside water gathered forage all day, since food weighed more,
and died.

`gatherers` counts the gatherers only; see [Roles](#roles). While the
band stands the hunters hunt instead of gathering; see
[Hunting](../game/skills.md#hunting). What the band
takes is its rate times the property of the cell, as
[Biomes](../biomes/overview.md#properties) defines it.

| Resource | Property | Rate per person per tick |
|----------|----------|--------------------------|
| `forage` | `food`   | 3.0                      |
| `water`  | `water`  | 4.0                      |
| `stones` | `stone`  | 0.5                      |
| `sticks` | `wood`   | 1.0                      |
| `herbs`  | `plants` | 0.2                      |
| `cords`  | `plants` | 0.3                      |

A good is gathered only once the band knows the skill that opens it, and
its need is the share missing of its keep, weighed by
`decisions.weights.goods`, 0.4; a hungry band wants no goods, and a
gathering takes no more than is missing of the keep. See
[Gathering goods](../game/skills.md#gathering-goods).

The cell pays for it. A cell at full stock holds a fixed amount per
property, and the stock falls by what was taken over that amount. The
value already carries the stock, so a cell gives less with every tick and
the band is pushed on.

| Property | A full cell holds |
|----------|-------------------|
| `food`   | 100 units         |
| `water`  | 2000 units        |
| `stone`  | 50 units          |
| `wood`   | 100 units         |
| `plants` | 50 units          |
| `game`   | 60 units          |

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
them. The ration of `forage` is the ration of food: it is eaten of every
resource of the kind `food` held, forage and meat, the oldest lot first
across them. So 15 adults need 15 kg of food and 15 litres of water a day, 30 kg of
the 90 kg they can carry: a band holds three days of supplies at most,
and its food spoils on the third. One gathering tick in a summer forest
brings 40 kg of food, in a winter forest 16, and in the desert no day is
long enough. The cell is what gives out: a forest cell holds 200 kg, a
fortnight for 15 people, and needs a month to grow back.

What is missing is counted per member as a share of its ration; see
[Hunger and thirst](#hunger-and-thirst).

___

## Hunger and thirst

Every member holds a reserve of food and one of water, in days: how long
it lives on without them once it ate and drank in full. A child's grows
with its age from the reserve of a newborn to an adult's at the end of
childhood.

| Stage   | Food              | Water             |
|---------|-------------------|-------------------|
| `child` | 1 at birth, to 2  | 1 at birth, to 2  |
| `adult` | 2                 | 2                 |
| `elder` | 1.5               | 1.5               |

A member keeps the days it went without, `hungry` and `thirsty`. A day
with its full ration sets them to 0; a part of the ration adds what was
missing, a day with nothing adds 1. A member is hungry, or thirsty,
while it went short and a day or less of the reserve is left, and it
dies when nothing is left; the player never dies of it.

```text
left    = reserve(stage, age) - days gone without
hungry  = days gone without > 0 and left <= 1
dies    = left <= 0
```

So an adult that ate in full lives through a day without food, is
hungry the second day and dies at the end of it, on the third; the same
with water. A newborn dies after a single day without.

What a day gives is shared before anyone else's ration is filled: the
members with the least of that reserve left eat first, children first
on a tie, so the ones nearest death are fed and people die one by one,
not the whole band on the same night. A hungry or thirsty member does
not conceive and gathers and walks at `people.weakened`, 0.6.

The band starves while at least one of its members is hungry, and
thirsts while one is thirsty; see [States](#states). Before game
7d5ec243 hunger and thirst were counted for the band as a whole: thirst
began after a single day short and took 15% of the people a day, and a
band that spent two days building a winter camp on a day of water lost
four people the same night, every autumn.

___

## Speed

A band moves one cell per tick over open ground. Each moving tick adds
progress, and the band enters the next cell when the progress reaches 1.

```text
progress = speed * value(passability, target cell)
speed = max(slowest, base - slowdown * population / 10) * efficiency * pace
```

With a base of 1.2 and a slowdown of 0.03 a band of 15 walks at 1.155
and a band of 150 at 0.75; no band is slower than 0.3. Litters lay
`speed.base` times 0.85 by the share of the pullers who pull one, so a
band of 15 whose pullers all pull walks at 0.975. A step along a
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
| `starvation` | a member is hungry                  | nobody hungry conceives, see [Hunger and thirst](#hunger-and-thirst) | no member is hungry |
| `thirst`     | a member is thirsty                 | nobody thirsty conceives        | no member is thirsty       |
| `tiredness`  | fatigue reaches 0.8                 | nobody is born                  | fatigue falls to 0.3       |

The members die of hunger and thirst by their own reserves, not by a
share of the band.

The beginning and the end of a state are events, and so is every death,
with its cause.

___

## What a band knows

A band sees the cells within 2 cells of its own, 25 in all. For each it
knows the biome, the river mark and the current value of every property.

It remembers what it saw for a year, `memory`, as it was when last
seen: a cell that was stripped bare stays bare in its memory until it is
seen again. Older memories are dropped. Before game 1d862e91 a band
forgot what it had not seen for 20 days, so a band that wintered in one
camp knew only the 25 cells around it by the end of the winter.

A band knows what the seasons do to its land. When a season starts, every
remembered cell is expected as the new season makes it: the share of its
stock that the band saw is kept, and the seasonal modifiers of the new
season replace those of the old. A meadow seen full in summer is
remembered as a winter meadow once winter comes, not as a summer one. The
cells whose memory changed go out in `known` of that update. The decision function reads nothing but what
is known, and so does the observation of the seat.

The cells a band knows grow with the land it walks, and so does the
snapshot; `known` and `snapshot` in `tests/runner/lives.json` follow
them.

___

## Parameters

The defaults of the three sections this document fills. Durations and
flows are written as [Parameters](../architecture/parameters.md#writing-values)
asks.

```yaml
resources:
  water: {kind: water, property: water, weight_kg: 1.0, spoils: {days: 5}}
  forage: {kind: food, property: food, weight_kg: 1.0, spoils: {days: 3}}
  meat: {kind: food, weight_kg: 1.0, spoils: {days: 2}, sickens: 0.03}
```

The goods are in
[Skills](../game/skills.md#parameters).

```yaml
units:
  band:
    start:
      population: 15
      stores: {water: 15, forage: 15}
      biomes: [grass, forest, floodplain]
      border: {cell: [forest], beside: [grass], stone: [hills, outcrops, mountain], within: 10}
      stage: adult
      oldest: {years: 12}
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
          dies: {encounter: 3.0, frailty: 1.2, injury: 0.5}
          reserve: {food: 1.0, water: 1.0, grows: true}
        adult:
          until: {years: 17}
          gathers: 1.0
          carries: 1.0
          eats: 1.0
          pace: 1.0
          tires: 1.0
          conceives: true
          votes: true
          dies: {encounter: 1.0, frailty: 0.05, injury: 1.0}
          reserve: {food: 2.0, water: 2.0}
        elder:
          gathers: 0.4
          carries: 0.5
          eats: 0.7
          pace: 0.8
          tires: 1.3
          conceives: false
          votes: true
          dies: {encounter: 2.0, frailty: 0.3, injury: 1.5}
          reserve: {food: 1.5, water: 1.5}
      age: {begins: {years: 17}, per_year: 0.15, doubles: {years: 2}}
      injury:
        per_day: 0.002
        heal_in_camp: 2.0
        severities:
          light: {days: 10, pace: 0.8, gathers: 0.7, treated: 0.5}
          medium: {days: 15, pace: 0.6, gathers: 0.4}
          heavy: {days: 20, pace: 0.4, gathers: 0.2}
        drawn: {light: 0.5, medium: 0.3, heavy: 0.2}
      weakened: {pace: 0.6, gathers: 0.6}
      sickness: {lasts: {days: 5}, pace: 0.7, gathers: 0.5, frailty: 2.0}
      exposure: {encounter: 1.0, frailty: 1.0}
      diet: {meat: meat, keeps: 0.8, full: {frailty: 0.85, heals: 1.25, carries: 1.1}}
      roles:
        gatherer: {gathers: 1.0}
        nanny: {gathers: 0.5, cares: 5}
        hunter:
          gathers: 1.0
          share: 0.2
          needs: spears
          gives:
            - {to: band, path: units.band.threat.camp, times: 0.8}
            - {to: band, path: units.band.threat.march, times: 0.8}
      birth:
        pregnancy: {months: 3}
        pause: {min: {months: 1}, max: {months: 2}}
        conceive_per_day: 0.05
        stores: {months: 3}
        child_survives: 0.5
        mother_dies: 0.05
        midwife: {survives: 0.55, mother: 0.75, herb: {survives: 0.6, mother: 0.5}}
    carry_kg: 6.0
    carry_water_kg: 0.0
    gathering_beside: 0.3
    gathering:
      forage: 3.0
      water: 4.0
      stones: 0.5
      sticks: 1.0
      herbs: 0.2
      cords: 0.3
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
    making:
      per_part: 1.0
      hands: 3
      mastery: {half: 10, floor: 0.6}
    hunting: {meat: 4.0, hides: 0.05}
    states:
      tiredness: {begins: 0.8, ends: 0.3}
    sight: 2
    memory: {years: 1}
    dread: {encounter: 0.3, lasts: {days: 20}}
    unease: {gain: 0.1, fade: 0.2}
    route: {margin: 4, threat: 2.0, hunger: 1.0, thirst: 1.0}
    shelter: {encounter: 0.5, frailty: 0.5}
    threat: {camp: 1.0, march: 1.0}
    drying: {of: forage, into: dried, keeps: 0.7, seasons: [spring, summer, autumn]}
    winter_camp:
      offered: {seasons: [winter], before: {days: 10}}
      unsafe: 0.5
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
    capacity: {food: 100, water: 2000, stone: 50, wood: 100, plants: 50, game: 60}
    recovery: {food: {winter: 0.25}, plants: {winter: 0.25}}
```

`eras.band.recovery` slows the recovery of a stock in a season: food
and plants grow back at a quarter of their pace in winter. `making` is
told in [Making](../game/skills.md#making), `hunting`, `sickness` and
`exposure` in [Hunting](../game/skills.md#hunting) and
[Sickness and herbs](../game/skills.md#sickness-and-herbs). Every number here is a
first guess; the lab of the roadmap is where they are tuned.

___

## Checks

A game does not start from a band that does not add up.

- A resource is of a kind, `food`, `water` or `goods`; it names a
  property of every era that uses it, if it is gathered, and a positive
  weight. Food and water have a time to spoil, goods a time to spoil,
  uses to wear by, or both; no time is zero.
- A biome lists only resources of the section `resources` that are
  gathered, and `gathering` names only those.
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
- The biomes of `start.border` exist, and those of its `cell` are start
  biomes.
- `tiredness.ends` is below `tiredness.begins`, and both lie in 0 to 1.
- Every name of `camp_parts` is one of `time.day_parts`.
- A reserve is above 0, and the last stage does not grow.
- Every season of `winter_camp.offered` and of `drying` is one of
  `time.seasons`, and `winter_camp.build` is not zero.
- `drying.of` and `drying.into` are resources, and `drying.into` is a
  reserve of food.
- A share, a chance and a loss lie between 0 and 1.
- Exactly one role cares for nobody and has no share; a role that needs
  a good names a personal one, and lays its bonuses on the band.
- The resources a hunt brings, `meat` and `hides`, exist.
- `diet.meat` names a resource of the kind `food`.

___

## Open points

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
