# Runs

#lab #runs #stagelab

How games are played by the thousand with nobody at the keyboard, how a
mind is trained, what a night leaves in the repository and how the
morning reads it. Part of the lab stage in
[the roadmap](../roadmap.md#stage-lab---players-and-statistics); the
players are in [Players](players.md), what is counted in
[Metrics](metrics.md).

- [What this covers](#what-this-covers)
- [A land and a draw](#a-land-and-a-draw)
- [The run file](#the-run-file)
- [Run a batch](#run-a-batch)
- [Training a mind](#training-a-mind)
- [Compare two runs](#compare-two-runs)
- [What a run leaves](#what-a-run-leaves)
- [The morning](#the-morning)
- [How long a night is](#how-long-a-night-is)
- [Open points](#open-points)

___

## What this covers

Three commands, each started in the evening and read in the morning.

| Command        | Does                                                          |
|----------------|---------------------------------------------------------------|
| `make batch`   | plays the games a run file asks for and writes their summary, report and heatmaps |
| `make train`   | trains a mind on the lands a run file names, and writes its weights |
| `make compare` | sets two runs on the same lands side by side                 |

Games are played in process, in step mode, by the runner the server
uses, in as many processes as the run asks: no server, no HTTP, nothing
but the local model's answers leaves the machine.

___

## A land and a draw

Today the seed of a game makes both its planet and every draw of its
life, so a player that never draws plays one seed the same way every
time. A heatmap of a land needs many lives on it. The game therefore
takes two numbers:

| Number  | Makes                                                           |
|---------|-----------------------------------------------------------------|
| `seed`  | the planet, the window and the start: the land                  |
| `draw`  | the streams of the game: births, deaths, encounters, wandering  |

A draw of 0 is the game of today, so every record and reference keeps
its meaning. The header of a record gains the draw, and a replay uses
it.

___

## The run file

A run is a file of YAML under `lab/runs/`, kept in the repository, so a
run can be played again by its name.

```yaml
run:
  lands: {first: 1, count: 10}
  draws: 50
  until: {people: 150, years: 18}
  workers: 10
  players:
    - leader
    - greedy
    - random
    - {mind: linear_v1}
    - {model: qwen2.5:7b, draws: 2, temperature: 0.3}
  params:
    default: {}
    richer-forest: {overrides: {biomes.forest.eras.band.properties.food.base: 1.0}}
  records: 2
```

| Field     | Is                                                              |
|-----------|-----------------------------------------------------------------|
| `lands`   | the seeds of the lands: a first and a count, or a list          |
| `draws`   | the lives played on every land, by every player, under every set of parameters |
| `until`   | a game ends at that many people, or after that many years - a fraction is allowed - or with the band or the seat |
| `workers` | the processes that play                                         |
| `players` | the players of [Players](players.md), each once; a player written as a mapping may ask for fewer draws with `draws`, as a slow model does |
| `params`  | the sets of parameters, each a preset and overrides over the defaults |
| `records` | the full records kept per land, player and set - those of its first draws - for `make replay` |

A deterministic player on one land and draw plays one game, so `draws`
is what gives a mind many games. `random` draws its answers from a
stream of the draw. The file is checked whole before a game is played:
every set of parameters is loaded and every player made under it, so a
wrong path of an override or a mind that does not exist stops the run at
once. `lab/runs/night.yaml` is the example; the local model of the
example above is not built yet.

___

## Run a batch

```bash
make batch RUN=lab/runs/night.yaml
```

The run is played into `lab/<moment>-<name>/`, the run file copied
there as `run.yaml`. The report is written as games end, so a run cut
short still says what it has. A run that is started again with
`make batch RESUME=lab/<moment>-<name>` plays its `run.yaml` again, only
the games the summary does not hold yet.

Every game is played by the runner of the server in step mode, with a
store of its own that keeps nothing past the game. The seat is asked at
every council and its answer is submitted as a vote; a tick with no
council, or with the seat silent, is stepped. A game ends when the band
reaches `until.people` (`reached`), when `until.years` have passed
(`cap`), or when the band dies or the seat is banished. Its record is
written to `DT_RECORDS_DIR` and kept for the first `records` draws; the
header names the player as the kind of the seat, and the draw. The
workers are processes started anew; a run of one worker plays in the
process of the command.

Expected output, a line per finished land, player and set:

```text
night: 10 lands, 50 draws, 4 players, 2 sets: 4000 games, 4000 to play, 10 workers
land 1, leader, default: 50 games, 0 reached 150, growth +4.1%, 5 died in the first year
```

___

## Training a mind

```bash
make train RUN=lab/runs/train-linear.yaml
```

A run file for training names the mind, its features, the lands and
draws it plays, the horizon and the size of a generation:

```yaml
train:
  mind: linear_v2
  from: linear_v1
  features: [go, stay, winter, abstain, votes, leader, score, hunger_food, thirst_water, calm_threat]
  lands: {first: 1, count: 8}
  draws: 4
  until: {people: 150, years: 6}
  population: 16
  generations: 60
  workers: 10
```

Every generation plays each weight set of the population on every land
and draw, scores it by the reward of [Metrics](metrics.md#the-goal) and
moves the population. The best weights so far are written to the
defaults, `content/defaults/minds/<mind>.yaml`, after every generation,
so a night cut short leaves a mind. The state of the search is kept in
`data/` and a training started again goes on from it. The curve -
the best, the mean and the spread of the reward by generation - goes
to `lab/<moment>-train-<mind>/training.txt`.

A horizon of 6 years trains about three times faster than 18; the mind
is then checked on the full 18 years by a batch.

___

## Compare two runs

```bash
make compare A=lab/<moment>-alpha B=lab/<moment>-beta
```

The games of B are matched with those of A by land, draw and player, and
every number of the report is shown as A, B and what moved; heatmaps of
the same land are drawn side by side. The comparison goes to
`compare.txt` in B, so a night of a balance change keeps what it changed.

___

## What a run leaves

```text
lab/
  runs/
    night.yaml
  20261020-0105-night/
    run.yaml          the run file as it was played
    summary.jsonl     a line per game
    report.txt        the tables of Metrics
    heatmaps/         a picture per land, player and set
    analysis.md       written in the morning
```

Everything of a run directory is kept in the repository, the heatmaps
included, and goes into the commit of the change it measured. A heatmap
is one picture of the window in four panes and is small; the full
records are not kept there but in `DT_RECORDS_DIR`, like those of a
played game, and `make replay` opens them.

___

## The morning

Claude reads `report.txt`, the heatmaps and, for the local model, the
`why` of its answers in `summary.jsonl`, and writes `analysis.md`: what
the numbers say, where the land kills, whether the seat's voice matters,
and the changes of balance it proposes, as overrides a next run file can
take. The person decides which go in; the next night plays them on the
same lands, and `make compare` says what they did.

___

## How long a night is

| Work                                   | Takes                         |
|----------------------------------------|-------------------------------|
| a game of 18 years, a mind or scripted | about 45 s of one core        |
| a night of 8 hours, 10 workers         | about 6000 such games         |
| a generation of 16 weights on 32 games | 512 games, about 40 minutes   |
| a generation with a horizon of 6 years | about 13 minutes, 35 a night  |
| a game of the local model              | about 30 minutes, beside the others |

A band that dies early ends early, so a real night plays more. The local
model plays on its own machine, so it costs the batch only the waiting
of the processes that hold its games.

___

## Open points

- **A night on two machines** - the batch plays on one machine. Playing
  on more would split the lands between them and join the summaries.
- **Disk** - a run keeps its pictures. If nights pile up, older runs can
  keep their report and drop their heatmaps once a later run replaced
  them.
- **Speed** - a game of 18 years is 9000 ticks. Making a tick cheaper,
  or skipping the ticks no one asks about, buys more games and more
  generations than any other change here.
