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

`make test` also keeps the reference of the maps,
`tests/planet/maps.json`: for three seeds, where the first window lies,
how many rivers run, the share of every biome and a hash of every cell,
with a hash of what a map follows from, the default parameters and the
code of the planet.

- **Nothing changed** - the hashes of the inputs agree and nothing is
  built.
- **Something changed** - the three planets are built, the reference is
  rewritten, every value that moved is printed as `old -> new`, and the
  maps are drawn as [`make maps`](#look-at-a-map) draws them.

So a change of the planet shows twice: as pictures to look at, and as a
difference of the reference in git. Commit the reference with the change
that moved it.

```bash
git diff tests/planet/maps.json
```

A test fails when the reference is not the one of the planet as it is,
which happens when the tests are run past `make test`.

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

Draw the first window of a seed and show it in a window. Close it with
Escape. A panel beside the map holds the legend with the share of every
biome, and under it the cell the pointer is on: its place, its biome,
whether a river crosses it, its properties and the four layers. The
terminal gets the shares as well.

```bash
make map
```

Options go through `MAP`. With `--out` the picture is written to a file
and no window is opened, so a map can be looked at without a display.

```bash
make map MAP='--seed 42'
make map MAP='--seed 42 --planet --out ../alpha.png'
make map MAP='--seed 42 --show food --season winter'
make map MAP='--seed 42 --show all --out ../beta.png'
make map MAP='--preset harsh-winter --set planet.sea=0.5'
```

| Option      | Does                                                        |
|-------------|-------------------------------------------------------------|
| `--seed`    | the seed of the planet; drawn and printed when left out     |
| `--preset`  | the preset of the parameters, as for a game                 |
| `--set`     | overrides one parameter, as `PATH=VALUE`                    |
| `--planet`  | draws the whole planet, with the first window outlined      |
| `--cell-km` | the cell of the whole planet, 50 km unless given            |
| `--show`    | `biomes`, one property of the era, or `all` of them         |
| `--season`  | the season the properties are worked out for                |
| `--scale`   | pixels to a side of a cell, 2 unless given                  |
| `--out`     | writes the picture to a file and opens no window            |

Expected output:

```text
seed 42: the window at 1730, 540, try 2 of 64, 0 needs missed, 310 rivers
biome       of all  of land
water        60.0%
mountain      3.2%     8.0%
forest        8.2%    20.5%
cells with a river: 2.5%
written to ../alpha.png
```

The numbers are an example: one line per biome, and what they are depends
on the seed and the parameters.

The tool reads the planet the way a game does and changes nothing: the
same seed, preset and overrides give the same picture. It needs
[pygame](https://pyga.me/), which stays a developer tool until the web
client of stage 4.

Write the planet and the first window of several seeds as pictures, with
the shares of the biomes and the time every picture took in `report.txt`
beside them. This is how the numbers of the planet are tuned.

```bash
make maps
make maps SEEDS='7 8 9' MAPS=maps/alpha MAP='--set planet.sea=0.5'
```

Every run gets its own directory under `maps`, named by the moment it
started, so two runs can be laid side by side. git ignores the pictures
and keeps the reports: commit the report of a run whose numbers were
agreed, and a later change of the planet shows as a difference between
two reports.

```bash
diff maps/20260101-120000/report.txt maps/20260102-120000/report.txt
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
