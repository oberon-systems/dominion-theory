# Setup

#dev #sop

How to bring a fresh clone to a working state, check it and run what
exists: the server, the console client, a game to play and the map tool.

- [What this covers](#what-this-covers)
- [Install](#install)
- [Check](#check)
- [Run the server](#run-the-server)
- [Run the client](#run-the-client)
- [Play a band](#play-a-band)
- [Settings](#settings)
- [The data directory](#the-data-directory)
- [Look at a map](#look-at-a-map)
- [Commit](#commit)
- [Version](#version)
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

`make test` runs the tests of the code first and stops when one fails.
After them it keeps the reference of the maps,
`tests/planet/maps.json`: for three seeds of the default planet and of
every preset that shapes the planet, where the first window lies,
how many rivers run, the share of every biome, how many square corners
the shore has and a hash of every cell, with a hash of what a map follows
from: the section `planet`, where each biome appears, the size of a cell,
the code of the content and of the planet, and the code that counts the
reference itself. A change of anything else in the tree, a number of the
band for one, redraws nothing.

- **Nothing changed** - the hashes of the inputs agree and nothing is
  built.
- **Something changed** - the planets are built, the reference is
  rewritten, every value that moved is printed as `old -> new`, and the
  maps are drawn as [`make maps`](#look-at-a-map) draws them.

So a change of the planet shows twice: as pictures to look at, and as a
difference of the reference in git. Commit the reference with the change
that moved it.

```bash
git diff tests/planet/maps.json
```

A test fails when the reference is not the one of the planet as it is,
which happens when the tests are run past `make test`, and when the shore
of a first window has square corners: water cut by the grid of the
skeleton instead of by the land. The numbers say that a map moved, not
whether it is better, so the pictures are still looked at.

The life of a band is kept the same way, in `tests/runner/lives.json`.
Five seeds live ten years with no player, a row a year: people, births and
deaths by cause, stores, actions, states, encounters, the cells the band
remembers (`known`) and the size of the snapshot the store would keep, in
KB (`snapshot`), with a hash of the state at the end of every year, so a
band that walks another way to the same totals still moves the reference.
Fifty more seeds live one year each, and the reference keeps the tick
every band that died in it died at.

The reference follows the tree but the section `council`, of which only
the status the player starts with is kept, and the code of
the content, the engine, the planet and the codec of the snapshot. When
any of it changed, `make test` runs `make lives`: the seeds are lived anew,
the reference is rewritten, every value that moved is printed as
`old -> new`, and the tables go to `lives/<moment>/report.txt` with the
time every seed took, a tick and a snapshot packed. The times are not kept
in the reference, since they move from one run to the next.

```bash
git diff tests/runner/lives.json
```

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

## Play a band

Play a band from one terminal. The target starts a server of its own on
a free port, waits for it and stops it when the game ends, so `make run`
is not needed; the server logs into `data/play-server.log`. The game is
new, in step mode, and you sit in the seat of its council.

```bash
make play
```

The terminal becomes a screen of two panes, drawn with
[Textual](https://textual.textualize.io/). The left pane is for playing:

- **the map** - the land the band knows around it, a cell as two
  characters on the colour of its biome, a glyph for the biome, `~` for a
  river and `@` for the band;
- **the band** - its people, stores, states, action, fatigue and intent,
  and your standing;
- **its place** - the biome of the band's cell and its properties as the
  band knows them, as bars;
- **the council** - while a council sits, its question and a
  menu of every option: the ones the others voted for first, with their
  votes, the leader marked and under the pointer, then the rest, and
  saying nothing last. A council meets only when an occasion calls it;
  on other evenings the screen runs on. When an occasion calls a council
  that is settled, the screen stops on "go on" so that what happened can
  be read before the night.

The right pane is the log: a line per update with something to tell, the
date, the standing and what happened.

| Key        | Does                                             |
|------------|--------------------------------------------------|
| arrows     | move the pointer in the council's menu           |
| Enter      | picks the option under the pointer               |
| q, Ctrl-C  | leaves the game                                  |

Backing an option with votes and proposing one without are the same
pick; saying nothing costs standing.
[Indirect control](../game/indirect_control.md) tells what each answer
does to the band and to your standing. Every other tick is answered with
`pass`, one each `--pace` seconds, so the band is seen to move between two
councils.

Options go through `PLAY`:

```bash
make play PLAY='--lang ru --seed 42'
make play PLAY='--debug'
make play PLAY='--preset harsh-winter --updates 200'
```

| Option       | Does                                                       |
|--------------|------------------------------------------------------------|
| `--lang`     | plays in `en` or `ru`                                      |
| `--seed`     | the seed of the game                                       |
| `--preset`   | the preset of the game                                     |
| `--set`      | overrides one parameter, as `PATH=VALUE`                   |
| `--updates`  | stops after that many updates                              |
| `--pace`     | seconds between two ticks on the screen, 0.2 by default    |
| `--debug`    | adds the stocks of the cell and the band's reason          |
| `--server`   | plays on that server instead; `make play` sets it          |
| `--wait`     | seconds to wait for the server to answer, 0 by default     |

With `--debug` the panel of the place also shows when the band saw the
cell, the stocks of the cell as the game holds them, what every value
moved by in the last update, and the reason of the band's last decision.
Those words are the names of the parameter tree and are not translated.

When the input or the output is not a terminal, as in a pipe, the game
is played as lines instead: a coloured line per update, and at every
council the map and a numbered list. The answer is then read as a line: a
number, a name of the API (`east`, `ne`, `stay`, `abstain`) or an
empty line, which says nothing. Colour is dropped when the output is not
a terminal.

```bash
printf 'stay\n\n' | make play PLAY='--updates 10'
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
| `DT_COUNCIL_WAIT_S` | `30`                      | how long a council waits for the player |
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
Escape. The wheel of the mouse, or plus and minus, zoom in and out on the
cell under the pointer; a drag with the left button or the arrows move
the map. A panel beside the map holds the legend with the share of every
biome, and under it the cell the pointer is on: its place, its biome,
whether a river crosses it, its properties and the layers. Open water is
painted darker the deeper it lies. The
terminal gets the shares as well.

```bash
make map
```

`make map` shows the land a band era is played on, a piece of the planet
5120 km across, so no continent fits in it. The whole planet, with that
piece outlined in red, is another target and takes the same options.

```bash
make planet
make planet MAP='--seed 42'
```

A preset is named after a dash, for the planet and for the window alike.

```bash
make planet-dune
make planet-pangea MAP='--seed 42'
make map-archipelago
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
| `--scale`   | pixels to a side of a cell at the start, 2 unless given     |
| `--out`     | writes the picture to a file and opens no window            |

Expected output:

```text
default, seed 42: the window at 1730, 540, try 2 of 128, 0 needs missed
rivers: 310
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
make maps PRESETS=pangea SEEDS='1 2 3'
make maps PRESETS=
```

The default planet and every preset of `PRESETS` are drawn for every seed
of `SEEDS`. The presets
`pangea`, `continents` and `archipelago` are the types of planet and
`dune` is a desert world;
[Generation](../biomes/generation.md#continents) tells what they change.
An empty `PRESETS` draws the default alone.

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

## Version

The version is `0.MILESTONE.PATCH` until the game reaches 1.0.0: 0.1 is
the band era with the console client and some gameplay, 0.2 the web. A
bump first shows its dry run with the changelog it would write, asks
`[N/y]`, and only on `y` writes the changelog, the version in `.cz.yaml`
and `pyproject.toml`, commits and tags.

A version is moved only through `make`. A `cz bump` run by hand is
refused by a hook of `.cz.yaml`, which puts the version back.

| Target            | Moves                         | Example         |
|-------------------|-------------------------------|-----------------|
| `make bump`       | the patch                     | 0.1.3 to 0.1.4  |
| `make major`      | the milestone                 | 0.1.4 to 0.2.0  |
| `make release-rc` | the next candidate of 1.0.0   | 1.0.0-rc0, rc1  |
| `make release`    | the major version             | 1.0.0           |

`release-rc` and `release` are closed and stop with a message until the
game is ready for 1.0.0. Opening them also sets `major_version_zero` to
false in `.cz.yaml`.

```bash
make bump
```

___

## Clean up

Remove the virtualenv, the hook environments and the build output.

```bash
make clean
```
