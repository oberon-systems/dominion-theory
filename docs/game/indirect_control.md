# Indirect control

#game #council #stage2

The player does not command the band. The player is one voice in its
council, and the council meets in the evening when something calls it:
the others put their votes
on what the band could do, the player sees how they lie and answers, and
what follows moves the player's status. This document gives the rules of
the council, the vote, the judgement and the status. Part of the stage 2
design in [the roadmap](../roadmap.md).

- [The idea](#the-idea)
- [Status](#status)
- [The council of the day](#the-council-of-the-day)
- [The table of votes](#the-table-of-votes)
- [The player's answer](#the-players-answer)
- [The decision](#the-decision)
- [An intent](#an-intent)
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
an occasion calls shows what the band is minded to do next. The player answers in one of three
ways: backs one of the options the others voted for, proposes another,
or does not vote, which costs status.

The player is answerable for the days the player voted for. On such a
day every death of hunger, thirst or an encounter costs status and every
birth earns it, whether the player backed the leader or turned the band;
turning the band is judged besides by what follows. Staying silent is no way out: it costs status
at once, and the deaths of that day are the player's while its births
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
player can still fall to banishment. At 90 a trip that worked gives 0.8
and one that failed costs 10.8, so the top is held only by a player who
keeps being right.

___

## The council of the day

The council meets in the evening, around the fire of the camp, when an
occasion calls it, and decides the days until the next one: the
mornings, the middays and the afternoons, when the band works. On an
evening with no occasion nothing sits: the last decision stands, the
band stays bound to it, and the days count for the player as the last
council left them.

| Occasion   | Holds when                                                   |
|------------|--------------------------------------------------------------|
| `first`    | it is the first evening of the game                          |
| `death`    | somebody died of a cause in `council.blamed` since the last council |
| `arrived`  | the band reached the place its go was bound to               |
| `hunger`   | hunger or thirst reaches `roaming.hunger`                    |
| `closed`   | the way of the decision in force was closed                  |
| `restless` | the decision in force is a stay with fewer than half the votes of the leader: the band wants another thing |
| `season`   | a season began since the last council, unless a winter camp is in force and still offered |
| `river`    | the band saw a river it did not know since the last council  |

The first that holds, in this order, is named in the event. An
occasion is a key, so that a chance encounter can later call a council
of its own, with options of its own: a pack of wolves that is fled,
fought or fed.

1. **Judgement** - the proposal of the council before, if the player
   turned the band, is judged first; see [The judgement](#the-judgement).
2. **The table** - the others vote, and the votes are shown to the
   player; see [The table of votes](#the-table-of-votes).
3. **The answer** - the council waits for the player; see
   [The player's answer](#the-players-answer).
4. **The decision** - the option with the most votes wins; see
   [The decision](#the-decision).

**A council that is settled does not sit.** When no option, one without
votes included, reaches the votes of the leader even with the player's
voice added, nothing the player could say would change the day. Then the
table is drawn but nobody is asked: the event `council-agreed` names the
leader, it becomes the band's intent, nothing is paid for silence, and the
day counts as one the player voted for, its deaths and births included.
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
people with names: how their votes lie follows from how good each option
looks to the band.

The options are a stay to gather, a winter camp while one is offered,
and a go to a place. The band names
one place each way, the land its [pull](decisions.md#scoring-the-actions)
finds there: the best cell it knows nearer that way, or the land it does
not know `decisions.horizon` cells past its sight. Two ways that lead to
the same cell are one option, and a go already in force is one more, so
the table says whether the band wants to go on.

There is no rest to propose: every night rests the band, and a tired
band rests on its way. Each option is scored by the day it leads to,
with the needs of [Decisions](decisions.md#needs):

| Option            | Score                                                       |
|-------------------|-------------------------------------------------------------|
| `stay-and-gather` | `weights.move` times the worth of the own cell              |
| `winter-camp`     | the same with the reach of the camp as the winter will make it, its food by the share of the winter it feeds the band, under the threat a built camp leaves |
| `go` to a place   | `weights.move` times the pull that way                      |

A built camp the band stands in adds `winter_camp.kept`, 0.2, to the
worth of both while its land still feeds the band a day: staying in it
is worth more than standing on its land. Once its cell and its reach
give the gatherers less than a day's food for the band, the camp is
stripped, kept is gone, and a council of hunger calls the band on.

```text
stay   = weights.move * (worth(own) + kept)
winter = weights.move * (worth(own and its reach in winter, food * fed, threat * winter_camp.threat) + kept)
go     = weights.move * pull
```

A winter camp is never offered on land too dangerous for it: when the
threat of the band's cell, with the dread of the band, times what its
guard leaves over a day, reaches `winter_camp.unsafe`, 0.5. Mountains,
swamps and shallows are never a camp; a forest is, until encounters that
hurt the band there make it one no more. A player who names a camp there
is refused with `refused-unsafe-land`.

### Survival before the votes

Before the votes are laid, hunger and thirst take options off the table,
and no score, bonus or distance outweighs them. Three games, the last
1d862e91, starved beside fresher land because a weight always lost to
another.

When the food or the water of the band ran out and its people go short -
starvation or thirst holds - staying and the winter camp go off the
table. Of the ways off
its land, those to the land that gives the most food and water by the
needs stay, the nearest of them; the threat is not weighed. A band whose
own land gives as much as any of them stays on it to gather. A band that
ranges from a winter camp gathers its reach already, so it takes only
the ways beyond the reach; where it knows nothing there, the unknown.

```text
gives = hunger * food + thirst * water, of the land of the option
```

A band that neither starves nor thirsts and stands in its built winter
camp in the autumn or the winter, `winter_camp.seasons`, keeps to it
while leaving would drop food: every go goes off the table, and the band
eats its stores down to what it carries. Spare goods and water over a
day of drinking do not hold it. Land grown too dangerous for a camp, by
`winter_camp.unsafe`, lifts the rule; so do starvation and thirst. In
seed 4 of the lives a band left a camp of 697 food on the first day of
the autumn with 36 on its back and starved in the winter.

The votes are laid over what is left. A place the player names is
weighed the same way, so a place the rule took off gets no vote of the
others.

A camp is valued by the winter it is for. Every cell of the camp and its
reach is expected as the winter will make it: of each property, the
share of the full value the band saw there, laid over what the winter
gives the biome, so meadows seen at 0.96 in the autumn are 0.24 in the
winter. `fed` is the share of the days of the winter the camp feeds
every eater: day by day the gatherers take the best food of the camp and
its reach, as far as the day needs, and the stock of that cell falls by
what is taken over the units a full cell holds. A camp on the edge of a
meadow that feeds the band ten days of thirty is worth a third of its
food.

A winter camp is offered on any day to a band that knows the skill
`wintering`: from its second winter on. It wins only in its season, the
seasons of `units.band.winter_camp.offered`, the autumn and the winter,
and the `before` days ahead of them, none: only then does a built camp
add its keep to staying and does the band see the threat of its camp
halved. The band settles in the autumn and stocks its camp from the
reach for two months before the cold. Out of its season the camp
is scored by the winter its reach would feed, which loses to the land
of the summer. In its season the old camp nearest the band, one it built
before and remembers, is named as a place to go; a band bound to winter
on such a camp puts it in order in an evening instead of building it
anew. The camp is worth the best
food and water within its reach, so the others want to leave only once
the cells around are stripped too. Its other effects - less eaten,
slower spoiling, a deeper rest - are no part of the worth of a cell, so
where the reach gives no more than the own cell, on safe land it ties
with the stay and the stay, first in the fixed order, leads. Once the
band ranges, the stay takes the reach as well.

A band on good land stays; a band on stripped land leans to better land
it knows or hopes for. How the band moves - walking or roaming - is its
own choice once the decision is made. A go is scored as a walk even for
a hungry band that may only roam, so the council still weighs every way
and not only the stay.

Every option of the table carries its words, `key`. A go is told by the
land of its target as the band knows it: `proposal-go-forest` is "we go
into the forest", `proposal-go-through-forest` is "we go on through the
forest" when the band stands in a forest too, and `proposal-go-unknown`
is "we go into land we do not know".

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
fixed order of the decision function. The table draws no random number,
so a player who knows the band can tell how it will lie.

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

| Answer      | The command names              | The player's voice goes to |
|-------------|--------------------------------|----------------------------|
| **back**    | an option that has votes       | that option                |
| **propose** | a place of the player's own    | that place                 |
| **abstain** | `abstain`, or nothing in time  | nowhere                    |

Backing and proposing are the same command; which one it is follows from
the table. A place the others did not name is weighed by them like their
own: the worth of the place, or what the band expects of land it does
not know, made smaller by the length of its route as a pull is. Then
the others' votes are laid again over the table and the place, so a good
place wins some of them and a bad one has the player's voice alone.

The weight of the voice is the status as a share of
`council.voice.share` of the voters, and never less than
`council.voice.least`: the player presses with authority.

```text
voice = max(least, share * voters * status / 100)
```

A refused `vote` costs nothing. It is refused for one of six reasons.

| Reason                      | When                                               |
|-----------------------------|----------------------------------------------------|
| `refused-no-council`        | no council sits now                                |
| `refused-already-voted`     | the seat has answered this council                 |
| `refused-no-such-place`     | the place is the band's own, lies outside the window, cannot be entered, or no route leads there |
| `refused-seat-banished`     | the player is no longer in the band                |
| `refused-not-learned`       | the band has not learned what the answer asks: a place no option names without `orientation`, a winter camp without `wintering` |
| `refused-unsafe-land`       | a winter camp is named on land too dangerous for it, see [The table of votes](#the-table-of-votes) |

Two skills gate the answer, as [Skills](skills.md#the-council) tells: a
band that has not learned `orientation` is sent only where the others
point, and one that has not lived through a winter is offered no winter
camp, by the council or by its own decision.

___

## The decision

The votes are counted with the player's voice added to the option the
player named. The option with the most votes wins; a tie goes to the
player's option, and among the others to the fixed order.

| The player             | The winner        | Then                                        |
|------------------------|-------------------|---------------------------------------------|
| backed the leader      | the leader        | the day is the player's                     |
| turned the band        | the player's option, not the leader | it is judged; the day is the player's |
| was outvoted           | another option    | `outvoted` is paid                          |
| abstained              | the leader        | `abstained` is paid; the deaths of the day are the player's |

Whoever carried it, the winner becomes the band's intent: the council
decides where the band spends the day, and a band that agreed to stay
does not roam away. Only an option the player carried against the
leader is judged.

___

## An intent

An intent holds from the decision to the next council: the night and
the working day after it. The band camps in the evening and the night
whatever the intent.

| Proposal          | The band                                    |
|-------------------|---------------------------------------------|
| `go`              | follows its route to the place, walking, roaming or gathering as it sees fit |
| `stay-and-gather` | stays on its cell, gathers and camps        |
| `winter-camp`     | builds a winter camp on its cell, then gathers and camps there |

A tired band camps whatever its intent, until its tiredness ends. A go
holds until the band stands on its place, which ends it and calls the
council that evening (`arrived`), or until no route is left (`closed`),
as [Decisions](decisions.md#under-an-intent) tells. A band on its way
does not turn for another wish: `restless` never holds for a go. A band
that agreed to stay goes on gathering a stripped cell until hunger calls
the council.

A winter camp is built first, for `winter_camp.build` days of work
without gathering; a band in the state of starvation or thirst gathers
and camps as under a stay, and builds on once the state ends.
See [Band](../units/band.md#winter-camp) for what it gives. Like a go it is never `restless`, and the season it was built in
does not end it: the first season that no longer offers it, the spring,
calls the council and the camp is judged there, as a stay is. The camp
stands while the band stands on its cell, under any intent, until that
season: leaving the cell loses it, and so does the spring.

___

## The judgement

An intent is judged at the next council, before the new table: for a go,
mostly the council its arrival calls. The game
compares the band at the decision with the band at the judgement.

The player turned the band away from what its people wanted, so the
day is judged against the day the leader promised.

| Measure    | Is                                                         |
|------------|------------------------------------------------------------|
| `expected` | the score of [the day](#the-table-of-votes) of the leader at the decision; of staying when no option had a vote |
| `reached`  | `weights.move` times what the cell the band stands on is worth to it, as [Decisions](decisions.md#what-a-cell-is-worth) counts it, weighed by the needs and the unease the band had at the decision |
| `before`   | `reached` of the cell the band stood on at the decision    |

Every proposal gets one of three verdicts, the first that fits.

| Verdict    | When                                                     |
|------------|----------------------------------------------------------|
| `worked`   | `reached` is at least `expected`                         |
| `even`     | `reached` is at least `before` less `council.judgement.slack`, 0.1 |
| `failed`   | otherwise                                                |

A go and a stay are judged by the land and not by the stores: a band
that walks gathers little and eats all the same, so its stores fall,
and a measure of stores would fail every go. Fresh
land beats stripped land, so the measure is not the land the band left
but the day the band would have had: a player who turns a band that did
not care where it went gains about as often as they lose, and one who
turns it from a clear choice mostly loses.

A turn that reached land no worse than the band left is `even` and
moves no status. In an even forest a day of walking reaches
land like the land left: before the verdict `even`, such a turn failed,
and a player who tried to lead the band out of danger lost status for
it while nobody died.

Deaths are no part of a verdict. Every death of a cause in
`council.blamed` is paid once, by the player who voted for the day or
kept silent on it, whether the player backed the leader or carried a
turn; see [What moves status](#what-moves-status). Before game e483e859
a death under a judgement was paid twice: once by itself and again by a
verdict it turned `failed` or `disaster`.

___

## What moves status

| What happened                                           | Status  |
|---------------------------------------------------------|---------|
| abstained                                               | -2      |
| outvoted                                                | -1      |
| backed the leader                                       | 0       |
| a go the player carried worked                          | +4      |
| a go failed                                             | -6      |
| a go came out even                                      | 0       |
| staying to gather worked                                | +3      |
| staying to gather failed                                | -6      |
| staying came out even                                   | 0       |
| a winter camp worked                                    | +3      |
| a winter camp failed                                    | -6      |
| a winter camp came out even                             | 0       |
| a death on a day the player voted for or kept silent on | -5 each |
| a birth on a day the player voted for                   | +5 each |

Only the deaths of the causes in `council.blamed` count: hunger, thirst
and encounters, which follow from where the band went and what it did.
Deaths of age, of frailty and in childbirth cost nothing, count for no
judgement and call no council.

The player voted for a day when the player's option won the evening
council before it, backed or carried. A player who kept silent at that
council answers for the deaths of the day and earns nothing from its
births; a player who was outvoted argued against the day and answers
for neither. A death or a birth belongs to the day it
ends: those at the end of the day, in the night, belong to the council
of the evening before that day, not to the one that has just sat.

Silence costs more than losing a vote, and more again on a day people
die, so a player who takes part is never worse off than one who does
not. A band that grows raises the
player who leads it, a band that dies takes the player down with it,
and turning the band is the way up and the way out faster.

___

## A seat with nobody in it

A game created with no player - a headless run, a run of the lab, a game
watched by the console client - has an empty seat, and no council sits
in it: no table is shown, nobody waits, nothing is paid. The band still
lives by the same decisions: on an occasion the leader of the table
binds it, with no event, as a settled council would.

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
| `proposal-worked`   | `proposal`, `status`                     | the judgement                 |
| `proposal-even`     | `proposal`, `status`                     | the judgement                 |
| `proposal-failed`   | `proposal`, `status`                     | the judgement                 |
| `intent-ended`      | `proposal`                               | the way was closed            |
| `intent-arrived`    | none                                     | the band reached its place    |
| `seat-blamed`       | `lost`, `status`                         | people died on a voted or silent day |
| `seat-praised`      | `born`, `status`                         | children were born on a voted day |
| `seat-banished`     | none                                     | status reached 0              |

`proposal`, `leader` and `winner` are themselves keys, such as
`proposal-go-forest`, told by what the band knew at the council;
`status` is the status after the change. The table
itself is not an event: it is part of the seat while the council sits.

___

## Parameters

```yaml
council:
  part: evening
  spread: 0.2
  voice:
    share: 0.5
    least: 2.0
  judgement:
    slack: 0.1
  status:
    start: 50
    abstained: -2
    outvoted: -1
    go_worked: 4
    go_failed: -6
    go_even: 0
    stay_worked: 3
    stay_failed: -6
    stay_even: 0
    camp_worked: 3
    camp_failed: -6
    camp_even: 0
    death: -5
    birth: 5
  blamed: [hunger, thirst, encounter]
```

`part` must be one of `time.day_parts`, and every cause of `blamed`
one of `hunger`, `thirst`, `encounter`, `age`, `frailty`, `birth`. `spread` must be above 0.
`least` must be above 1, so that
the player's voice is never an ordinary one. `DT_COUNCIL_WAIT_S` is a
setting of the server, not of the game: it changes how long a person may
think, never the outcome of a run in step mode.

___

## Examples

A band of 15 adults stands at 120, 40 in the evening, status 50, so the
player speaks with 3.75 voices. The others score staying to gather 0.5,
a go to 123, 40, the best land east, 0.4, and the seven other goes 0.
With a spread of 0.2 the fourteen votes lie 6.42, 3.89 and 0.53 for each
other go; by the largest remainder staying gets 6, the go east 4, and
the first four other goes in the fixed order 1 each.

```text
seq 500          council-opened leader proposal-stay-and-gather, occasion occasion-hunger
                 table: stay-and-gather 6, go-through-grass 1, go-grass 1, go-forest 4, ...
```

The player backs the go east: 4 + 3.75 = 7.75 beats 6. The band lays its
route from the next morning, walks it and arrives on the second day; its
arrival calls the council, which judges the go against the 0.5 staying
promised: the land reached scores 0.55 by the same measure, and the go
worked.

```text
POST /commands   {"id": "c-7", "kind": "vote", "proposal": {"kind": "go", "to": {"x": 123, "y": 40}}}
seq 500          council-turned proposal-go-forest, yes 7.75 of 17.75
seq 508          intent-arrived
seq 508          proposal-worked proposal-go-forest, status 54
```

The player backs the go north, which one of the others wants: 1 + 3.75
does not beat 6, and staying to gather wins.

```text
seq 500          council-outvoted proposal-go-through-grass, winner proposal-stay-and-gather, status 49
```

The player backs staying to gather: the leader wins, the band stays and
gathers, and the next day is the player's. The player does not answer in
time: the leader wins, status falls by 2, and the deaths of the next
day are still the player's.

```text
seq 500          council-followed proposal-stay-and-gather
seq 500          council-abstained status 48
```

___

## Open points

- **A vote without chance** - the table is a formula. A draw around the
  shares would make the council less of a calculation and the game less
  easy to play by a program.
- **The band's own luck** - an encounter on the way of a go counts
  against the player, though no proposal causes a bear.
- **The way and the end** - a go is judged by the land it reaches, not
  by the days on the way: a long trip through a forest is paid in steps
  and encounters only.
- **The emergency council** - a meeting with another band calls a
  council at once, outside the evening; it is designed with stage 3.
