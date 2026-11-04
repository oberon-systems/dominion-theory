# Indirect control

#game #council #stage2

The player does not command the band. The player is one voice in its
council, and the council meets in the evening when something calls it.
It chooses a plan for the band's next month: to camp, to roam or to
explore, with a direction or a cell. The others put their votes on the
plans the band could follow, the player sees how they lie and answers,
and the band carries the winner out on its own. What follows moves the
player's status. This document gives the rules of the council, the
plan, the vote, the judgement and the status. Part of the stage 2 design
in [the roadmap](../roadmap.md).

- [The idea](#the-idea)
- [Status](#status)
- [The council and its plan](#the-council-and-its-plan)
- [The table of votes](#the-table-of-votes)
- [The player's answer](#the-players-answer)
- [The decision](#the-decision)
- [A plan](#a-plan)
- [The judgement](#the-judgement)
- [What moves status](#what-moves-status)
- [A seat with nobody in it](#a-seat-with-nobody-in-it)
- [Banishment](#banishment)
- [Events](#events)
- [Parameters](#parameters)
- [Examples](#examples)
- [Open points](#open-points)

___

## The idea

There is no headman. The band acts on its own, by
[its decision function](decisions.md), and the council of an evening
an occasion calls shows which plan the band is minded to follow next. The player answers in one of three
ways: backs one of the plans the others voted for, proposes another,
or does not vote, which costs status.

A plan lasts. The council does not decide the next step but the next
month: where the band goes and what it looks for. The band walks, stands
and gathers within it by itself, and calls the council again only when
the month is over, the plan has run its course or something breaks it.
In game 4f160478 a council that decided the next day sat about 25 times
a year, and nearly every sitting ended with the player saying what
everybody said; a council of plans sits 10 to 15 times a year, and each
sitting is a choice.

The player is answerable for the days the player voted for. On such a
day every death of hunger, thirst or an encounter costs status and every
birth earns it, whether the player backed the leader or turned the band;
turning the band is judged besides by how its plan went. Staying silent is no way out: it costs status
at once, and the deaths of the plan are the player's while its births
are not.

___

## Status

Status is a number from 0 to 100 that belongs to the seat. It starts at
50, never passes 100, and at 0 the player is banished.

It does two things. It is the weight of the player's voice in the vote,
and it is the player's life in the game. Nothing but the council and the
days the player voted for change it: it does not drift by itself, and
what the band suffers on a day the player did not vote for is not the
player's fault.

Above the middle, the higher status stands, the harder it moves up and
the easier down: every change is weighed by the height it starts from.

```text
gain = amount * min((100 - status) / 50, 1)
loss = amount * max(status / 50, 1)
```

At 50 and below every amount is paid as the tables give it, so a
player can still fall to banishment. At 90 a plan that worked gives 0.8
and one that failed costs 10.8, so the top is held only by a player who
keeps being right.

___

## The council and its plan

The council meets in the evening, around the fire of the camp, when an
occasion calls it, and chooses the plan the band follows until the next
one. On an evening with no occasion nothing sits: the plan in force
stands, the band stays bound to it, and the days count for the player
as the council that chose it left them.

| Occasion    | Holds when                                                  |
|-------------|-------------------------------------------------------------|
| `first`     | it is the first evening of the game                         |
| `death`     | somebody died of a cause in `council.blamed` since the last council |
| `hunger`    | a member dies tonight of hunger                             |
| `thirst`    | a member dies tonight of thirst                             |
| `encounter` | an encounter struck the band since the last council         |
| `found`     | the band saw a river or a biome it never knew since the last council |
| `spent`     | the plan has run its course: its cell reached, no way further, or a stand on land that no longer feeds the band |
| `term`      | the term of the plan is over                                |
| `season`    | a season began since the last council, unless a camp in its season is in force and the new season still offers it |

The first that holds, in this order, is named in the event. An
occasion is a key, so that a chance encounter can later call a council
of its own, with options of its own: a pack of wolves that is fled,
fought or fed.

Empty stores call nobody: the members live on their reserves while the
band forages on its way, and that is following a plan, not failing it.
Reaching a leg of a plan calls nobody either, and neither does a band
that would rather do something else: the plan holds for its term. In
game 4f160478 a council sat for every arrival, every hungry evening and
every evening the others leaned elsewhere, and dried food of 115 to 200
days lay in the stores of a band that was told hunger pressed.

1. **Judgement** - the plan in force, when the player turned the band to
   it, is judged first; see [The judgement](#the-judgement).
2. **The table** - the others vote, and the votes are shown to the
   player; see [The table of votes](#the-table-of-votes).
3. **The answer** - the council waits for the player; see
   [The player's answer](#the-players-answer).
4. **The decision** - the plan with the most votes wins; see
   [The decision](#the-decision).

**A council that is settled does not sit.** When no plan, one without
votes included, reaches the votes of the leader even with the player's
voice added, nothing the player could say would change the month. Then
the table is drawn but nobody is asked: the event `council-agreed` names
the leader, it becomes the band's plan, nothing is paid for silence, and
the plan belongs to nobody: its deaths cost the player nothing and its
births earn nothing. In game 4f160478 a settled council undid the go the player
had carried the evening before, a predator killed 2 on the land it chose,
and the player paid 15.8 status for a move they had voted against.
The higher the status, the louder the voice and the more often the
council sits.

The band camps while the council sits, as it does every evening and
every night. In step mode the game waits for the seat as it always
does. In real time the clock stops while the council waits, for at most
`DT_COUNCIL_WAIT_S` seconds of real time, a setting of the server, 30 by
default; a player who has not answered by then did not vote.

___

## The table of votes

The council is every member whose stage votes but the player, one voice
each: the adults and the elders; children have no say. They are not
people with names: how their votes lie follows from how good each plan
looks to the band.

| Plan      | Fields                       | The band                                   |
|-----------|------------------------------|--------------------------------------------|
| `camp`    | none                         | stands on its cell, gathers and rests; in the season of the camp it winters there |
| `roam`    | `direction` or `to`          | goes through land it knows or sees towards better land that way, gathering on the way |
| `explore` | `direction` or `to`          | goes into land it does not know that way, to see what lies there |

A `direction` is one of the eight: `n`, `ne`, `e`, `se`, `s`, `sw`,
`w`, `nw`. A plan with a direction looks for land in the sector of 45
degrees around it; a plan with `to` goes to that cell. The cell of a
`roam` is land the band knows; the cell of an `explore` is land it does
not know. The plans are not the actions of the band: under the plan
`roam` the band takes the actions `move`, `roam`, `gather` and `camp` as
[Decisions](decisions.md#under-a-plan) tells.

**`camp` in its season is the winter camp.** In the seasons of the camp,
for a band that knows `wintering`, on land safe for a camp, the plan
`camp` builds a winter camp on the cell, stocks it and winters there;
outside them, or on land too dangerous for a camp, it is the stand of a
month. There is no separate winter camp on the table. In game 4f160478
staying to gather and the winter camp tied 7 to 7 every autumn on the
same cell with the same score, and the player had nothing to choose by.

**A band that knows how winters.** In those seasons, on land safe for a
camp whose cell and reach still feed it a day, the table holds only the
winter camp and a `roam` to a camp the band built before. So it stands in
its camp from the first day of the autumn to the spring and gathers all
around it. Its first winter it does not know how, and goes on as it was.

The table lays one `camp`, one `roam` and one `explore` each way, where
that way leads somewhere: a `roam` where the sector holds known land
better than the own cell, an `explore` where it holds land the band does
not know and a route leads there. Each plan with a direction is aimed at
its first target, the cell its [leg](#a-plan) would go to tonight. Two
plans aimed at the same cell are one option, the first in the fixed
order, and the plan in force is one more, so the table says whether the
band wants to go on.

Every option carries what tells it apart from the others:

| Field       | Holds                                                         |
|-------------|---------------------------------------------------------------|
| `proposal`  | the plan, as the player would name it                         |
| `key`       | its words, such as `proposal-roam-ne` "we roam to the north-east" |
| `to`        | its first target, the cell, or null for a `camp`              |
| `offset`    | that cell from the band, `{"dx", "dy"}`, east and south positive |
| `expect`    | `food`, `water` and `threat` of that cell as the band knows or expects it |
| `votes`     | the votes of the others                                       |
| `score`     | the band's own score of the plan                              |

The council itself carries the days of food and of water the stores
hold, `stores`, so a client shows what each plan risks. In game 4f160478
the table listed "we go through the meadows, near" eight times with the
same food, water and threat and no way to tell where any led.

Each plan is scored by the land it leads to, with the needs of
[Decisions](decisions.md#needs):

| Plan      | Score                                                         |
|-----------|---------------------------------------------------------------|
| `camp`    | `weights.move` times the worth of the own cell; in its season the worth of the camp, below |
| `roam`    | `weights.move` times the pull of its first target             |
| `explore` | `weights.move` times the pull of its first target, the unknown with its [lure](decisions.md#the-lure-of-the-unknown) |

A built camp the band stands in adds `winter_camp.kept`, 0.2, to the
worth of `camp` while its land still feeds the band a day: staying in it
is worth more than standing on its land. Once its cell and its reach
give the gatherers less than a day's food for the band, the camp is
stripped, kept is gone, and the band is drawn on.

```text
camp    = weights.move * (worth(own) + kept)
winter  = weights.move * (worth(own and its reach in winter, food * fed, threat * winter_camp.threat) + kept)
roam    = weights.move * pull(first target)
explore = weights.move * pull(first target) * lure
```

### The council remembers

The band keeps its last decision, `decision` on the band: the plan, the
cell it was taken on and the day it was taken, moved to the day the plan
ended. A council that re-decides the plan in force keeps it, and its term
starts anew.

- **Momentum** - the plan in force gets `weights.momentum` on the table,
  so the band goes on unless something else is clearly better.
- **Going back** - a plan aimed at the cell the last decision left,
  through the decision and `council.memory` days after it ended, loses
  `weights.move * weights.back`. When survival leaves it the only land
  that feeds a starving band, it is the only option, and the band goes
  back.

In game 4f160478 an `arrived` council sent the band back the same evening
to the meadow it had just left, and did so for years.

A winter camp is never built on land too dangerous for it: when the
threat of the band's cell, with the dread of the band, times what its
guard leaves over a day, reaches `winter_camp.unsafe`, 0.5. Mountains,
swamps and shallows are never a camp; a forest is, until encounters that
hurt the band there make it one no more. On such land `camp` is the
stand of a month, in any season.

### Survival before the votes

Before the votes are laid, hunger and thirst take options off the table,
and no score, bonus or distance outweighs them. Three games, the last
1d862e91, starved beside fresher land because a weight always lost to
another.

When the food or the water of the band ran out and its people go short -
starvation or thirst holds - `camp` goes off the table. Of the plans
that lead off its land to land that gives more food and water by the
needs than its own, those of the best weighed worth stay, the nearest of
them: `gives` weighed by distance and visits as
[Decisions](decisions.md#scoring-the-actions) weighs a pull. The threat
is not weighed. A band whose own land gives as much as any of them
camps on it to gather. A band that ranges from a winter camp gathers
its reach already, so it takes only the plans beyond the reach; where it
knows nothing there, the unknown.

```text
gives = hunger * food + thirst * water, of the first target of the plan
```

A band that neither starves nor thirsts and stands in its built winter
camp in the autumn or the winter, `winter_camp.seasons`, keeps to it
while leaving would drop food: every `roam` and `explore` goes off the
table, and the band eats its stores down to what it carries. Spare goods
and water over a day of drinking do not hold it. Land grown too
dangerous for a camp, by `winter_camp.unsafe`, lifts the rule; so do
starvation and thirst. In seed 4 of the lives a band left a camp of 697
food on the first day of the autumn with 36 on its back and starved in
the winter.

The votes are laid over what is left. A plan the player names is
weighed the same way, so a plan the rule took off gets no vote of the
others.

### The worth of a camp

A camp in its season is valued by the winter it is for. Every cell of
the camp and its reach is expected as the winter will make it: of each
property, the share of the full value the band saw there, laid over what
the winter gives the biome, so meadows seen at 0.96 in the autumn are
0.24 in the winter. `fed` is the share of the days of the winter the
camp feeds every eater: day by day the gatherers take the best food of
the camp and its reach, as far as the day needs, and the stock of that
cell falls by what is taken over the units a full cell holds. A camp on
the edge of a meadow that feeds the band ten days of thirty is worth a
third of its food.

The season of the camp is `units.band.winter_camp.offered`, the autumn
and the winter, and the `before` days ahead of them, none. Only then is
`camp` a winter camp, does a built camp add its keep and does the band
see the threat of its camp halved. The band settles in the autumn and
stocks its camp from the reach for two months before the cold. In its
season the old camp nearest the band, one it built before and remembers,
is the cell of one more `roam`; a band bound to camp on such a camp puts
it in order in an evening instead of building it anew. Once the band
ranges, the stand takes the reach as well.

A band on good land camps; a band on stripped land leans to better land
it knows or hopes for. How the band moves - walking or roaming - is its
own choice once the plan is made. A plan is scored as a walk even for a
hungry band that may only roam, so the council still weighs every way
and not only the stand.

### Votes and the leader

```text
weight of an option = exp(score / spread)
votes of an option  = weight / the sum of all weights * (voters - 1)
```

Every option the band could take has its weight, so the votes lean to
the best option without all going to it: the closer two scores, the
more evenly the votes split between them. `council.spread` says how
soft the lean is; a small spread gives nearly everything to the best
option, a large one splits the band evenly. Whole votes are given by the
largest remainder: each option takes the whole part of its votes, and
the votes left over go one each to the largest remainders, ties in the
fixed order: `camp`, then the `roam` from the north clockwise, then the
`explore` the same, then the plan in force and the player's. The table
draws no random number, so a player who knows the band can tell how it
will lie.

The option with the most votes of the others is the **leader**: what the
band would do if the player said nothing; a tie goes to the fixed order.
The table is empty, with no leader, only when the band can take no
option at all.

The table is part of the seat while the council sits, as
[What the API shows](01_bands.md#what-the-api-shows) gives it, so a
client shows the options with their votes before the player answers.

___

## The player's answer

The player answers with the command `vote`, once per council.

| Answer      | The command names                         | The player's voice goes to |
|-------------|-------------------------------------------|----------------------------|
| **back**    | an option that has votes                  | that option                |
| **propose** | a plan of the player's own: a direction or a cell | that plan          |
| **abstain** | `abstain`, or nothing in time             | nowhere                    |

Backing and proposing are the same command; which one it is follows from
the table. A plan the others did not name is weighed by them like their
own: the pull of its first target, made smaller by distance and visits
as a pull is, with the lure for an `explore`. Then the others' votes are
laid again over the table and the plan, so a good plan wins some of them
and a bad one has the player's voice alone. A client that wants no say
at a council backs its leader: that costs nothing, so a player may
follow the majority to the next council where the voice can change the
outcome.

The weight of the voice is the status as a share of
`council.voice.share` of the voters, and never less than
`council.voice.least`: the player presses with authority.

```text
voice = max(least, share * voters * status / 100)
```

A refused `vote` costs nothing. It is refused for one of five reasons.

| Reason                      | When                                               |
|-----------------------------|----------------------------------------------------|
| `refused-no-council`        | no council sits now                                |
| `refused-already-voted`     | the seat has answered this council                 |
| `refused-no-such-place`     | the cell is the band's own, lies outside the window, cannot be entered or has no route; the cell of a `roam` is land the band does not know, or that of an `explore` land it knows; a direction leads nowhere |
| `refused-seat-banished`     | the player is no longer in the band                |
| `refused-not-learned`       | a direction or a cell no option names, without `orientation` |

Without `orientation` the band goes only where the others point, and
explores the way it picks itself; see
[Skills](skills.md#the-council). A `camp` is never refused: without
`wintering`, or on land too dangerous for a camp, it is the stand.

___

## The decision

The votes are counted with the player's voice added to the option the
player named. A point counts with the votes of the options told by the
same words, its way: a vote for a cell to the south is a vote for going
south, the band goes to the cell, and a player on the way of the leader
backs the leader. The option with the most votes wins; a tie goes to the
player's option, and among the others to the fixed order.

| The player             | The winner        | Then                                        |
|------------------------|-------------------|---------------------------------------------|
| backed the leader      | the leader        | the plan is the player's                    |
| turned the band        | the player's option, not the leader | it is judged; the plan is the player's |
| was outvoted           | another option    | nothing is paid; the plan is not the player's |
| abstained              | the leader        | `abstained` is paid; the deaths of the plan are the player's |

Whoever carried it, the winner becomes the band's plan, its intent: the
band follows it, and a band that agreed to camp does not roam away. Only
a plan the player carried against the leader is judged.

___

## A plan

A plan holds from the decision until a council replaces it: for its
term, `council.term`, a month of `time.days_per_month` days, or a
`camp` in its season to the end of that season. The band camps in the
evening and the night whatever the plan.

| Plan      | The band                                                       |
|-----------|----------------------------------------------------------------|
| `camp`    | stays on its cell, gathers and camps while the cell feeds it; in its season builds a winter camp first |
| `roam`    | marches leg by leg that way, over better land where it knows some, or to its cell |
| `explore` | marches leg by leg into unknown land that way, or to its cell  |

**Legs.** A `roam` or an `explore` with a direction does not walk to one
cell. At the decision and at every leg it reaches the band picks its
next target in the sector: for a `roam` the best known cell there,
weighed by distance and visits, when it is better than the own cell, and
otherwise the nearest cell there that a route reaches, so a direction
goes on over land no better than the own; for an `explore` the nearest
cell there the band does not know, that a route reaches. A plan with `to`
has one leg, to its cell. A leg is walked by a route, as
[Decisions](decisions.md#the-route) tells.

**Marching.** A band on a leg walks every working part of the day. It
does not stop to stock up: a roam forages on the way, a share of what the
cell ahead gives, and a fresh cell gives more than one eaten down; with
under 2 days of food or water it roams and forages more, at 0.6 of a walk,
as [Band](../units/band.md#speed) tells. Only tiredness stops it, until it
has rested, and the evening and the night.

**The end.** A plan is spent when its cell is reached, when no route
leads further that way, or, for a `camp` outside its season, when its cell
gives the gatherers less than a day's food and a way leads off it; such a
camp is then left off the table of the council while a way off remains.
The event `plan-ended` tells which, and the council sits that evening
(`spent`). A band on its plan does not turn for another wish, and empty
stores do not turn it either; see
[The council and its plan](#the-council-and-its-plan).

A winter camp is built first, for `winter_camp.build` days of work by
`winter_camp.builders` of the hands, while the others gather what the band
needs; a band in the state of starvation or thirst gathers and camps
first, and builds on once the state ends. See
[Band](../units/band.md#winter-camp) for what it gives. The first season
that no longer offers the camp, the spring, calls the council and the
camp is judged there. The camp stands while the band stands on its cell,
under any plan, until that season: leaving the cell loses it, and so
does the spring.

___

## The judgement

A plan the player turned the band to is judged when it ends: when its
term is over, when it is spent, when something breaks it and the council
sits, or when a council replaces it. A council that keeps the plan in
force judges it and starts its term anew. The game compares the band at
the decision with the band at the judgement, and the verdict says why.

| Measure  | Is                                                             |
|----------|----------------------------------------------------------------|
| `short`  | the days of the plan on which starvation or thirst held        |
| `before` | the days the stores held at the decision, the fewer of food and water |
| `after`  | the same at the judgement                                      |
| `found`  | the cells the band came to know during the plan                |

Every plan gets one of three verdicts, the first that fits.

| Verdict  | When                                                              |
|----------|-------------------------------------------------------------------|
| `failed` | `short` is above `judgement.short`, or `after` fell below `judgement.kept` of `before` and below `judgement.enough` days |
| `worked` | `short` is 0, `after` is at least the fewer of `before` and `judgement.enough`, and a `roam` or an `explore` found at least `judgement.found` cells |
| `even`   | otherwise                                                         |

A plan is judged by how its days went, not by the land it ends on. Until
game 4f160478 a plan was judged by the worth of the cell the band stood
on against the day the leader promised; a winter camp was judged at the
spring by a cell it had grazed bare all winter, and a band that wintered
with no deaths and 72 dried food left cost the player 10.9 status with
no reason given.

**A camp in its season is judged by the winter.** Its term is the
season, so its measures are the winter's: the days of starvation and
thirst through it and the stores left at the spring. A winter eats its
stores by design, so for it `failed` is `short` above `judgement.short`
alone, and `worked` is `short` 0 with `after` at least
`judgement.enough`, no cells asked.

Deaths and births are no part of a verdict. Every death of a cause in
`council.blamed` is paid once, by the player who voted for the plan or
kept silent on it, and every birth on a plan the player voted for is
paid once; see [What moves status](#what-moves-status). Before game
e483e859 a death under a judgement was paid twice: once by itself and
again by a verdict it turned `failed`.

The verdict carries its measures, so a client tells the reason with it.

```text
proposal-failed  proposal-camp, status 80, short 5, before 12, after 3, found 0
                 It went badly: we camp here. Hungry 5 days, stores 12 -> 3 days.
proposal-worked  proposal-explore-ne, status 54, short 0, before 6, after 7, found 9
                 It went well: we explore to the north-east. 9 new cells, stores 6 -> 7 days.
```

___

## What moves status

| What happened                                           | Status  |
|---------------------------------------------------------|---------|
| abstained                                               | -2      |
| outvoted                                                | 0       |
| backed the leader                                       | 0       |
| a `roam` or an `explore` the player carried worked      | +4      |
| a `roam` or an `explore` failed                         | -6      |
| a `roam` or an `explore` came out even                  | 0       |
| a `camp` worked                                         | +3      |
| a `camp` failed                                         | -6      |
| a `camp` came out even                                  | 0       |
| a death on a plan the player voted for or kept silent on | -5 each |
| a birth on a plan the player voted for                  | +5 each |

Only the deaths of the causes in `council.blamed` count: hunger, thirst
and encounters, which follow from where the band went and what it did.
Deaths of age and in childbirth cost nothing, count for no
judgement and call no council.

The player voted for a plan when the player's option won the council
that chose it, backed or carried. A settled council belongs to nobody:
the plan after it costs no deaths and earns no births, whoever spoke at
the council before. A player who kept silent at that council answers
for the deaths of the plan and earns nothing from its births; a player
who was outvoted argued against the plan and answers for neither. A
death or a birth belongs to the day it ends: those at the end of the
day, in the night, belong to the plan in force that day, not to the one
the council of that evening has just chosen.

Silence costs more than losing a vote, and more again on a plan people
die on, so a player who takes part is never worse off than one who does
not. A band that grows raises the player who leads it, a band that dies
takes the player down with it, and turning the band is the way up and
the way out faster.

___

## A seat with nobody in it

A game created with no player - a headless run, a run of the lab, a game
watched by the console client - has an empty seat, and no council sits
in it: no table is shown, nobody waits, nothing is paid. The band still
lives by the same plans: on an occasion the leader of the table binds
it, with no event, as a settled council would.

The life of such a band follows `council.spread`, which lays the votes,
and nothing else of the council but the status the player starts with.
A game is created with the seat taken unless it asks for
`seated: false`; a vote in a game with an empty seat is refused with
`refused-no-council`.

___

## Banishment

When status reaches 0 the player is banished. The event `seat-banished`
is reported, the game ends with the outcome `banished`, and every later
command of the seat is refused with `refused-seat-banished`.

The band is not harmed by it. In a game with more seats it would simply
go on without that voice.

A client says why its game ended: the console screen names banishment
when the status of the seat is 0, and the end of the band when it is
gone. Status is shown with one decimal, so a player at 0.7 does not
read 1.

___

## Events

Every event is a message key with values, in both catalogues.

| Key                 | Values                                   | When                          |
|---------------------|------------------------------------------|-------------------------------|
| `council-opened`    | `leader`, `occasion`                     | the table is drawn            |
| `council-agreed`    | `leader`, `occasion`                     | the leader wins whatever the player says |
| `council-followed`  | `proposal`                               | the player backed the leader  |
| `council-turned`    | `proposal`, `yes`, `all`                 | the player carried an option  |
| `council-outvoted`  | `proposal`, `winner`, `status`           | the player lost the vote      |
| `council-abstained` | `status`                                 | the player did not vote       |
| `proposal-worked`   | `proposal`, `status`, `short`, `before`, `after`, `found` | the judgement |
| `proposal-even`     | `proposal`, `status`, `short`, `before`, `after`, `found` | the judgement |
| `proposal-failed`   | `proposal`, `status`, `short`, `before`, `after`, `found` | the judgement |
| `plan-ended`        | `proposal`, `why`                        | the plan is spent: `reached`, `nothing` or `closed` |
| `seat-blamed`       | `lost`, `status`                         | people died on a voted or silent plan |
| `seat-praised`      | `born`, `status`                         | children were born on a voted plan |
| `seat-banished`     | none                                     | status reached 0              |

`proposal`, `leader` and `winner` are themselves keys, told by what the
band knew at the council: `proposal-camp`, `proposal-winter-camp` for a
`camp` in its season, `proposal-roam-<direction>` and
`proposal-explore-<direction>` for the eight directions, and for a plan
with `to` the direction of its cell from the band. `status` is the
status after the change. The table itself is not an event: it is part of
the seat while the council sits.

___

## Parameters

```yaml
council:
  part: evening
  spread: 0.2
  term: {months: 1}
  voice:
    share: 0.5
    least: 2.0
  judgement:
    short: 2
    kept: 0.5
    enough: 5
    found: 3
  memory: {days: 10}
  status:
    start: 50
    abstained: -2
    outvoted: 0
    roam_worked: 4
    roam_failed: -6
    roam_even: 0
    explore_worked: 4
    explore_failed: -6
    explore_even: 0
    camp_worked: 3
    camp_failed: -6
    camp_even: 0
    death: -5
    birth: 5
  blamed: [hunger, thirst, encounter]
```

`part` must be one of `time.day_parts`, and every cause of `blamed`
one of `hunger`, `thirst`, `encounter`, `age`, `birth`. `spread` must be above 0.
`least` must be above 1, so that
the player's voice is never an ordinary one. `term` is at least a day.
`judgement.short` and `judgement.found` are whole numbers of 0 or more,
`kept` lies in 0 to 1, and `enough` is days. The values of `judgement`
are a first guess, tuned with the lives of the band. `DT_COUNCIL_WAIT_S`
is a setting of the server, not of the game: it changes how long a
person may think, never the outcome of a run in step mode.

___

## Examples

A band of 15 adults stands at 120, 40 in the evening of the first day
of a summer month, status 50, so the player speaks with 3.75 voices. Its
stores hold 6 days of food and 4 of water. The others score `camp` 0.5,
a `roam` to the north-east, aimed at a forest at 122, 38, 0.4, an
`explore` to the east, aimed at the unknown at 124, 40, 0.3, and the
other plans less. By the largest remainder `camp` gets 6, the roam 4 and
the explore 2.

```text
seq 500          council-opened leader proposal-camp, occasion occasion-term
                 table: camp 6, roam-ne +2 -2 forest 4, explore-e +4 +0 unknown 2, ...
                 stores: food 6, water 4
```

The player backs the explore: 2 + 3.75 = 5.75 does not beat 6, and
`camp` wins.

```text
seq 500          council-outvoted proposal-explore-e, winner proposal-camp, status 50
```

At the next council the player backs the roam to the north-east: 4 +
3.75 = 7.75 beats 6. The band walks two days to the forest, foraging on
the way, picks its next leg in the sector, a meadow at 124, 36, and walks
on. On the tenth day the term is over; the
band never went short, its stores hold 7 days and it came to know 6
cells, so the roam worked.

```text
POST /commands   {"id": "c-7", "kind": "vote", "proposal": {"kind": "roam", "direction": "ne"}}
seq 510          council-turned proposal-roam-ne, yes 7.75 of 17.75
seq 540          council-opened leader proposal-camp, occasion occasion-term
seq 540          proposal-worked proposal-roam-ne, status 54, short 0, before 6, after 7, found 6
```

In the autumn the player turns the band to `camp`, which is the winter
camp now: the band builds it, stocks it from its reach and winters
there. At the spring the council sits for the season; the band went
short 2 days, no more than `short` allows, and holds 3 days of food,
below `enough`, 5, so the camp came out even.

```text
seq 2100         proposal-even proposal-winter-camp, status 54, short 2, before 40, after 3, found 0
```

___

## Open points

- **A vote without chance** - the table is a formula. A draw around the
  shares would make the council less of a calculation and the game less
  easy to play by a program.
- **The band's own luck** - an encounter on the way of a plan counts
  against the player, though no plan causes a bear.
- **Against what is a plan judged** - a verdict measures the days of the
  plan against fixed lines, not against what the leader's plan would have
  given. A band in a hard winter fails a plan no other plan would have
  saved.
- **The emergency council** - a meeting with another band calls a
  council at once, outside the evening; it is designed with stage 3.
