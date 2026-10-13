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
each resource the cell gives, and a move to each of the eight cells
around that can be entered: at most eleven.

The function reads the band and what the band knows, and nothing else.
It is pure: the same band with the same knowledge decides the same. The
weights it uses are data, and a set of weights is what stage 3 will call
a temperament.

___

## Needs

A need is a number from 0, nothing wanted, to 1, nothing else matters.

| Need      | Is                                                          |
|-----------|-------------------------------------------------------------|
| `hunger`  | 1 minus the days of food in the stores over `comfort`       |
| `thirst`  | 1 minus the days of water in the stores over `comfort`      |
| `rest`    | the fatigue, plus `night` in the evening and at night       |

Each is held between 0 and 1. Days of food are the stores over what the
people eat in a day; `comfort` is two days, all that a band can carry.
A state doubles its need before the hold: a starving band is hungrier
than its stores alone say.

___

## What a cell is worth

A cell the band knows has a worth, the answer to "how good would it be
to stand there now".

```text
worth = hunger * food + thirst * water - weights.safety * threat
```

The properties are the values the band remembers, stock and season
included. The worth changes with the needs: to a thirsty band the river
is worth more than the forest.

A cell that cannot be entered is worth nothing, and neither is a cell
the band does not know.

___

## Scoring the actions

Every score is a sum of what the action gives, each part weighed by the
need it serves.

| Action          | Score                                                        |
|-----------------|--------------------------------------------------------------|
| `camp`          | `weights.rest` times rest                                    |
| `gather` forage | `weights.hunger` times hunger, food of the cell and room     |
| `gather` water  | `weights.thirst` times thirst, water of the cell and room    |
| `move` to a cell| see below                                                    |

```text
move = weights.move * (pull - worth of the own cell) - weights.rest * rest * effort
```

- **Room** is the share of the carrying weight still free, so a loaded
  band does not gather.
- **Pull** of a neighbour is the best worth among the known cells that
  lie closer to it than to the band, each divided by 1 plus its distance
  in cells times `distance`. The neighbour itself is one of them.
- **Effort** is 1 over the passability of the neighbour, held at 4: a
  tired band does not start into a swamp.

A move scores above zero only when something known is better than the
place the band stands on. A band on good land stays; a band on stripped
land goes.

___

## Choosing

The best score wins. Two rules settle the rest.

- **A tie** goes to the option that comes first in a fixed order: `camp`,
  `gather` forage, `gather` water, then the moves clockwise from the
  north.
- **A move in progress is kept.** The cell the band is already walking
  towards gets `weights.momentum` added, so a band does not turn back in
  the middle of a forest.

When nothing scores above `idle`, the band has no reason to do anything
in particular. Then it wanders: one of the cells it can enter is drawn
from the game's stream `decisions`, and the band keeps that direction
for a day. This is the only random draw of the function, and how a band
on a bare plain finds better land.

___

## Under an intent

A proposal the council passed is the band's intent. An intent does not
replace the function: it narrows the options and the function chooses
among what is left.

| Intent            | Options left                              |
|-------------------|-------------------------------------------|
| `move` a direction| a move that way, or a camp                |
| `rest`            | a camp                                    |
| `stay-and-gather` | gathering of any resource, or a camp      |

"That way" is the named direction first. When that cell cannot be
entered, the two directions beside it are taken, the clockwise one
first; when neither can, the intent ends early. Under a `move` intent
the moves are scored with the pull replaced by a fixed `weights.intent`,
so the band walks by day and still camps when the rest outweighs it.

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
      comfort: {days: 2}
      night: 0.5
      night_parts: [evening, night]
      distance: 0.25
      idle: 0.05
      wander: {days: 1}
      weights:
        hunger: 1.0
        thirst: 1.2
        rest: 1.0
        safety: 0.3
        move: 1.0
        momentum: 0.1
        intent: 0.6
```

`night_parts` names the parts of the day that add `night` to the need
for rest; a name must be one of `time.day_parts`.

___

## Examples

A band of 15 at midday in a summer forest, rested, with half a day of
food and a day of water: 37.5 kg of the 90 it can carry, so the room is
0.58. Hunger is 0.75, thirst 0.5, rest 0.1.

```text
camp            1.0 * 0.1                  = 0.10
gather forage   1.0 * 0.75 * 0.9 * 0.58    = 0.39
gather water    1.2 * 0.5  * 0.6 * 0.58    = 0.21
move east       grass beyond, worth lower  < 0
-> gather forage
```

The same band at night with fatigue 0.55, a day and a half of food and
a room of 0.3. Hunger is 0.25, rest is 0.55 plus 0.5, held at 1.

```text
camp            1.0 * 1.0                  = 1.00
gather forage   1.0 * 0.25 * 0.9 * 0.3     = 0.07
-> camp
```

The same band on a stripped forest cell, food at a stock of 0.1, with
a full forest remembered three cells to the east. Hunger is 0.75, thirst
0, rest 0.1; the threat of 0.4 takes 0.12 from the worth of both cells.

```text
gather forage   1.0 * 0.75 * 0.09 * 0.6          = 0.04
move east       pull   (0.75 * 0.9 - 0.12) / 1.75 = 0.32
                own     0.75 * 0.09 - 0.12        = -0.05
                effort  1.0 * 0.1 * 1.67          = 0.17
                1.0 * (0.32 + 0.05) - 0.17        = 0.20
-> move east
```

___

## Open points

- **Looking ahead** - the function scores one tick. A band does not
  count that the walk to better land costs a day it has no food for.
- **Stores that spoil** - a band gathers up to its carrying weight even
  when the lot will spoil before it is eaten.
- **Safety** - threat lowers the worth of a cell but a band never flees
  one. A band that was just struck could leave.
- **Weights per band** - one set of weights serves every band until
  stage 3 names temperaments.
