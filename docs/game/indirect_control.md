# Indirect control

#game #council #stage2

The player does not command the band. The player is one voice in its
council: a proposal is made, the council votes, and what follows moves
the player's status. This document gives the rules of the council, the
vote, the judgement and the status. Part of the stage 2 design in
[the roadmap](../roadmap.md).

- [The idea](#the-idea)
- [Status](#status)
- [Calling a council](#calling-a-council)
- [The vote](#the-vote)
- [An intent](#an-intent)
- [The judgement](#the-judgement)
- [What moves status](#what-moves-status)
- [Banishment](#banishment)
- [Events](#events)
- [Parameters](#parameters)
- [Examples](#examples)
- [Open points](#open-points)

___

## The idea

There is no headman. The band acts on its own, by
[its decision function](decisions.md), and a player who says nothing
loses nothing. The player speaks by calling a council and proposing one
of three things: to go in a direction, to rest, or to stay and gather.

Status moves only with what the player proposed. A proposal that the
band follows and that ends well raises it; one that ends in hunger or
loss lowers it; one the council votes down costs a little.

___

## Status

Status is a number from 0 to 100 that belongs to the seat. It starts at
50, never passes 100, and at 0 the player is banished.

It does two things. It is the weight of the player's voice in the vote,
and it is the player's life in the game. Nothing but the outcome of a
proposal changes it: it does not drift by itself, and what the band
suffers on its own is not the player's fault.

___

## Calling a council

The command is `call-council` with a proposal, as
[Commands](../api/commands.md#the-commands) shows. The engine refuses it
for one of four reasons.

| Reason                      | When                                               |
|-----------------------------|----------------------------------------------------|
| `refused-council-too-soon`  | fewer than `council.min_gap` since the last council |
| `refused-proposal-pending`  | the last proposal that passed is not judged yet    |
| `refused-no-such-direction` | the cell that way and both cells beside it cannot be entered |
| `refused-seat-banished`     | the player is no longer in the band                |

The gap is two days and counts from the call, whether the council passed
the proposal or not. A refused command costs nothing and starts no gap.

A direction is one of the eight compass points. The player reads them as
a nomad would say them - the sunrise, the star that does not move - and
those words are in the catalogues, not in the command.

___

## The vote

The council is everybody but the player, one voice each. They are not
people with names: how many of them say yes follows from how good the
proposal looks to the band.

```text
agreement = score of the proposal / score of the band's own best choice
yes       = agreement * (population - 1) + voice
all       = (population - 1) + voice
passes when yes > all / 2
```

- **The score of the proposal** is what the decision function gives the
  first action the proposal would lead to: the move that way, the camp,
  or the better of the two gatherings. Agreement is held between 0 and 1.
- **The player's voice always weighs more than one.** It is the status
  as a share of `council.voice.share` of the band, and never less than
  `council.voice.least`: the player presses with authority.

```text
voice = max(least, share * population * status / 100)
```

With a share of 0.5 a player of status 50 in a band of 15 speaks with
3.75 voices and needs the agreement of 0.37 of the others; at status 100
it is 7.5 voices and 0.23. A proposal the band would have chosen itself
always passes.

The vote draws no random number. A player who knows the band's needs can
tell how a proposal will fare, and so can a program.

___

## An intent

A proposal that passes becomes the band's intent from the next phase on.
The band holds it for a set time and then decides freely again.

| Proposal          | Holds for | The band                                    |
|-------------------|-----------|---------------------------------------------|
| `move`            | 1 day     | walks that way and camps when it must       |
| `rest`            | 2 days    | camps and does nothing else                 |
| `stay-and-gather` | 2 days    | stays on its cell, gathers and camps        |

A `move` ends early when the way is closed, as
[Decisions](decisions.md#under-an-intent) tells. No other thing ends an
intent early: a band that agreed to rest goes on resting while its food
runs out.

___

## The judgement

A proposal that passed is judged when its window closes: three days
after the call for a `move`, at the end of the intent for the other two.
The game compares the band at the call with the band at the close.

| Measure  | Is                                                            |
|----------|---------------------------------------------------------------|
| `supply` | the lesser of the days of food and the days of water in the stores, held at 2 |
| `lost`   | the people who died within the window, of any cause, as a share of the people at the call |

A `move` gets one of three verdicts, the first that fits.

| Verdict    | When                                                     |
|------------|----------------------------------------------------------|
| `disaster` | `lost` is at least `council.judgement.disaster`, 0.2     |
| `failed`   | anybody died, or `supply` fell by more than `tolerance`, a quarter of a day |
| `worked`   | otherwise                                                |

The other two proposals follow the decisions of the roadmap.

- **A rest always worked.** It raises status whatever it cost; the cost
  is the food and water nobody gathered.
- **Staying to gather worked** unless an encounter took people within
  the window. Then it failed, and it was a disaster by the same share
  as a move.

___

## What moves status

| What happened                 | Status |
|-------------------------------|--------|
| the council voted it down     | -2     |
| a move worked                 | +4     |
| a move failed                 | -6     |
| a move ended in disaster      | -20    |
| a rest                        | +2     |
| staying to gather worked      | +3     |
| staying to gather failed      | -6     |
| staying ended in disaster     | -20    |

Loss weighs more than gain on purpose: a player who proposes at random
is banished, and one who proposes rarely and well climbs slowly. A rest
is the safe way up and the slow one, and it eats the stores.

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

| Key                 | Values                                   | When                         |
|---------------------|------------------------------------------|------------------------------|
| `council-accepted`  | `proposal`, `yes`, `all`                 | the vote passed              |
| `council-declined`  | `proposal`, `yes`, `all`, `status`       | the vote went against        |
| `proposal-worked`   | `proposal`, `status`                     | the judgement                |
| `proposal-failed`   | `proposal`, `lost`, `status`             | the judgement                |
| `proposal-disaster` | `proposal`, `lost`, `status`             | the judgement                |
| `intent-ended`      | `proposal`                               | the way was closed           |
| `seat-banished`     | none                                     | status reached 0             |

`proposal` is itself a key, such as `proposal-move-east`; `status` is
the status after the change. A council that is voted down is not a
refused command: the command was accepted and carried out, and the event
`command-accepted` comes before `council-declined`.

___

## Parameters

```yaml
council:
  min_gap: {days: 2}
  voice:
    share: 0.5
    least: 2.0
  intent:
    move: {days: 1}
    rest: {days: 2}
    stay_and_gather: {days: 2}
  judgement:
    move_after: {days: 3}
    supply_cap: {days: 2}
    tolerance: 0.25
    disaster: 0.2
  status:
    start: 50
    declined: -2
    move_worked: 4
    move_failed: -6
    move_disaster: -20
    rest: 2
    stay_worked: 3
    stay_failed: -6
    stay_disaster: -20
```

`least` must be above 1, so that the player's voice is never an ordinary
one. `move_after` is not shorter than `intent.move`.

___

## Examples

A proposal that passes and works, in step mode. The band of 15 stands on
a stripped cell and remembers a forest to the east; the player has
status 50.

```text
POST /commands   {"id": "c-7", "kind": "call-council", "proposal": {"kind": "move", "towards": "east"}}
seq 412          command-accepted c-7
                 council-accepted proposal-move-east, yes 17.75 of 17.75
seq 413..417     the band walks east and camps at night
seq 427          proposal-worked proposal-move-east, status 54
```

A proposal the council votes down: to walk north, away from the river,
with a day of water left. The band's best choice scores 0.6 and the move
north 0.1, so agreement is 0.17.

```text
yes = 0.17 * 14 + 3.75 = 6.1
all = 14 + 3.75        = 17.75
6.1 is not above 8.875
seq 430          command-accepted c-8
                 council-declined proposal-move-north, yes 6.1 of 17.75, status 48
```

A rest proposed with a day of food in the stores. It passes at night,
when the band wants to camp anyway, and holds for two days.

```text
day 1            the band camps; the food is eaten
day 2            the band camps; the day is short of food
seq 452          proposal-worked proposal-rest, status 50
day 3            the band gathers; one more short day would start starvation
```

___

## Open points

- **A vote without chance** - the council is a formula. A draw around the
  agreement would make the vote less of a calculation and the game less
  easy to play by a program.
- **A rest that kills** - a rest raises status even when people starved
  in it. The roadmap says always; whether a disaster during a rest is
  still a disaster is seen in play.
- **The band's own luck** - an encounter within the window of a move
  counts against the player, though no proposal causes a bear.
- **Directions by landmark** - a proposal names a compass point only. "To
  the river" needs the band's map in the command and waits for the
  browser client.
- **Status that fades** - a player who stays silent keeps the status for
  ever. A slow drift towards the middle would ask for a voice now and
  then.
