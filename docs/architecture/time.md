# Time

#architecture #time #stage0

How time is counted in the game: the tick, the day, the calendar and the
seasons, how fast it runs on the screen, and how rules state durations.
Part of the stage 0 design in [the roadmap](../roadmap.md).

- [Two kinds of time](#two-kinds-of-time)
- [The tick and the day](#the-tick-and-the-day)
- [The calendar](#the-calendar)
- [Seasons](#seasons)
- [Eras and the span of a tick](#eras-and-the-span-of-a-tick)
- [Real time](#real-time)
- [How rules state time](#how-rules-state-time)
- [Boundary events](#boundary-events)
- [Parameters](#parameters)
- [Open points](#open-points)

___

## Two kinds of time

Game time and real time are separate, and only one of them is part of the
rules.

- **Game time** is counted by the engine in whole steps. It decides what
  happens.
- **Real time** is how long a step takes on the screen. It belongs to the
  runner and decides nothing.

A game played at double speed, paused for an hour or run in a batch with
no waiting at all ends in the same state.

___

## The tick and the day

A tick is one call of the engine's `step()`: the smallest step there is,
and the same thing as a turn.

A day is made of **parts**, five of them, and the clock of a game is a
count of parts since the start. In the band era one tick is one part, so a
day is exactly five ticks. A part stands for about five hours, but no rule
counts hours.

| Part | Name        | What it is for in the band era            |
|------|-------------|-------------------------------------------|
| 1    | `morning`   | acting                                    |
| 2    | `midday`    | acting                                    |
| 3    | `afternoon` | acting                                    |
| 4    | `evening`   | acting, or making camp                    |
| 5    | `night`     | rest; the day's accounts are closed after |

What a band may do in each part is a rule of [the band](../units/band.md),
not of the clock. The clock only names the part.

___

## The calendar

The calendar is short, so that a year passes in minutes rather than hours.

| Unit   | Made of             | Parts | Ticks in the band era |
|--------|---------------------|-------|-----------------------|
| day    | 5 parts             | 5     | 5                     |
| month  | 10 days             | 50    | 50                    |
| year   | 10 months, 100 days | 500   | 500                   |

A date is worked out from the count of parts and is never stored on its
own. Years, months and days are numbered from 1, and the game starts on the
morning of day 1, month 1, year 1.

```text
parts = 1234
year  = parts // 500 + 1            -> 3
month = parts % 500 // 50 + 1       -> 5
day   = parts % 50 // 5 + 1         -> 7
part  = parts % 5 + 1               -> 5, night
```

Months have no names of their own yet; a month is shown by its season and
its number within it.

___

## Seasons

A year has four seasons, and it starts with spring.

| Season   | Months | Month numbers | Days |
|----------|--------|---------------|------|
| `spring` | 2      | 1-2           | 20   |
| `summer` | 3      | 3-5           | 30   |
| `autumn` | 2      | 6-7           | 20   |
| `winter` | 3      | 8-10          | 30   |

The number of months in a year is not set on its own: it is the sum of the
season lengths, so the two cannot disagree.

The seasons of a year are laid out when the year begins, into a schedule
that says on which day each one starts. For now the schedule is the table
above. Later it is drawn with some chance, so that winter can come early
or summer run long, and nothing else has to change: every rule asks the
schedule which season it is.

Stage 0 only tells the season. What it does to food, water and movement is
set with the biomes in stage 1 and the band in stage 2.

___

## Eras and the span of a tick

The world is played at one era at a time, and each era says how many parts
one tick covers. The count of parts runs on unbroken; only the step
changes.

| Era        | Parts per tick | A tick is | Ticks per year |
|------------|----------------|-----------|----------------|
| band       | 1              | 1/5 day   | 500            |
| tribe      | 5              | 1 day     | 100            |
| later eras | to be set      | longer    | fewer          |

Only the band row is decided. The tribe row shows the intent: as the map
zooms out and a cell covers more land, a tick covers more time, so that
movement stays near one cell per tick.

A change of era takes effect at the start of a day, so a tick never ends in
the middle of one.

___

## Real time

The length of a tick on the screen is `tick_ms`, a setting of the server
with a default of 500. It is not a parameter of the game and is not written
into a game's record.

At the default, in the band era:

| Game time    | Ticks | Real time    |
|--------------|-------|--------------|
| day          | 5     | 2.5 seconds  |
| month        | 50    | 25 seconds   |
| short season | 100   | 50 seconds   |
| long season  | 150   | 75 seconds   |
| year         | 500   | 4 min 10 sec |

The real-time runner offers pause and a speed multiplier. The step runner
has no `tick_ms` at all: a tick happens when every seat has answered, or
when the caller asks.

___

## How rules state time

A rule never says "every N ticks". It names a unit of the calendar, and
the engine turns that into parts.

- **A duration** is a number and a unit: `{days: 3}`, `{months: 1}`,
  `{parts: 2}`. The shortest gap between two councils and the window in
  which a proposal is judged are written this way.
- **A flow** - eating, drinking, spoiling, a cell recovering - is an
  amount per day. Each tick takes its share: the amount times the parts
  in the tick, over five.
- **A yearly rate** - births, deaths - is an amount per year, shared out
  the same way. Demography is tuned to the short year, not to real growth.
- **An action** - moving, gathering - takes one tick, whatever the tick
  covers in that era.

Because flows are shared out by parts, a rule written for the band era
keeps working when a tick becomes a day. Amounts are therefore fractional;
they are whole numbers only where they are shown to a player.

___

## Boundary events

When a tick crosses a boundary of the calendar, the engine reports it, in
this order: day, month, season, year.

| Key              | Values                  |
|------------------|-------------------------|
| `day-started`    | year, month, day        |
| `month-started`  | year, month, season     |
| `season-started` | year, season            |
| `year-started`   | year, the season plan   |

Rules that run once a day - judging a proposal whose window has closed,
for one - hang on `day-started` rather than on a count of ticks.

___

## Parameters

Time is part of the parameter tree of a game, so a run can be repeated
with a longer winter or a shorter month.

```yaml
time:
  day_parts: [morning, midday, afternoon, evening, night]
  days_per_month: 10
  seasons:
    - {name: spring, months: 2}
    - {name: summer, months: 3}
    - {name: autumn, months: 2}
    - {name: winter, months: 3}

eras:
  band:
    parts_per_tick: 1
```

The server setting stands apart from it.

```yaml
runner:
  tick_ms: 500
```

A game refuses to start when the tree does not add up: a season with no
months, or an era whose tick does not divide a day or cover whole days.

___

## Open points

- **The length of a game** - how many years the band era should take at
  the default speed. A target such as half an hour to an hour, seven to
  fourteen years, gives demography something to be tuned to.
- **Tribe time** - whether a tick of the tribe era is a day, as shown, or
  something else.
