# Protocol

#api #protocol #stage0

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
  "seat": {"name": "player", "unit": 1, "status": 47},
  "units": [
    {"id": 1, "kind": "band", "at": {"x": 2301, "y": 744}, "state": "normal", "action": "camp", "people": 18}
  ],
  "waiting": []
}
```

The map is not in the snapshot: it is large and is fetched in pieces.

Stage 0 answers with the frame of this. `seat` holds the name alone and
`units` is empty until stage 2 brings the band, and the window starts at
the origin until stage 1 places it on a planet.

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
  "date": {"year": 1, "month": 7, "day": 3, "part": "night", "season": "autumn"},
  "events": [
    {"key": "council-accepted", "values": {"unit": 1, "proposal": "proposal-rest"}}
  ],
  "changes": {
    "units": [
      {"id": 1, "kind": "band", "at": {"x": 2301, "y": 744}, "state": "normal", "action": "camp", "people": 18}
    ],
    "gone": [],
    "cells": [],
    "seat": {"status": 48}
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
- **`waiting`** names the seats a game in step mode is waiting for.

An update is not a tick. The client is never told how many steps of the
engine an update covers, and a fast game may cover several in one.

When a game ends the server closes the stream. A stream that cannot be
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

The answer gives the biome of every cell, row by row, as indexes into a
short list of the biomes present, and the state of the cells in the same
order.

```json
{
  "scale": 0,
  "x": 2040, "y": 610, "width": 64, "height": 64,
  "biomes": ["grass", "forest", "hills", "water"],
  "cells": [0, 0, 1, 1, 3],
  "food": [1.0, 0.8, 1.0, 0.4, 1.0]
}
```

Biomes do not change during an era, so a client fetches each rectangle
once. What does change - a cell being exhausted and recovering - comes in
the `cells` of an update.

The answer holds the part of the asked rectangle that lies in the window,
and a request with no rectangle gets the whole window. The state of the
cells, `food` here, is not sent yet: cells get a state in stage 1.

___

## Views

The same game can be looked at in two ways.

- **`seat`** - what the player's band knows. This is what a person and an
  LLM play from, and it is the default.
- **`spectator`** - everything. It is for watching a game of bots and for
  finding faults, and it sends no commands.

The view is asked for with `?view=` on the snapshot, the map and the
stream. Whether a server offers the spectator view is the setting
`DT_SPECTATOR`, on by default; a view that is not offered is answered
with 400. Until stage 2 gives a band something to know, both views show
the same.

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
| 404    | no such game, preset or language; the record is gone      |
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
- **What a seat sees** - how far a band knows the land around it is a rule
  of the band, set in stage 2.
