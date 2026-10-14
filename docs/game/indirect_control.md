# Indirect control

#game #council #stage2

The player does not command the band. The player is one voice in its
council, and the council meets every morning: the others put their votes
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
[its decision function](decisions.md), and the council of every morning
shows what the band is minded to do. The player answers in one of three
ways: backs one of the options the others voted for, proposes another,
or does not vote, which costs status.

The player is answerable only for what the player changed. Backing what
the band would have done anyway moves nothing; turning the band
elsewhere is judged by what follows; staying silent is a small loss
every day.

___

## Status

Status is a number from 0 to 100 that belongs to the seat. It starts at
50, never passes 100, and at 0 the player is banished.

It does two things. It is the weight of the player's voice in the vote,
and it is the player's life in the game. Nothing but the council changes
it: it does not drift by itself, and what the band suffers on its own is
not the player's fault.

___

## The council of the day

The council meets once a day, at the first tick of the day, the
morning. Nobody calls it, and it cannot be called at another time.

1. **Judgement** - the proposal of the day before, if the player turned
   the band, is judged first; see [The judgement](#the-judgement).
2. **The table** - the others vote, and the votes are shown to the
   player; see [The table of votes](#the-table-of-votes).
3. **The answer** - the council waits for the player; see
   [The player's answer](#the-players-answer).
4. **The decision** - the option with the most votes wins; see
   [The decision](#the-decision).

The band does not act while the council sits: the morning tick is spent
in it, as a camp. In step mode the game waits for the seat as it always
does. In real time the clock stops while the council waits, for at most
`DT_COUNCIL_WAIT_S` seconds of real time, a setting of the server, 30 by
default; a player who has not answered by then did not vote.

___

## The table of votes

The council is everybody but the player, one voice each. They are not
people with names: how their votes lie follows from how good each option
looks to the band.

The options are the proposals the player could make: a move in each of
the eight directions whose cell can be entered, a rest, and a stay to
gather; ten at most. Each gets the score the decision function gives the
first action it would lead to - the move that way, the camp, or the
better of the two gatherings - as it does now for one proposal.

```text
share of an option = its score / the sum of all scores above zero
votes of an option = share * (population - 1), in whole votes
```

An option that scores zero or less gets no votes. Whole votes are given
by the largest remainder: each option takes the whole part of its votes,
and the votes left over go one each to the largest remainders, ties in
the fixed order of the decision function. The table draws no random
number, so a player who knows the band can tell how it will lie.

The option with the most votes of the others is the **leader**: what the
band would do if the player said nothing. When no option scores above
zero the table is empty and there is no leader.

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
| backed the leader      | the leader        | the band decides freely; status does not move |
| turned the band        | the player's option, not the leader | it becomes the band's intent and is judged |
| was outvoted           | another option    | the band decides freely; `outvoted` is paid  |
| abstained              | the leader        | the band decides freely; `abstained` is paid |

"Decides freely" means no intent: the band runs its decision function
tick by tick, which is what the leader stood for. Only an option the
player carried against the leader binds the band.

___

## An intent

An intent holds from the decision to the next council, the rest of the
day and the night.

| Proposal          | The band                                    |
|-------------------|---------------------------------------------|
| `move`            | walks that way and camps when it must       |
| `rest`            | camps and does nothing else                 |
| `stay-and-gather` | stays on its cell, gathers and camps        |

A `move` ends early when the way is closed, as
[Decisions](decisions.md#under-an-intent) tells. No other thing ends an
intent early: a band that agreed to rest goes on resting while its food
runs out.

___

## The judgement

An intent is judged at the next council, before the new table. The game
compares the band at the decision with the band at the judgement.

| Measure | Is                                                            |
|---------|---------------------------------------------------------------|
| `worth` | what the cell the band stands on is worth to it, as [Decisions](decisions.md#what-a-cell-is-worth) counts it, weighed by the needs the band had at the decision |
| `lost`  | the people who died since the decision, of any cause, as a share of the people at the decision |

A `move` gets one of three verdicts, the first that fits.

| Verdict    | When                                                     |
|------------|----------------------------------------------------------|
| `disaster` | `lost` is at least `council.judgement.disaster`, 0.2     |
| `failed`   | anybody died, or the cell reached is worth less than the cell left |
| `worked`   | otherwise                                                |

A move is judged by the land it reached and not by the stores: a band
that walks for a day gathers nothing and eats a day of food, so its
stores always fall, and a measure of stores would fail every move.

- **A rest always worked.** It raises status whatever it cost; the cost
  is the food and water nobody gathered.
- **Staying to gather worked** unless an encounter took people. Then it
  failed, and it was a disaster by the same share as a move.

___

## What moves status

| What happened                       | Status |
|-------------------------------------|--------|
| abstained                           | -2     |
| outvoted                            | -1     |
| backed the leader                   | 0      |
| a move the player carried worked    | +4     |
| a move failed                       | -6     |
| a move ended in disaster            | -20    |
| a rest the player carried           | +2     |
| staying to gather worked            | +3     |
| staying to gather failed            | -6     |
| staying ended in disaster           | -20    |

Silence costs more than losing a vote, so a player who takes part is
never worse off than one who does not. Gains come only from turning the
band, so following the crowd is safe and slow, and leading is the way
up and the way out.

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
| `council-followed`  | `proposal`                               | the player backed the leader  |
| `council-turned`    | `proposal`, `yes`, `all`                 | the player carried an option  |
| `council-outvoted`  | `proposal`, `winner`, `status`           | the player lost the vote      |
| `council-abstained` | `status`                                 | the player did not vote       |
| `proposal-worked`   | `proposal`, `status`                     | the judgement                 |
| `proposal-failed`   | `proposal`, `lost`, `status`             | the judgement                 |
| `proposal-disaster` | `proposal`, `lost`, `status`             | the judgement                 |
| `intent-ended`      | `proposal`                               | the way was closed            |
| `seat-banished`     | none                                     | status reached 0              |

`proposal`, `leader` and `winner` are themselves keys, such as
`proposal-move-east`; `status` is the status after the change. The table
itself is not an event: it is part of the seat while the council sits.

___

## Parameters

```yaml
council:
  part: morning
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
    rest: 2
    stay_worked: 3
    stay_failed: -6
    stay_disaster: -20
```

`part` must be one of `time.day_parts`. `least` must be above 1, so that
the player's voice is never an ordinary one. `DT_COUNCIL_WAIT_S` is a
setting of the server, not of the game: it changes how long a person may
think, never the outcome of a run in step mode.

___

## Examples

A band of 15 in the morning, status 50, so the player speaks with 3.75
voices. The others score staying to gather 0.63, a move east 0.40 and a
rest 0.07; the fourteen votes lie 8.02, 5.09 and 0.89, and by the largest
remainder 8, 5 and 1.

```text
seq 500          council-opened leader proposal-stay-and-gather
                 table: stay-and-gather 8, move-east 5, rest 1
```

The player backs the move east: 5 + 3.75 = 8.75 beats 8. The band walks
east for the day and the move is judged the next morning.

```text
POST /commands   {"id": "c-7", "kind": "vote", "proposal": {"kind": "move", "towards": "east"}}
seq 500          council-turned proposal-move-east, yes 8.75 of 17.75
seq 505          proposal-worked proposal-move-east, status 54
```

The player proposes a move north, which nobody voted for: 3.75 does not
beat 8, and staying to gather wins.

```text
seq 500          council-outvoted proposal-move-north, winner proposal-stay-and-gather, status 49
```

The player backs staying to gather: the leader wins, the band decides
freely and status does not move. The player does not answer in time:
the leader wins and status falls by 2.

```text
seq 500          council-followed proposal-stay-and-gather
seq 500          council-abstained status 48
```

___

## Open points

- **A vote without chance** - the table is a formula. A draw around the
  shares would make the council less of a calculation and the game less
  easy to play by a program.
- **A rest that kills** - a rest the player carried raises status even
  when people starved in it. Whether a disaster during a rest is still a
  disaster is seen in play.
- **The band's own luck** - an encounter within the day of a move counts
  against the player, though no proposal causes a bear.
- **Directions by landmark** - a proposal names a compass point only. "To
  the river" needs the band's map in the command and waits for the
  browser client.
- **A day is short** - a move is judged after one day, where the council
  of the old design gave it three. Whether one day shows a move's worth
  is seen in the lab.
- **The emergency council** - a meeting with another band calls a
  council at once, outside the morning; it is designed with stage 3.
