# Architecture overview

#architecture #stage0

How the game is put together: the layers, the packages, what one tick does
and where every kind of data lives. Stage 0 of
[the roadmap](../roadmap.md) built this frame; what a later stage adds to
it is marked as such.

- [The idea in one picture](#the-idea-in-one-picture)
- [Packages](#packages)
- [The engine](#the-engine)
- [One tick](#one-tick)
- [Determinism](#determinism)
- [Runners](#runners)
- [Seats](#seats)
- [Where data lives](#where-data-lives)
- [How a proposal travels](#how-a-proposal-travels)
- [Rules for the code](#rules-for-the-code)
- [Open points](#open-points)

___

## The idea in one picture

The game is a simulation that runs on the server. Clients draw what it
reports and send what the player wants; they hold no rules.

```text
 console client  web client  LLM player  unity client
     |               |           |            |
     +-------+-------+-----------+------------+
             |  HTTP + WebSocket, JSON
     +-------+--------+
     |      api       |   games, commands in, state and events out
     +---+--------+---+
         |        |
   +-----+----+ +-+--------+
   |  runner  | |    db    |   profiles, game index
   +--+----+--+ +----------+
      |    |
      |  +-+-------+
      |  |  store  |          a copy of every live game
      |  +---------+
  +---+----+
  | engine |                  state + rules: step() and nothing else
  +---+----+
      |
  +---+-----------------------+
  | content: planet, biomes,  |
  | units, eras, resources    |
  +---------------------------+
```

Each layer knows only the ones below it. The engine can be imported and
stepped from a test with no server, no store and no database. Of the
clients only the console one exists: the browser client is stage 4, the
LLM player belongs to the lab.

___

## Packages

Everything is one Python distribution, `dominion_theory`, split into
packages by layer.

| Package   | Holds                                                    | May import                 |
|-----------|----------------------------------------------------------|----------------------------|
| `core`    | settings, logging, errors                                | nothing of ours            |
| `content` | the tree of parameters: schema, defaults, presets        | `core`                     |
| `planet`  | world generation: the planet, windows, rivers            | `core`, `content`          |
| `engine`  | game state, the tick, commands, events, clock, counters  | `core`, `content`, `planet`|
| `players` | scripted players, from stage 3                           | `engine`                   |
| `i18n`    | message keys and the catalogues                          | `core`                     |
| `store`   | the game store: fake by default, Valkey when configured  | `core`                     |
| `db`      | tables, sessions, migrations                             | `core`                     |
| `runner`  | live games, the two clocks, run records and replay       | `engine`, `store`, `content`|
| `api`     | the application, routes, the update stream               | `runner`, `engine`, `db`, `i18n` |
| `lab`     | the batch runner, the LLM player, statistics             | the API as a client        |
| `client`  | the console client: play, watch, step and replay a game  | `i18n`, `runner`           |

Every package may import `core`. `players` and `lab` are not built yet, and
the browser client will live in a top-level `web` directory, not in a
Python package.

The console client talks to the game over the API alone and renders
messages with `i18n`. It imports `runner` for one thing: a downloaded
record is replayed by running the engine again, and `replay` lives there.

___

## The engine

The engine is a library with one object, the game. It takes a seed and a
parameter tree, accepts commands, and advances by one tick when told to.

```python
from dominion_theory.engine import Game, Pass

game = Game.create(seed=42, params=params)
game.submit(Pass(seat='player'))
result = game.step()

result.events      # what happened, as message keys with values
result.changes     # what changed in the state since the last tick
result.counters    # one row of numbers for the run record
result.hash        # the hash of the state after this tick
game.snapshot()    # the whole state, serialisable
```

A game is restored from a snapshot, and a snapshot plus the commands that
followed it gives the same state again.

```python
copy = Game.restore(game.snapshot())
```

The engine never sleeps, never reads a clock, never opens a file or a
socket, and never produces text for a person.

___

## One tick

`step()` runs the same phases in the same order every time. The order is
part of the rules: changing it changes the outcome of a game.

1. **Commands** - the commands submitted since the last tick are taken in
   a fixed order and checked. A refused command becomes an event.
2. **Councils** - proposals are put to the vote; what is accepted becomes
   the band's intent.
3. **Decisions** - every unit without an intent decides for itself, in the
   order of unit identifiers.
4. **Actions** - units move, gather or camp. Conflicts over a cell are
   settled here.
5. **World** - cells recover, stores spoil, people eat and drink, chance
   encounters are drawn, proposals whose window closed are judged.
6. **Calendar** - time advances by the span of the era, and the day,
   month, season and year boundaries are noted. See [Time](time.md).
7. **Report** - events, changes and counters are returned.

Every phase is filled for the one band of stage 2; what each does to it
is told in [Bands](../game/01_bands.md#one-tick-of-a-band). What waits for
stage 3 is the part that needs more than one unit: the order of units in
`decisions` and the conflicts over a cell in `actions`.

___

## Determinism

The same seed, the same parameters and the same commands always give the
same game. Replay, the comparison of parameter sets and every test rest on
this.

- **Random numbers come from the game only.** Each subsystem draws from its
  own named stream derived from the seed, so a new draw in one subsystem
  does not shift the numbers of another.
- **No wall clock and no global state.** The only time is the tick counter.
- **Every iteration has a fixed order**: units by identifier, cells by
  coordinate, commands by seat and sequence number.
- **A state has a hash.** Two runs are compared by the hash after every
  tick, with numbers rounded so that it does not depend on the platform.

___

## Runners

A runner owns a game and decides when to call `step()`. There are two, and
they differ in nothing else.

The runner is all the API ever talks to: it takes commands, gives out
snapshots and hands out updates to whoever subscribed. It is also the only
thing that touches the store, where it keeps a copy of the game so that a
game outlives a restart of the server.

The store keeps a full snapshot at the start of each game day and the
commands in between. The reference of lives measures what that costs: a
snapshot of the band era packs to 21 to 28 KB, of which the band's memory
is up to 7 KB, and packing takes about 3 ms against 2.5 ms for a tick.
Once a day that is nothing. Every tick it would still be cheap in real
time, 3 ms of a 500 ms tick, but would double the cost of a tick in step
mode, so the snapshot stays once a day.

What leaves the runner is an **update**, not a tick: a sequence number,
the game date, the events and the changes. As built, one update covers
one tick; the contract leaves the runner free to fold several into one at
high speed. Nothing above the runner counts ticks: the API passes updates
on without reading them, and a client orders them by sequence number and
shows the date. In step mode an update also says which seats the game is
waiting for.

- **Real time** - a tick every `tick_ms` milliseconds, 500 by default. A
  command that arrives late waits for the next tick. Pause and speed are
  settings of the runner.
- **Step** - a tick when every seat has answered, or when a caller asks
  for one. This is what a slow player such as an LLM needs, and what a
  batch of a thousand games needs.

Speed and pause never reach the engine, so they are not part of a game's
record and cannot change its outcome.

___

## Seats

A seat is a place at the game that somebody plays from. Whoever holds it
sees the same observation and can send the same commands.

- **A person** in the console client, and later in the browser.
- **An LLM** through the lab's player, which is an API client like any
  other.
- **A scripted player**, in process, for tests and batches.

One game has one seat for now, and the seat speaks for one band. The
other bands of stage 3 are not seats: they are run by the engine's own
decision function. The seat sees its band, its status and when it may
call the next council; what the band knows of the land is read as a map,
as [the protocol](../api/protocol.md#what-a-band-knows) tells.

A seat leaves the game in two ways. Its band dies, or the band banishes
the player; either ends the game, the runner closes it and the index of
games keeps the outcome, `died` or `banished`.

___

## Where data lives

Three kinds of data, three places, and none of them is the engine.

| Data                         | Place         | Default                   | Lifetime          |
|------------------------------|---------------|---------------------------|-------------------|
| State of a running game      | game store    | in-process fake           | while it runs     |
| Profile: name, language      | database      | SQLite file               | permanent         |
| Index of games and outcomes  | database      | SQLite file               | permanent         |
| Run record of a game         | file on disk  | directory from settings   | until removed     |

The store is reached through one interface and by the runner alone, and a
[Valkey](https://valkey.io/) server replaces the fake by configuration. The database is reached
through [SQLModel](https://sqlmodel.tiangolo.com/); the connection string
picks SQLite or PostgreSQL. Tables are plain, with no foreign keys, and the
database keeps a path to a run record rather than its content. A run
record is a compressed file with one JSON object per line.

Tests and smoke runs use the fake store and SQLite only.

___

## How a proposal travels

The path of one player action, from the browser and back. The council is
a rule of stage 2; today `pass` travels the same path and comes back as
`command-accepted`.

1. The client sends "at the council of the day, I propose we stay and
   gather" to the API.
2. The API takes the caller for the one seat of the game, since there is
   no sign-in yet, and hands the command to the runner of that game.
3. The runner submits it to the engine before the next tick.
4. The engine checks the command against the rules - whether a council
   sits, for one - and counts the votes with the player's voice.
5. `step()` returns an event with the key `council-turned` and the
   values of the proposal.
6. The runner writes the changes to the store, appends the row of counters
   to the run record and hands an update to its subscribers.
7. The API, one of them, pushes the update to every connected client. The
   client looks the key up in the catalogue of the player's language and
   shows the words.

___

## Rules for the code

- **Imports go down only**, as the table of packages states. A test fails
  when `engine` imports `api`, `store`, `db` or `i18n`, and when `api`
  imports `store`.
- **Every balance number is a parameter.** No rule carries a literal that
  a designer would want to change.
- **Content is data.** A biome, a unit or an era is added by a data file
  and a test, not by an edit to the engine.
- **The engine speaks in keys.** Each event and each name shown to a
  player is a message key with values; a test fails when a key is missing
  from the English or the Russian catalogue.
- **Positions are planet coordinates with a scale**, never bare cell
  indexes, because the map zooms out from era to era.

___

## Open points

- **Folding updates** - whether a fast game puts several ticks into one
  update, and from which speed.
- **Splitting the server** - the API and the runner share one process. If
  they are ever split, the runner's interface gets a second implementation
  that works across processes; the API does not change.
