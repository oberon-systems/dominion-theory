# Indirect control

#game #council #stage2

The player does not command the band. The player is one voice in its
council, and the council meets every evening: the others put their votes
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
[its decision function](decisions.md), and the council of every evening
shows what the band is minded to do tomorrow. The player answers in one of three
ways: backs one of the options the others voted for, proposes another,
or does not vote, which costs status.

The player is answerable for the days the player voted for. On such a
day every death costs status and every birth earns it, whether the
player backed the leader or turned the band; turning the band is judged
besides by what follows. Staying silent is no way out: it costs status
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

___

## The council of the day

The council meets once a day, in the evening, around the fire of the
camp, and decides the next day: the morning, the midday and the
afternoon, when the band works. Nobody calls it, and it cannot be called
at another time.

1. **Judgement** - the proposal of the evening before, if the player
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

The council is everybody but the player, one voice each. They are not
people with names: how their votes lie follows from how good each option
looks to the band.

The options are the proposals the player could make: a move in each of
the eight directions whose cell can be entered and a stay to gather;
nine at most. There is no rest to propose: every night rests the band.
The council decides where the band spends the day,
so each option is scored by the day it leads to, with the needs of
[Decisions](decisions.md#needs):

| Option            | Score                                                       |
|-------------------|-------------------------------------------------------------|
| `stay-and-gather` | `weights.move` times the worth of the own cell              |
| `move` that way   | `weights.move` times the pull that way                      |

```text
stay = weights.move * worth(own)
move = weights.move * pull
```

A band on good land stays; a calm band in a dangerous forest leans to
the open land beside it.
How the band moves - walking or roaming - is its own choice once the
day is decided. A move is scored as a walk even for a hungry band that
may only roam, so the council still weighs every way and not only the
stay.

```text
weight of an option = exp(score / spread)
votes of an option  = weight / the sum of all weights * (population - 1)
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
| **propose** | an option that has no votes    | that option alone          |
| **abstain** | `abstain`, or nothing in time  | nowhere                    |

Backing and proposing are the same command; which one it is follows from
the table. The weight of the voice is the status as a share of
`council.voice.share` of the band, and never less than
`council.voice.least`: the player presses with authority.

```text
voice = max(least, share * population * status / 100)
```

A refused `vote` costs nothing. It is refused for one of four reasons.

| Reason                      | When                                               |
|-----------------------------|----------------------------------------------------|
| `refused-no-council`        | no council sits now                                |
| `refused-already-voted`     | the seat has answered this council                 |
| `refused-no-such-direction` | the cell that way and both cells beside it cannot be entered |
| `refused-seat-banished`     | the player is no longer in the band                |

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
| `move`            | roams or walks that way, as it sees fit     |
| `stay-and-gather` | stays on its cell, gathers and camps        |

A `move` ends early when the way is closed, as
[Decisions](decisions.md#under-an-intent) tells. No other thing ends an
intent early: a band that agreed to stay goes on gathering a stripped
cell.

___

## The judgement

An intent is judged at the next council, before the new table. The game
compares the band at the decision with the band at the judgement.

The player turned the band away from what its people wanted, so the
day is judged against the day the leader promised.

| Measure    | Is                                                         |
|------------|------------------------------------------------------------|
| `expected` | the score of [the day](#the-table-of-votes) of the leader at the decision; of staying when no option had a vote |
| `reached`  | `weights.move` times what the cell the band stands on is worth to it, as [Decisions](decisions.md#what-a-cell-is-worth) counts it, weighed by the needs the band had at the decision |
| `lost`     | the people who died since the decision, of any cause, as a share of the people at the decision |

Every proposal gets one of three verdicts, the first that fits.

| Verdict    | When                                                     |
|------------|----------------------------------------------------------|
| `disaster` | `lost` is at least `council.judgement.disaster`, 0.2     |
| `failed`   | anybody died                                             |
| `failed`   | `reached` is below `expected`                            |
| `worked`   | otherwise                                                |

A move and a stay are judged by the land and not by the stores: a band
that walks for a day gathers nothing and eats a day of food, so its
stores always fall, and a measure of stores would fail every move. Fresh
land beats stripped land, so the measure is not the land the band left
but the day the band would have had: a player who turns a band that did
not care where it went gains about as often as they lose, and one who
turns it from a clear choice mostly loses.

The judgement sits before the night, so the deaths of hunger and thirst
at the end of the judged day are not in `lost`. They are paid as every
death of a day the player voted for is; see
[What moves status](#what-moves-status).

___

## What moves status

| What happened                                           | Status  |
|---------------------------------------------------------|---------|
| abstained                                               | -2      |
| outvoted                                                | -1      |
| backed the leader                                       | 0       |
| a move the player carried worked                        | +4      |
| a move failed                                           | -6      |
| a move ended in disaster                                | -20     |
| staying to gather worked                                | +3      |
| staying to gather failed                                | -6      |
| staying ended in disaster                               | -20     |
| a death on a day the player voted for or kept silent on | -5 each |
| a birth on a day the player voted for                   | +5 each |

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
in it: no table, no wait, no cost, and the band decides freely in every
tick. A band with an empty seat lives exactly as it did before the
council was daily, and the reference of lives does not move for it. A
game is created with the seat taken unless it asks for `seated: false`;
a vote in a game with an empty seat is refused with `refused-no-council`.

___

## Banishment

When status reaches 0 the player is banished. The event `seat-banished`
is reported, the game ends with the outcome `banished`, and every later
command of the seat is refused with `refused-seat-banished`.

The band is not harmed by it. In a game with more seats it would simply
go on without that voice.

___

## Events

Every event is a message key with values, in both catalogues.

| Key                 | Values                                   | When                          |
|---------------------|------------------------------------------|-------------------------------|
| `council-opened`    | `leader`                                 | the table is drawn            |
| `council-agreed`    | `leader`                                 | the leader wins whatever the player says |
| `council-followed`  | `proposal`                               | the player backed the leader  |
| `council-turned`    | `proposal`, `yes`, `all`                 | the player carried an option  |
| `council-outvoted`  | `proposal`, `winner`, `status`           | the player lost the vote      |
| `council-abstained` | `status`                                 | the player did not vote       |
| `proposal-worked`   | `proposal`, `status`                     | the judgement                 |
| `proposal-failed`   | `proposal`, `lost`, `status`             | the judgement                 |
| `proposal-disaster` | `proposal`, `lost`, `status`             | the judgement                 |
| `intent-ended`      | `proposal`                               | the way was closed            |
| `seat-blamed`       | `lost`, `status`                         | people died on a voted or silent day |
| `seat-praised`      | `born`, `status`                         | children were born on a voted day |
| `seat-banished`     | none                                     | status reached 0              |

`proposal`, `leader` and `winner` are themselves keys, such as
`proposal-move-east`; `status` is the status after the change. The table
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
    disaster: 0.2
  status:
    start: 50
    abstained: -2
    outvoted: -1
    move_worked: 4
    move_failed: -6
    move_disaster: -20
    stay_worked: 3
    stay_failed: -6
    stay_disaster: -20
    death: -5
    birth: 5
```

`part` must be one of `time.day_parts`. `spread` must be above 0.
`least` must be above 1, so that
the player's voice is never an ordinary one. `DT_COUNCIL_WAIT_S` is a
setting of the server, not of the game: it changes how long a person may
think, never the outcome of a run in step mode.

___

## Examples

A band of 15 in the evening, status 50, so the player speaks with 3.75
voices. The others score staying to gather 0.5, a move east 0.4 and the
seven other moves 0. With a spread of 0.2 the fourteen votes lie 6.42,
3.89 and 0.53 for each other move; by the largest remainder staying
gets 6, the move east 4, and the first four other moves in the fixed
order 1 each.

```text
seq 500          council-opened leader proposal-stay-and-gather
                 table: stay-and-gather 6, move-north 1, move-north-east 1, move-east 4, ...
```

The player backs the move east: 4 + 3.75 = 7.75 beats 6. The band roams
east the next day and the move is judged the next evening against the
0.5 staying promised: the land reached scores 0.55 by the same measure,
and the move worked.

```text
POST /commands   {"id": "c-7", "kind": "vote", "proposal": {"kind": "move", "towards": "east"}}
seq 500          council-turned proposal-move-east, yes 7.75 of 17.75
seq 505          proposal-worked proposal-move-east, status 54
```

The player backs a move north, which one of the others wants: 1 + 3.75
does not beat 6, and staying to gather wins.

```text
seq 500          council-outvoted proposal-move-north, winner proposal-stay-and-gather, status 49
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
- **The band's own luck** - an encounter within the day of a move counts
  against the player, though no proposal causes a bear.
- **Directions by landmark** - a proposal names a compass point only. "To
  the river" needs the band's map in the command and waits for the
  browser client.
- **A day is short** - a move is judged after one day, where the council
  of the old design gave it three. Whether one day shows a move's worth
  is seen in the lab.
- **The emergency council** - a meeting with another band calls a
  council at once, outside the evening; it is designed with stage 3.
