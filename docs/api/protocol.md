# Protocol

#api #protocol #stage0 #stage2

How a client talks to the game: the addresses, the messages and the stream
of updates. It is written so that a browser, a Unity client and a program
that plays can all be built from this page. Part of the stage 0 design in
[the roadmap](../roadmap.md).

- [Shape of the API](#shape-of-the-api)
- [Addresses](#addresses)
- [Starting a game](#starting-a-game)
- [The snapshot](#the-snapshot)
- [The stream of updates](#the-stream-of-updates)
- [Falling behind](#falling-behind)
- [Coordinates](#coordinates)
- [The map](#the-map)
- [Views](#views)
- [Controlling the clock](#controlling-the-clock)
- [Errors](#errors)
- [Schema and versions](#schema-and-versions)
- [Open points](#open-points)

___

## Shape of the API

Two channels, both carrying JSON.

- **HTTP** for everything a client asks for: create a game, read its
  state, send a command.
- **A WebSocket** for what the game tells the client unasked: one stream
  of updates per game.

A client never has to poll. It reads a snapshot once, then applies
updates as they come.

The API carries no sentences. Everything a player reads arrives as a
message key with values, as [Localisation](../architecture/localisation.md)
describes.

___

## Addresses

Every address starts with `/api/v1`.

| Method | Address                       | Does                                      |
|--------|-------------------------------|-------------------------------------------|
| GET    | `/health`                     | says the server is up                     |
| GET    | `/profile`                    | the player's profile                      |
| PATCH  | `/profile`                    | changes the name or the language          |
| GET    | `/locales/{lang}`             | the catalogue of one language             |
| GET    | `/presets`                    | the named sets of parameters              |
| POST   | `/games`                      | creates a game                            |
| GET    | `/games`                      | lists games, from the index               |
| GET    | `/games/{id}`                 | one game: mode, date, whether it runs     |
| DELETE | `/games/{id}`                 | ends a game                               |
| GET    | `/games/{id}/params`          | the resolved tree of parameters           |
| GET    | `/games/{id}/snapshot`        | the state, as the caller may see it       |
| GET    | `/games/{id}/biomes`          | the biomes of the game, for the era       |
| GET    | `/games/{id}/map`             | a rectangle of the map                    |
| POST   | `/games/{id}/commands`        | sends a command                           |
| POST   | `/games/{id}/clock`           | pause, resume, speed, step                |
| GET    | `/games/{id}/record`          | the run record, as a file                 |
| WS     | `/games/{id}/updates`         | the stream of updates                     |
| GET    | `/openapi.json`               | the description of the HTTP side          |
| GET    | `/updates.schema.json`        | the schema of a message of the stream     |

A profile is its `id`, its `name` and its `language`. Ending a game
answers with its row of the index, as the list of games gives it.

___

## Starting a game

A game is created from a seed, a set of parameters and a mode. All three
may be left out: the seed is then drawn, the parameters are the defaults
and the mode is real time.

```json
{
  "seed": 42,
  "preset": "harsh-winter",
  "overrides": {"planet.window.width": 256},
  "mode": "step"
}
```

The answer names the game and says where it stands.

```json
{
  "id": "7f3a9c1e",
  "seed": 42,
  "params_hash": "b41f",
  "mode": "step",
  "running": false,
  "date": {"year": 1, "month": 1, "day": 1, "part": "morning", "season": "spring"}
}
```

A game starts paused, and the answer has status 201. Parameters that fail
their check are refused with the path of the value, what was found and
what was expected; see [Parameters](../architecture/parameters.md).

___

## The snapshot

A snapshot is everything the caller may see at one moment. It carries the
number of the last update it includes, so the stream can be joined right
after it.

```json
{
  "seq": 311,
  "date": {"year": 1, "month": 7, "day": 3, "part": "evening", "season": "autumn"},
  "window": {"scale": 0, "x": 2040, "y": 610, "width": 512, "height": 256},
  "seat": {"name": "player", "unit": 1, "status": 47.0, "seated": true, "council": null},
  "units": [
    {
      "id": 1,
      "kind": "band",
      "place": {"scale": 0, "x": 2301, "y": 744},
      "population": 18,
      "ages": {"child": 4, "adult": 12, "elder": 2},
      "pregnant": 1,
      "injured": 0,
      "wounds": {"light": 0, "medium": 0, "heavy": 0},
      "stores": {"forage": 22.5, "water": 30.0},
      "fatigue": 0.3,
      "states": [],
      "action": {"kind": "camp"},
      "intent": null,
      "reason": {"action": "camp", "need": "rest", "score": 0.0, "pull": null},
      "lore": ["orientation"]
    }
  ],
  "waiting": []
}
```

The map is not in the snapshot: it is large and is fetched in pieces.
The window is where the first window was placed on the planet, so it does
not start at the origin; see
[Generation](../biomes/generation.md#the-first-window).

### The seat

- **`unit`** - the id of the seat's band, `null` once the band is gone.
- **`status`** - the player's weight in the council, 0 to 100; see
  [Indirect control](../game/indirect_control.md#status).
- **`seated`** - whether a player sits in the seat; a game with an empty
  seat has no council.
- **`council`** - the council of the day while it sits, `null` otherwise:
  the `leader`, the option the others lean to or `null`, the `table`,
  every option with its words, `key`, and its votes, as
  [Indirect control](../game/indirect_control.md#the-table-of-votes)
  lays them out, the `voice`, the votes the player's word adds,
  `winter`, whether a winter camp is offered, and `place`, whether the
  player may name a place no option names; see
  [Skills](../game/skills.md#the-council).

```json
{
  "leader": {"kind": "stay-and-gather"},
  "table": [
    {"proposal": {"kind": "stay-and-gather"}, "key": "proposal-stay-and-gather", "votes": 8},
    {"proposal": {"kind": "go", "to": {"x": 2301, "y": 740}}, "key": "proposal-go-through-grass", "votes": 1},
    {"proposal": {"kind": "go", "to": {"x": 2304, "y": 744}}, "key": "proposal-go-forest", "votes": 5}
  ],
  "voice": 3.75,
  "winter": false,
  "place": true
}
```

### A unit

A unit is a band in stage 2, as
[Bands](../game/01_bands.md#what-the-api-shows) shows it.

| Field        | Holds                                                       |
|--------------|-------------------------------------------------------------|
| `place`      | the cell it stands on, with the scale                       |
| `population` | the people in it                                            |
| `ages`       | the people by stage of life: `child`, `adult`, `elder`      |
| `pregnant`   | the women with child                                        |
| `injured`    | the people who are hurt and not yet healed                  |
| `wounds`     | the injured by severity: `light`, `medium`, `heavy`         |
| `stores`     | the amount held of each resource                            |
| `fatigue`    | 0 for rested, growing with work                             |
| `states`     | `starvation`, `thirst`, `tiredness`, in that order          |
| `action`     | what it did in the last tick: `camp`, `build`, `gather`, `move` or `roam` |
| `intent`     | the proposal the council bound it to, or `null`             |
| `route`      | the cells still ahead to the place of a go, each `{"x", "y"}` |
| `roles`      | the people by role: `gatherer`, `nanny`                     |
| `camp`       | its winter camp, `{"x", "y", "built"}` with the share built, or `null` |
| `reason`     | why it took that action; see [Decisions](../game/decisions.md#the-reason) |
| `lore`       | the skills it knows, in the order learned; see [Skills](../game/skills.md#the-skills) |

An action of `gather` carries its `shares`, the share of the gatherers
that went to every resource, `{"forage": 0.56, "water": 0.44}`, and one
of `move` its `towards`. An intent is `null` or a proposal as
[Commands](commands.md#the-commands) gives it.

```json
{"proposal": {"kind": "go", "to": {"x": 2304, "y": 744}}}
```

___

## The stream of updates

After the snapshot the client opens the stream and says which update it
has. Without `after` the stream starts at the present.

```text
/api/v1/games/7f3a9c1e/updates?after=311
```

Each message on the stream is one update.

```json
{
  "seq": 312,
  "date": {"year": 1, "month": 7, "day": 3, "part": "evening", "season": "autumn"},
  "events": [
    {"key": "council-turned", "values": {"proposal": "proposal-stay-and-gather", "yes": 8.75, "all": 17.75}}
  ],
  "changes": {
    "units": [
      {
        "id": 1,
        "kind": "band",
        "place": {"scale": 0, "x": 2301, "y": 744},
        "population": 18,
        "ages": {"child": 4, "adult": 12, "elder": 2},
        "pregnant": 1,
        "injured": 0,
      "wounds": {"light": 0, "medium": 0, "heavy": 0},
        "stores": {"forage": 22.5, "water": 30.0},
        "fatigue": 0.0,
        "states": [],
        "action": {"kind": "camp"},
        "intent": {"proposal": {"kind": "stay-and-gather"}},
        "reason": {"action": "camp", "need": "rest", "score": 0.0, "pull": null}
      }
    ],
    "gone": [],
    "cells": [{"x": 2301, "y": 744, "water": 1.0, "food": 0.4}],
    "known": [
      {"x": 2301, "y": 744, "biome": "forest", "river": false, "water": 0.6,
       "food": 0.36, "threat": 0.4, "passability": 0.6, "seen": 63}
    ],
    "seat": {"council": null}
  },
  "waiting": ["player"]
}
```

- **`seq`** grows by one with every update. It is the only thing a client
  orders by.
- **`date`** is the date of the game after the update.
- **`events`** are what happened, in order.
- **`changes`** hold the whole new value of each thing that changed, not
  the fields that differ, so a client replaces what it has.
- **`changes.units`** holds every unit whose shown form changed, whole.
  The `reason` changes with the part of the day, so a band is sent in
  most updates.
- **`changes.gone`** names the units that left the game: a band that died.
- **`changes.cells`** lists every cell whose stock moved, with its place
  and one number per stock of the era: `water` and `food` in the band
  era. A cell that is back to full is listed once more, with every stock
  at 1.
- **`changes.known`** lists the cells the band now remembers differently
  from before: its biome, its river, the value of every property of the
  era as the band saw it, and the day it was seen.
- **`changes.seat`** carries only the keys of the seat that moved:
  `council` when the council of the day sat down, with its table, or
  rose, as `null`; `status` when the status changed.
- **`waiting`** names the seats a game in step mode is waiting for.

An update is not a tick. The client is never told how many steps of the
engine an update covers, and a fast game may cover several in one.

When a game ends the server closes the stream. A game the rules end - the
band died, the player was banished - sends its last update first, with the
event that ended it and nobody waiting. A stream that cannot be
served - no such game, a view that is not offered - gets one message, the
error, and is closed with the code 4000 plus the HTTP status of that
error: 4404 for a game that is not found.

___

## Falling behind

The server keeps the last updates of a game for clients that reconnect:
512 of them, or what the setting `DT_UPDATES_KEPT` says.

- A client that returns with `after` still in that window is sent what it
  missed and carries on.
- A client that has been away longer is sent one message, `resync`, and
  must read the snapshot again.

```json
{"resync": true, "seq": 1904}
```

A client that sees a gap in `seq` does the same of its own accord.

___

## Coordinates

A place is a cell of the planet at a scale.

- **`scale`** is the step of the zoom: 0 in the band era, 1 after the
  first zoom out, and so on. A cell of a higher scale covers a square of
  cells of the scale below.
- **`x`** counts cells from the western edge and wraps around: the planet
  is closed from east to west.
- **`y`** counts cells from the northern edge and does not wrap.

Positions inside a snapshot or an update leave the scale out and use the
one of the window. The window says which rectangle of the planet the game
is played on.

Because a place is always a cell of the planet, not of the window, it
keeps its meaning when the window grows, and places of different eras can
be laid over one map.

___

## The map

The map is read in rectangles, in planet coordinates of the window's
scale.

```text
/api/v1/games/7f3a9c1e/map?x=2040&y=610&width=64&height=64
```

The answer gives the biome of every cell, row by row, as indexes into the
list of the biomes of the game, and the rivers and the stocks of the cells
in the same order.

```json
{
  "scale": 0,
  "x": 2040, "y": 610, "width": 64, "height": 64,
  "biomes": ["water", "mountain", "hills", "forest", "grass"],
  "cells": [4, 4, 3, 3, 0],
  "rivers": [0, 0, 1, 0, 0],
  "water": [1.0, 1.0, 1.0, 1.0, 1.0],
  "food": [1.0, 0.8, 1.0, 0.4, 1.0]
}
```

- **`biomes`** is every biome of the game in its order of generation,
  present in the rectangle or not, so an index means the same in every
  answer.
- **`rivers`** is 1 where a river crosses the cell and 0 elsewhere.
- **A stock** is one list per property that recovers in the era, `water`
  and `food` for a band: 1 for an untouched cell, 0 for one stripped bare.
  The names come from the era, so the schema lists them as additional
  fields.

Biomes and rivers do not change during an era, so a client fetches each
rectangle once. What does change - a cell being exhausted and recovering -
comes in the `cells` of an update.

The answer holds the part of the asked rectangle that lies in the window,
and a request with no rectangle gets the whole window.

### What a band knows

With `known` and the id of a unit, the same rectangle comes as that band
remembers it. An id the game does not hold is answered with 404 and
`error-unit-not-found`.

```text
/api/v1/games/7f3a9c1e/map?x=2299&y=742&width=3&height=1&known=1
```

```json
{
  "scale": 0,
  "x": 2299, "y": 742, "width": 3, "height": 1,
  "biomes": ["forest"],
  "cells": [null, 0, 0],
  "rivers": [null, 0, 1],
  "water": [null, 0.6, 1.0],
  "food": [null, 0.9, 0.36],
  "threat": [null, 0.4, 0.4],
  "passability": [null, 0.6, 0.6],
  "seen": [null, 63, 63]
}
```

- **A cell the band does not know** is `null` in every list.
- **`biomes`** holds only the biomes of the cells it knows, in their order
  of generation.
- **A property** is one list per property of the era, not per stock: the
  value as the band saw it, the season, the river and the stock applied.
- **`seen`** is the day the band last saw the cell. What it saw longer ago
  than its memory is forgotten and is `null` again.

What a biome is worth is read once per game.

```text
/api/v1/games/7f3a9c1e/biomes
```

```json
{
  "era": "band",
  "biomes": [
    {
      "id": "forest",
      "name": {"key": "biome-forest", "values": {}},
      "colour": "#006400",
      "properties": {"water": 0.6, "food": 0.9, "threat": 0.4, "passability": 0.6},
      "resources": ["water", "forage"]
    }
  ]
}
```

The list is in the same order as `biomes` of the map. The properties are
the bases of the current era; what a season, a river and a stock make of
them is told in [Biomes](../biomes/overview.md#base-and-modifiers).

___

## Views

The same game can be looked at in two ways.

- **`seat`** - what the player's band knows. This is what a person and an
  LLM play from, and it is the default.
- **`spectator`** - everything. It is for watching a game of bots and for
  finding faults, and it sends no commands.

The view is asked for with `?view=` on the snapshot, the biomes, the map
and the stream. Whether a server offers the spectator view is the setting
`DT_SPECTATOR`, on by default; a view that is not offered is answered
with 400. Both views show the same for now: what a band knows is read with
`known` on the map, in either view.

___

## Controlling the clock

Pause, speed and single steps are requests to the runner, not commands of
the game. They are not written into the run record and cannot change how
a game goes.

```json
{"action": "speed", "value": 2}
```

| Action   | Does                                                    |
|----------|---------------------------------------------------------|
| `pause`  | stops the clock                                         |
| `resume` | starts it                                               |
| `speed`  | sets the multiplier, in real-time mode                  |
| `step`   | advances once, in step mode or when paused              |

The answer is the game, as `GET /games/{id}` gives it. `step` on a clock
that is running is refused with 409, and in step mode there is no clock to
pause, resume or speed up: those three are taken and change nothing.

___

## Errors

A request that cannot be served gets an HTTP status and a body that is a
message, like everything else.

```json
{"key": "error-game-not-found", "values": {"id": "7f3a9c1e"}}
```

| Status | When                                                      |
|--------|-----------------------------------------------------------|
| 400    | the request cannot be read                                |
| 404    | no such game, preset, language or unit; the record is gone |
| 409    | the game has ended; a step was asked of a running clock   |
| 422    | the parameters, the command or a profile fail their check |

A command that the rules refuse is not an error of the API: it was
received correctly. The refusal comes as an event, described in
[Commands](commands.md).

___

## Schema and versions

The HTTP side is described by an [OpenAPI](https://www.openapis.org/)
document that the server produces from its own code, and the messages of
the stream by a JSON Schema beside it. A client in any language can be
generated or checked from the two. They are served at
`/api/v1/openapi.json` and `/api/v1/updates.schema.json`.

The `v1` in the address changes only when an existing field changes its
meaning or goes away. New addresses and new fields are added without a
new version, and a client ignores fields it does not know.

___

## Open points

- **Who is calling** - a local server has one profile and asks for no
  proof. Sign-in is designed when a server is first put where others can
  reach it.
- **How long the stream remembers** - the number is a setting now, with a
  default of 512 updates. What it should be for a browser on a poor line
  is seen in stage 4.
- **Map encoding** - plain lists are easy to read and large. A packed form
  is added if the map proves slow to load.
- **What a seat sees** - the seat view still shows the whole map. Whether
  it should show only what the band knows, as the known map does, is
  settled when a person first plays from the browser.
