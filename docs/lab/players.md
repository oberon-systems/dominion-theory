# Players

#lab #players #stagelab

Who can sit in the player's seat besides a person, and how each of them
sees the game and answers: a mind of a few weights trained here, a local
language model on a machine of its own, and Claude through an MCP
server. Part of the lab stage in
[the roadmap](../roadmap.md#stage-lab---players-and-statistics); how
they are run in numbers is in [Runs](runs.md), what is measured in
[Metrics](metrics.md). Every number here is data and a first guess.

- [One seat, three players](#one-seat-three-players)
- [What a seat sees](#what-a-seat-sees)
- [The answer](#the-answer)
- [Scripted players](#scripted-players)
- [The mind](#the-mind)
- [The local model](#the-local-model)
- [Claude](#claude)
- [A mind for the bots](#a-mind-for-the-bots)
- [Packages](#packages)
- [Parameters](#parameters)
- [Open points](#open-points)

___

## One seat, three players

The seat is the one place a game is played from, as
[the overview](../architecture/overview.md#seats) says: whoever holds it
sees the same observation and sends the same command. Three players are
built for it, and each has its own use.

| Player          | Runs                           | Is for                                              |
|-----------------|--------------------------------|-----------------------------------------------------|
| a mind          | in process, on the CPU         | thousands of games a night: the numbers of balance; later the voice of the bots |
| the local model | over HTTP, on a GPU elsewhere  | a reasonable player in words, tens of games a night |
| Claude          | an MCP server over the API     | games played and read by the assistant, the analysis in the morning |

Nothing of the three is needed for the others. A night of runs needs
neither Claude nor anybody at the keyboard; Claude reads what the night
left. Every player sees only what the seat sees: no stock of a cell, no
reason of the band's decision, nothing `--debug` adds.

A player is asked only when a council sits and waits for the seat. Every
other tick is passed, so the cost of a player is its councils: about 33
a year in the games played so far, about 550 in 18 years.

___

## What a seat sees

The observation is built once, from the game, and given in two forms:
numbers for a mind, text for a language model. Both say the same.

| Part       | Holds                                                          |
|------------|----------------------------------------------------------------|
| the date   | year, month, day, part of the day, season                      |
| the band   | people by stage, pregnant, injured, sick; states; fatigue; the days of food and of water held; the skills; the goods and the kits |
| the seat   | status, the voice it gives, the occasion that called the council |
| the table  | every option: its kind, its words, its votes, whether it leads, the band's score of it, and its place |
| a place    | the cell as the band knows it: biome, food, water, threat, passability, a river, whether it is unknown; how far and by how long a route |
| the land   | the cells the band knows around it, as the map of the API gives them |
| the story  | what happened since the last council, as the lines of the log  |

The engine builds the numbers, `engine/observation.py`, while a council
waits for the seat. The band's score of an option is the one its votes
were laid by: the council keeps it in its table when it sits, beside the
occasion, and the API shows both. A place is read as the band reads a
go: a known cell with its shores and dread, land it does not know as it
expects such land, and the route as the band would lay it. The land and
the story are of the text, built in `lab`.

The numbers of an option are its features, the same list for every
option, and each feature is a name, so a mind says what it weighs:

| Feature             | Is                                                          |
|---------------------|-------------------------------------------------------------|
| `go`, `stay`, `winter`, `abstain` | 1 for the kind of the option, else 0          |
| `votes`             | its votes over the voters                                   |
| `leader`            | 1 when it leads the table                                   |
| `score`             | the band's own score of it                                  |
| `hunger_food`       | hunger times the food of its place                          |
| `thirst_water`      | thirst times the water of its place                         |
| `calm_threat`       | calm times the threat of its place                          |
| `river`             | 1 when its place has a river                                |
| `unknown`           | 1 when its place is land the band does not know             |
| `distance`          | the cells of its route over the sight of the band; 0 where it stands or knows no way |
| `winter_short`      | for a winter camp, the share of its seasons left, the autumn and the winter as one, 1 before they begin |
| `short_stay`        | for a stay, 1 when the days of food or water are below a day |
| `outvoted`          | for an option not leading, abstaining aside, the share of the leader's votes the seat's voice lacks |

The features of the band alone, the same for every option, would change
no choice, so they enter only through these products. A mind names the
features it uses, see [The mind](#the-mind); a new feature is a function
of the engine and a name in a mind.

The text says the same in lines a person reads, in English or Russian:

```text
Day 14, month 3, year 2, spring, the evening. Your standing is 52.
The band: 21 people - 4 children, 15 adults, 2 elders; 1 with child.
Food for 1.4 days, water for 2.1 days. Fatigue 0.3. Knows: orientation, sticks.
The council sits: the band has seen a river.
1. Stay and gather here (leads, 9 votes of 18): forest, food 0.9, water 0.6, threat 0.4.
2. Go into the forest by the river, near (5 votes): 3 cells north-east, food 0.9, water 1.0.
3. Go onto the meadows, far (4 votes): 7 cells south, food 0.8, water 0.4, threat 0.1.
0. Say nothing.
Since the last council: 2 children were born. 1 person died of an encounter.
```

___

## The answer

Every player answers with a number of the table: an option, or 0 for
silence. The options are numbered from 1 in the order of the council's
table, and abstaining is the last of them, so a player may abstain as a
person does. The seat turns it into the command `vote`, so the game sees no
difference between the players and a person. A place of the player's
own, which a person may point, is not offered to the players of the lab:
it would let a model wander the whole window, and the options already
hold the land the band can name.

An answer that names no option is silence. It is counted, as the
roadmap asks, so a weak model shows in the numbers instead of stalling
a run. Every answer is a command of the record, so a game is replayed
without the player that played it.

___

## Scripted players

Three players of a few lines, the floor every other is measured against.

| Player   | Answers                                                    |
|----------|------------------------------------------------------------|
| `leader` | the option that leads, which costs nothing and turns nothing |
| `silent` | nothing, every time                                        |
| `random` | an option drawn from a stream of its own, silence among them |
| `greedy` | the option with the best score of the band                 |

`leader` is the yardstick of the seat: if no player does better than
backing the leader, the player's voice decides nothing, and that is a
finding about the game, not about the player.

___

## The mind

A mind scores every option of the table and answers with the best:

```text
score of an option = sum of weight[feature] * feature, over the features of the mind
answer             = the option with the highest score; a tie goes to the order of the table
```

A mind is data: a file of the defaults under `minds`,
`content/defaults/minds/<mind>.yaml`, one per mind, holding its features
and their weights; a mind's name is lower case with `_`. The first,
`linear_v0`, is set by hand, not trained: it backs the band's own score,
the leader on a near tie, and never abstains. So a mind is part of the tree of
parameters, its hash is part of the record, and a game played by a mind
replays exactly.

```yaml
minds:
  linear_v1:
    features: [go, stay, winter, abstain, votes, leader, score, hunger_food, thirst_water, calm_threat]
    weights: [0.1, 0.2, 0.0, -1.0, 0.5, 0.3, 1.0, 0.8, 0.6, -0.7]
    trained: {run: 20261020-train, generations: 48, reward: 0.31}
```

A mind is trained by [Runs](runs.md#training-a-mind), with no gradient:
a population of weights plays the same lands, the better half pulls the
next generation towards it
([CMA-ES](https://en.wikipedia.org/wiki/CMA-ES)). The reward is the goal
of the era, see [Metrics](metrics.md#the-goal). The weights stay
readable: a large weight on `leader` says the mind learned to follow, a
negative one on `calm_threat` that it fears danger.

A small network in place of the sum is the next step only if a linear
mind stops improving; it would score an option the same way, from the
same features.

___

## The local model

A language model on a machine of its own answers the text. It is reached
over HTTP at any server that speaks the chat API of OpenAI - Ollama,
llama.cpp, LM Studio, vLLM - named by settings, not by code.

| Setting              | Is                                         | Default |
|----------------------|--------------------------------------------|---------|
| `DT_LLM_URL`         | the base address of the chat API          | none    |
| `DT_LLM_MODEL`       | the model the server names                 | none    |
| `DT_LLM_TIMEOUT_S`   | seconds to wait for one answer             | 120     |

The model is given the rules in short, the text of the council and the
form of its answer, and asked for JSON: `{"choice": 2, "why": "..."}`,
with the server's structured output where it has one. `why` is kept in
the summary of the game and is the reason a model is worth running at
all: it says what a reasonable player made of the table. The
temperature, the length of the answer and the words of the rules are
parameters of the player in the run, not of the game.

A model of 7 to 8 billion weights in 4 bits fits a GPU of 6 GB; one of 3
to 4 billion leaves room for other work on it. An answer takes some
seconds, a game of 18 years half an hour, so a night gives tens of
games: few, beside the thousands of a mind, and read for their words.

___

## Claude

Claude plays through an MCP server, `dominion`, over stdio, written
with the Python SDK `mcp` in `lab/dominion.py`. The server is a client of
the API, as the console client is: it starts a server of the game of its
own on a free port, as `make play` does, logging into
`data/mcp-server.log`, or plays on the one `--server` names. Its games
are in step mode with the seat taken, one at a time. The tools:

| Tool         | Does                                                             |
|--------------|------------------------------------------------------------------|
| `new_game`   | a new game, by seed and preset, in English or Russian; the game played before ends |
| `look`       | the text of the seat: the date, the standing, the band, its fatigue and intent, the map of the land it knows, whether a council waits, the story since the last look |
| `council`    | the table numbered: every option with its place, votes and the band's score, abstaining after them, 0 for silence |
| `vote`       | the answer by its number; gives the story of the tick it closes  |
| `advance`    | passes until a council waits for the seat, or until the days given have begun, at most 100; gives the story |
| `panes`      | the people by stage, condition and role, the skills, the stores  |
| `end`        | ends the game; its record is the one `make replay` plays         |

The text is built in `lab/sitting.py` from what the API gives the seat
and the catalogues, in English or Russian: the band and its stores as
the console client says them, the map as the console client draws it,
without colour, and the place of an option as the band knows it - its
biome, food, water, threat, passability and a river. The story leaves
out what every tick of step mode carries, the passes accepted and the
days begun.

The server is registered in `.mcp.json` of the working copy, which git
ignores, beside the servers already there; `command` is the Python of
the virtualenv, run from the root of the working copy:

```json
{
  "mcpServers": {
    "dominion": {
      "type": "stdio",
      "command": ".venv/bin/python",
      "args": ["-m", "dominion_theory.lab.dominion"]
    }
  }
}
```

Claude reads the morning's results as files - the report, the summary,
the heatmaps - and needs no tool for it; see
[Runs](runs.md#the-morning).

___

## A mind for the bots

The bands of stage 3 are not seats: the engine runs them. A mind is
built so that one can be their voice. It is data of the tree, its score
is a sum with no draw, and its features come from what the band knows,
so the engine can ask it inside a tick and the game stays deterministic.
The scoring and the features therefore live in the engine; the seat's
player only wraps them. Which band hears which mind is a question of
stage 3.

___

## Packages

| Package   | Holds, in this stage                                         | May import                     |
|-----------|--------------------------------------------------------------|--------------------------------|
| `engine`  | the observation as numbers, the features, a mind's score     | as before                      |
| `players` | the seat's contract; `leader`, `silent`, `random`, `greedy`; the mind as a player | `engine`, `content` |
| `lab`     | runs and training in process, summaries, reports, heatmaps, compare; the local model's player; the MCP server | `players`, `runner`, `content`, `i18n`, `client` |

The text of an observation is built from the numbers with the catalogues,
in `lab`, so the engine still produces no words. `lab` reads `content`
to check the sets of parameters of a run file before a game is played,
and the tally of a game, which counts events of the engine, lives in
`runner`. The MCP server reaches the game through the API with the calls,
the session and the lines of `client`. The table of
[the overview](../architecture/overview.md#packages) and the test of the
imports follow it.

___

## Parameters

```yaml
minds:
  linear_v1:
    features: [...]
    weights: [...]
    trained: {run: ..., generations: ..., reward: ...}
```

A mind's weights are as many as its features, every feature is a name
the engine knows, and `trained` is free text kept for the reader. The
settings of the local model are of the server, not the game.

___

## Open points

- **A place of the player's own** - a mind and a model answer only the
  options of the table. A player that may point at any cell would need a
  feature of every cell, a different kind of mind.
- **A network** - built only if a linear mind stops improving.
- **The bots' minds** - which band hears which mind, and whether a mind
  learns from playing bands as well, is stage 3.
- **Prompting** - the words of the rules for the model are tuned by
  reading its `why`; whether a model plays better with the log of the
  whole game or only since the last council is measured, not guessed.
