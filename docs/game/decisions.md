# Decisions

#game #band #decisions #stage2

A band decides for itself in every tick. This document says how: which
needs it has, how it scores what it could do and what breaks a tie. The
same function runs the player's band and, from stage 3, every other one.
Part of the stage 2 design in [the roadmap](../roadmap.md).

- [The idea](#the-idea)
- [Needs](#needs)
- [What a cell is worth](#what-a-cell-is-worth)
- [Scoring the actions](#scoring-the-actions)
- [Choosing](#choosing)
- [Under an intent](#under-an-intent)
- [The reason](#the-reason)
- [Parameters](#parameters)
- [Examples](#examples)
- [Open points](#open-points)

___

## The idea

In the phase `decisions` the band lists what it could do, gives every
option a score and takes the best. The options are a camp, gathering of
each resource the cell gives, and a move and a roam to each of the eight
cells around that can be entered: at most nineteen. The function decides
the parts of the day the band works in; in the parts of
`units.band.camp_parts`, the evening and the night, the band camps
without asking it.

The function reads the band and what the band knows, and nothing else.
It is pure: the same band with the same knowledge decides the same. The
weights it uses are data, and a set of weights is what stage 3 will call
a temperament.

___

## Needs

A need is a number from 0, nothing wanted, to 1, nothing else matters.

| Need      | Is                                                          |
|-----------|-------------------------------------------------------------|
| `hunger`  | the level of the days of food in the stores                 |
| `thirst`  | the level of the days of water in the stores                |

Days of food are the stores over what the people eat in a day. Hunger
and thirst are not a line but levels: the first level, from the top,
whose `days` the stores reach gives the need.

| Level    | Days in the stores | Need |
|----------|--------------------|------|
| `sated`  | 2 or more          | 0.1  |
| `fed`    | 1 to 2             | 0.4  |
| `hungry` | less than 1        | 0.8  |
| starving | the state holds    | 1.0  |

A band that starves or thirsts has the need 1 whatever its stores say.
The levels are data, and so is their number.

Fatigue is no need. Every night rests the band, and fatigue does not
weigh in a decision; it takes from what the band can do instead, its
pace and its gathering, as [the band](../units/band.md#fatigue) says.

The band is **calm** when neither hunger nor thirst presses:

```text
calm = 1 - max(hunger, thirst)
```

A calm band thinks of growth: of land that is safe to raise children on.
A hungry one thinks of food and fears nothing.

___

## What a cell is worth

A cell the band knows has a worth, the answer to "how good would it be
to stand there now".

```text
worth = hunger * food + thirst * water - weights.safety * calm * threat
```

The properties are the values the band remembers, stock and season
included. The worth changes with the needs: to a thirsty band the river
is worth more than the forest, and to a calm band the open grass is
worth more than the forest with wolves in it.

A cell that cannot be entered is worth nothing, and neither is a cell
the band does not know.

___

## Scoring the actions

Every score is a sum of what the action gives, each part weighed by the
need it serves.

| Action          | Score                                                        |
|-----------------|--------------------------------------------------------------|
| `camp`          | 0: what a band does when nothing else is worth it            |
| `gather` forage | `weights.hunger` times hunger, food of the cell and fit      |
| `gather` water  | `weights.thirst` times thirst, water of the cell and fit     |
| `move` to a cell| see below                                                    |
| `roam` to a cell| see below                                                    |

```text
move = weights.move * (pull - worth of the own cell)
roam = roaming.speed * weights.move * (pull - worth of the own cell)
       + roaming.share * (the gatherings of what the band is short of, scored on the cell ahead)
```

- **Fit** is the share of a tick's haul that the free carrying weight
  takes, 1 when all of it fits, so a loaded band does not gather.
- **Pull** of a neighbour is the best worth among the known cells that
  lie closer to it than to the band, each divided by 1 plus its distance
  in cells times `distance`. The neighbour itself is one of them. A
  worth below zero is multiplied instead, so that distance never makes
  bad land look better.

A move scores above zero only when something known is better than the
place the band stands on. A band on good land stays; a band on stripped
land goes.

A roam gets there slower, so it gets a part of the move's gain, and
adds what the band would forage on the way. A fed band in a hurry walks;
a band short of food roams through good land. **A hungry band does not
walk**: when hunger or thirst reaches `roaming.hunger`, the moves are not
among its options and only the roams are.

___

## Choosing

The best score wins. Two rules settle the rest.

- **A tie** goes to the option that comes first in a fixed order: `camp`,
  `gather` forage, `gather` water, then the moves clockwise from the
  north, then the roams the same.
- **A move in progress is kept.** The cell the band is already walking
  towards gets `weights.momentum` added, so a band does not turn back in
  the middle of a forest.

When nothing scores above `idle`, the band has no reason to do anything
in particular. Then it wanders: one of the cells it can enter is drawn
from the game's stream `decisions`, and the band roams that way for a
day, foraging as it goes. This is the only random draw of the function,
and how a band on a bare plain finds better land.

___

## Under an intent

A proposal the council passed is the band's intent. An intent does not
replace the function: it narrows the options and the function chooses
among what is left.

| Intent            | Options left                              |
|-------------------|-------------------------------------------|
| `move` a direction| a move or a roam that way, or a camp      |
| `stay-and-gather` | gathering of any resource, or a camp      |

"That way" is the named direction first. When that cell cannot be
entered, the two directions beside it are taken, the clockwise one
first; when neither can, the intent ends early. Under a `move` intent
the moves and the roams are scored with the pull replaced by a fixed
`weights.intent`, and a roam gets the whole of that gain, not
`roaming.speed` of it: the intent names the way, not the pace. The band
roams wherever the cell ahead feeds it and walks only over bare land.

The band holds an intent to its end, starving or not. That is what makes
a bad proposal bad; see
[Indirect control](indirect_control.md#an-intent).

___

## The reason

Every decision carries its reason: the action, its score, the need that
gave the largest part of it and, for a move, the cell that pulled.

```json
{"action": "move", "towards": "east", "need": "thirst", "score": 0.61, "pull": {"x": 2305, "y": 744}}
```

The reason is part of the band in the snapshot, so the inspector of
stage 4 shows why a band did what it did. It is not an event: a band
decides in every tick, and the event log would hold nothing else.

___

## Parameters

```yaml
units:
  band:
    decisions:
      levels:
        sated: {days: 2, need: 0.1}
        fed: {days: 1, need: 0.4}
        hungry: {days: 0, need: 0.8}
      distance: 0.25
      idle: 0.05
      wander: {days: 1}
      weights:
        hunger: 1.5
        thirst: 1.2
        safety: 2.0
        move: 3.0
        momentum: 0.1
        intent: 0.6
```

`levels` are read from
the most days down; their days must differ, one of them must be 0, and
every need lies between 0 and 1.

___

## Examples

A band of 15 at midday in a summer forest, rested, with a day and a half
of food and two days of water: 52.5 kg of the 90 it can carry. It is fed
and sated: hunger 0.4, thirst 0.1, calm 0.6. A tick of forage
would be 40.5 kg and 37.5 fit, so the fit is 0.93. The band knows only
forest around it.

```text
camp                                       = 0.00
gather forage   1.5 * 0.4  * 0.9 * 0.93    = 0.50
gather water    1.2 * 0.1  * 0.6 * 1.0     = 0.07
-> gather forage
```

The same band with open grass to the east, threat 0.1 against the 0.4 of
the forest. Calm, it weighs the danger of the forest higher than its
food, and it roams there rather than walks: the grass feeds it on the
way.

```text
own forest      0.4 * 0.9 + 0.1 * 0.6  - 2.0 * 0.6 * 0.4 = -0.06
grass east      0.4 * 0.8 + 0.1 * 0.28 - 2.0 * 0.6 * 0.1 =  0.23
pull            0.23 / 1.25                             =  0.18
move east       3.0 * (0.18 + 0.06)                     =  0.73
grass ahead     1.5 * 0.4 * 0.8, no water: two days held =  0.48
roam east       0.75 * 0.73 + 0.5 * 0.48                =  0.79
gather forage                                           =  0.50
-> roam east
```

The same place with less than a day of food: hungry, hunger 0.8, calm
0.2. The danger hardly counts and the forest feeds better than the
grass. A hungry band does not walk, so only the roam is weighed.

```text
own forest      0.8 * 0.9 + 0.1 * 0.6  - 2.0 * 0.2 * 0.4 =  0.62
grass east     (0.8 * 0.8 + 0.1 * 0.28 - 2.0 * 0.2 * 0.1) / 1.25 = 0.50
grass ahead     1.5 * 0.8 * 0.8, no water: two days held =  0.96
roam east       0.75 * 3.0 * (0.50 - 0.62) + 0.5 * 0.96 =  0.22
gather forage   1.5 * 0.8 * 0.9 * 1.0                   =  1.08
-> gather forage
```

A hungry band on a stripped forest cell, food at a stock of 0.1, with a
full forest remembered three cells to the east. It is hungry, so it
roams there, gathering what the stripped cell ahead still gives.

```text
gather forage   1.5 * 0.8 * 0.09 * 1.0                     = 0.11
roam east       pull   (0.8 * 0.9 + 0.06 - 0.16) / 1.75    = 0.35
                own     0.8 * 0.09 + 0.06 - 0.16           = -0.03
                ahead   1.5 * 0.8 * 0.09, no water       = 0.11
                0.75 * 3.0 * (0.35 + 0.03) + 0.5 * 0.11    = 0.91
-> roam east
```

___

## Open points

- **Looking ahead** - the function scores one tick. A band does not
  count that the walk to better land costs a day it has no food for.
- **Stores that spoil** - a band gathers up to its carrying weight even
  when the lot will spoil before it is eaten.
- **Safety** - a calm band leaves dangerous land, a hungry one does not.
  A band that was just struck is not more afraid than before it.
- **Weights per band** - one set of weights serves every band until
  stage 3 names temperaments.
