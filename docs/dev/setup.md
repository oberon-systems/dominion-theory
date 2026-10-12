# Setup

#dev #sop

How to bring a fresh clone to a working state, check it and run what
exists: the server, the console client and the map tool.

- [What this covers](#what-this-covers)
- [Install](#install)
- [Check](#check)
- [Run the server](#run-the-server)
- [Run the client](#run-the-client)
- [Settings](#settings)
- [The data directory](#the-data-directory)
- [Look at a map](#look-at-a-map)
- [Commit](#commit)
- [Clean up](#clean-up)

___

## What this covers

Everything goes through the root `Makefile`. It creates a virtualenv in
`.venv`, keeps the hook environments in `.pre-commit` inside the
repository, and holds every command in full. You need Python 3.14, `make`
and `git`.

___

## Install

Create the virtualenv, install the tooling and the game, and wire up the
git hooks.

```bash
make install
```

Open a subshell with the virtualenv active. Leave it with `exit`.

```bash
make
```

Run `make install` again after a change of the dependencies in
`pyproject.toml`.

___

## Check

Run every hook over every file, tracked or not.

```bash
make lint
```

The hooks are [ruff](https://docs.astral.sh/ruff/),
[black](https://black.readthedocs.io/), [flake8](https://flake8.pycqa.org/),
[mypy](https://mypy.readthedocs.io/) and
[pymarkdown](https://pymarkdown.readthedocs.io/). ruff and black rewrite
files: when a hook reports a change, run the command again.

Run the tests.

```bash
make test
```

Expected output, with the number of tests growing over time:

```text
1 passed
```

The tests need nothing installed or started: they use the in-process
store, a SQLite file in a temporary directory, and the loopback address
for the tests of the client.

___

## Run the server

Start the server on the loopback address. Stop it with Ctrl-C.

```bash
make run
```

It listens on port 8000; `make run PORT=8010` picks another. Check that
it is up from a second terminal.

```bash
curl http://127.0.0.1:8000/api/v1/health
```

Expected output:

```json
{"status":"ok"}
```

The server describes its own API at
`http://127.0.0.1:8000/api/v1/docs`. [The protocol](../api/protocol.md)
says what the addresses mean.

___

## Run the client

With the server running, watch a new game from a second terminal. Stop
with Ctrl-C; the client pauses the game it started.

```bash
make watch
```

Expected output, one line per update:

```text
game 7f3a9c1e
midday, day 1, month 1, year 1, spring
afternoon, day 1, month 1, year 1, spring
```

Options go through `WATCH`, and `PORT` names the port of the server. The
language is the one of the profile unless `--lang` says otherwise.

```bash
make watch WATCH='--lang ru'
make watch WATCH='--step --updates 500 --seed 42'
make watch WATCH='--game 7f3a9c1e'
make watch WATCH='--preset harsh-winter --set planet.window.width=128'
```

| Option       | Does                                                      |
|--------------|-----------------------------------------------------------|
| `--lang`     | prints in `en` or `ru`                                    |
| `--step`     | plays in step mode and answers every wait with `pass`     |
| `--updates`  | stops after that many updates                             |
| `--game`     | joins a game by its identifier instead of creating one    |
| `--seed`     | the seed of a new game                                    |
| `--preset`   | the preset of a new game                                  |
| `--set`      | overrides one parameter of a new game, as `PATH=VALUE`    |

Replay the record of a game, from the subshell. The identifier is the
first line `watch` printed.

```bash
python -m dominion_theory.client replay 7f3a9c1e
```

Expected output:

```text
the record of 7f3a9c1e replays: 500 ticks, every hash matches
```

___

## Settings

The server reads its settings from the environment, with the prefix
`DT_`. Every one has a default that works with nothing installed.

| Setting           | Default                     | Meaning                                |
|-------------------|-----------------------------|----------------------------------------|
| `DT_DATA_DIR`     | `./data`                    | root for everything written locally    |
| `DT_DATABASE_URL` | SQLite file in the data dir | which database, by its URL             |
| `DT_RECORDS_DIR`  | `records` in the data dir   | where run records are written          |
| `DT_STORE_URL`    | empty                       | empty is the in-process store          |
| `DT_STORE_TTL`    | `7d`                        | how long an untouched game is kept     |
| `DT_TICK_MS`      | `500`                       | length of a tick in real time          |
| `DT_UPDATES_KEPT` | `512`                       | updates kept for clients that return   |
| `DT_SPECTATOR`    | `true`                      | whether the spectator view is offered  |

Set one for a single run.

```bash
DT_TICK_MS=100 make run
```

None of them changes how a game goes; what does is a parameter of the
game, as [Parameters](../architecture/parameters.md) describes.

___

## The data directory

Everything the server writes goes under `data` in the directory it was
started from, and git ignores it.

```text
data/
  dominion-theory.db
  records/
    7f3a9c1e.jsonl.gz
```

The database holds the profile and the index of games; the records hold
every game that was played. Running games live in the memory of the
server and are gone when it stops, unless `DT_STORE_URL` names a
[Valkey](https://valkey.io/) server. Remove the directory to start clean.

```bash
rm -rf data
```

___

## Look at a map

Generate a map and show it in a window. Close it with Escape.

```bash
make map
```

The tool takes a size, a seed and a property to colour by. Run it from the
subshell for anything but the defaults.

```bash
python -m dominion_theory.planet.tools --width 256 --height 256 --seed 42 simple
python -m dominion_theory.planet.tools property --name food
```

___

## Commit

Commit messages are written through
[commitizen](https://commitizen-tools.github.io/commitizen/) and checked by
a hook. From the subshell:

```bash
cz commit
```

___

## Clean up

Remove the virtualenv, the hook environments and the build output.

```bash
make clean
```
