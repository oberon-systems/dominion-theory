# Storage

#architecture #storage #stage0

Where the game keeps things outside the engine: the store for running
games, the database for what lasts, and files for run records. Part of the
stage 0 design in [the roadmap](../roadmap.md).

- [Three places](#three-places)
- [Settings](#settings)
- [The game store](#the-game-store)
- [Keys](#keys)
- [After a restart](#after-a-restart)
- [The database](#the-database)
- [Tables](#tables)
- [Rules for tables](#rules-for-tables)
- [Local and tests](#local-and-tests)
- [Open points](#open-points)

___

## Three places

What a thing is decides where it goes.

| The thing                                     | Goes to      | Why                               |
|-----------------------------------------------|--------------|-----------------------------------|
| changes every tick, needed only while running | game store   | fast, and cheap to lose           |
| small, lasting, looked up by a query          | database     | survives, can be listed           |
| large, written once, read as a whole          | file on disk | a database is a poor place for it |

The engine uses none of them. The runner owns the store and the files; the
API reads and writes the database.

___

## Settings

Storage is configured by settings of the server, and every one has a
default that works on a laptop with nothing installed.

| Setting           | Default                       | Meaning                              |
|-------------------|-------------------------------|--------------------------------------|
| `DT_DATA_DIR`     | `./data`                      | root for everything written locally  |
| `DT_STORE_URL`    | empty                         | empty is the in-process fake         |
| `DT_STORE_TTL`    | `7d`                          | how long an untouched game is kept   |
| `DT_DATABASE_URL` | SQLite file in the data dir   | which database, by its URL           |
| `DT_RECORDS_DIR`  | `records` in the data dir     | where run records are written        |

The data directory is ignored by git.

___

## The game store

The store holds a copy of every running game, so that the server can pick
its games up again. It is a key-value store with the interface of
[Valkey](https://valkey.io/).

By default it is [fakeredis](https://fakeredis.readthedocs.io/), which
keeps everything in the memory of the server process and needs no
service. When `DT_STORE_URL` names a Valkey server, the same code talks to
that instead.

The runner reaches the store through one small interface and never
through the client library directly.

| Operation               | Does                                                 |
|-------------------------|------------------------------------------------------|
| `save_snapshot`         | writes the whole state and forgets the changes       |
| `append_changes`        | adds the changes of one tick                         |
| `load`                  | returns the last snapshot and the changes after it   |
| `live_games`            | lists the games that have a copy                     |
| `drop`                  | removes a game                                       |

A snapshot is written at the start of each game day and the changes of
every tick in between, so a restore replays at most one day of changes.
A command taken since the snapshot is kept in the same list, so a restored
game holds the commands that were waiting when the server stopped.

___

## Keys

Every key starts with `dt:`, so the game can share a server with
something else.

| Key                       | Kind   | Holds                                      |
|---------------------------|--------|--------------------------------------------|
| `dt:games`                | set    | identifiers of live games                  |
| `dt:game:<id>:meta`       | hash   | seed, hash of parameters, last tick, mode  |
| `dt:game:<id>:snapshot`   | string | the state at the start of the current day  |
| `dt:game:<id>:changes`    | list   | ticks and commands since then, in order    |

A snapshot is a JSON document for everything that is not a grid, and the
grids - the biomes now, the state of the cells later - packed as arrays
and compressed with zlib. Every key of a game expires after
`DT_STORE_TTL` unless the game is touched.

When a game ends, its keys are removed: the run record and the row in the
index are what remains of it.

___

## After a restart

When the server starts, the runner asks the store for its live games and
restores each one, paused.

With the default fake store there is nothing to find, because the fake
lives and dies with the process. A game that was running is then not
lost, only stopped: it stays in the index as unfinished, and its
[run record](records.md) can be replayed up to the last game day that was
written.

So the store buys two things over the record alone: a game comes back at
the exact tick it stopped, and it comes back without replaying its whole
history.

___

## The database

The database holds what must outlast a game and be found again. It is
reached through [SQLModel](https://sqlmodel.tiangolo.com/), and
`DT_DATABASE_URL` alone decides the engine: SQLite by default,
PostgreSQL when a URL says so.

Nothing in the code depends on one engine. Only column types that both
have are used, and no query is written in the dialect of one of them.

The schema is built by numbered migrations, with
[Alembic](https://alembic.sqlalchemy.org/). A migration is never edited
once it has been applied anywhere. The server applies the migrations it
lacks when it starts, so a local run needs no step of its own for them.

___

## Tables

Stage 0 has two.

**`profiles`** - the person who plays.

| Column       | Holds                                  |
|--------------|----------------------------------------|
| `id`         | identifier                             |
| `name`       | the name shown in the game             |
| `locale`     | language of the game, `en` or `ru`     |
| `created_at` | wall-clock time, in Unix seconds       |

A local server has one profile, `local`, created the first time it starts.
Every time is a whole number of Unix seconds, so that both engines store
it the same way.

**`games`** - the index of games, described with
[run records](records.md#the-index-of-games).

___

## Rules for tables

The tables are plain, and the rules that keep them so are not open to
discussion per table.

- **No relations.** No foreign key, no cascade, no trigger that writes to
  another table. Tables are tied by plain value columns, such as
  `profile_id` in `games`, which the code keeps consistent.
- **A new feature is a new table.** An existing table is not widened.
- **No bulk content.** A row points at a file; it does not hold it.
- **What a cascade would have done, the code does** in the same
  transaction, from one list of every column that refers to a profile.
- **Changing a column's type or size** is the only alteration of a table,
  and each one is agreed before it is written.

Two tests guard this: one fails when the schema holds a foreign key, the
other when a column that refers to a profile is missing from the list. A
hook of `make lint` refuses a migration that names a relation or alters a
table.

___

## Local and tests

Everything local runs on the defaults: the fake store, a SQLite file, a
directory for records. Nothing has to be installed or started.

Tests use the fake store and a SQLite database of their own, made fresh
for the run. No test needs a Valkey or a PostgreSQL server, and none
reaches one.

Running the suite against real servers is a separate, manual check, done
before the first deployment that uses them.

___

## Open points

- **Who is the player** - a local server has one profile and asks no
  password. How a player is told apart on a server that others can reach
  is not designed.
- **How the snapshot is packed** - the grids are raw arrays behind a JSON
  head, compressed together. Whether another encoding is worth it is
  measured on a map that carries cell state.
- **Changes or snapshots only** - if a snapshot proves cheap enough, it can
  be written every tick and the list of changes dropped.
