# Metrics

#lab #metrics #stagelab

What a run counts and draws: the goal of the band era as a number, a
line per game, the tables of a report, the heatmaps of a land and the
measures of whether the seat's voice matters. Part of the lab stage in
[the roadmap](../roadmap.md#stage-lab---players-and-statistics); how
runs are played is in [Runs](runs.md).

- [The goal](#the-goal)
- [A game in a line](#a-game-in-a-line)
- [The report](#the-report)
- [Heatmaps](#heatmaps)
- [The land by biome](#the-land-by-biome)
- [Does the voice matter](#does-the-voice-matter)
- [Open points](#open-points)

___

## The goal

The band era is won when the band reaches 150 people, and it should take
15 to 30 minutes of play: about 18 years of the game. Today no reference
band gets there; the best would in about 50 years. Every measure here
leads to that one.

| Measure        | Is                                                              |
|----------------|-----------------------------------------------------------------|
| `reached`      | the share of games that reached 150 within the run's years      |
| `time`         | the median day those games reached it                           |
| `growth`       | the yearly growth of the others, compounded, as the lives do    |
| `projected`    | the year 150 would be reached at that growth                    |
| `early`        | the share of bands dead in their first year                     |
| `lost`         | the share of games that ended with the band dead or the seat banished |

The reward a mind is trained by is the same goal in one number:

```text
reward = 1 + (horizon - day reached) / horizon      when 150 was reached
       = log(people at the end / start) / log(150 / start), within -1 and 1, otherwise
       = -1                                        when the band died or the seat was banished
```

The weights are a first guess, tuned in the first nights of training.

___

## A game in a line

Every game is a line of `summary.jsonl`, written when it ends.

| Field        | Holds                                                          |
|--------------|----------------------------------------------------------------|
| `land`, `draw`, `player`, `set` | which game it was                           |
| `outcome`    | `reached`, `died`, `banished` or `cap`                         |
| `day`        | the day it ended                                               |
| `people`     | at the start, at the end and at most                           |
| `born`, `died` | in all, and the deaths by cause                              |
| `councils`   | that sat, settled, backed, turned, outvoted, abstained         |
| `verdicts`   | worked, even, failed                                           |
| `status`     | at the end and at its lowest                                   |
| `skills`     | the day each skill was learned                                 |
| `why`        | for the local model, its answers in words, by council          |
| `seconds`    | how long the game took                                         |

___

## The report

`report.txt` holds a table per set of parameters, a row per player, and
the same per land, so a land that kills every player stands out. The
numbers below show the shape of the table only; no run has made them.

```text
default          games  reached  time  growth  projected  early  lost  turned  worked
leader             1000     0.0%     -   +4.2%       52    9.8%  31%      0%       -
greedy             1000     0.4%  6120   +5.1%       44    9.1%  28%     23%     61%
linear_v1          1000     2.1%  5480   +6.3%       37    8.7%  24%     18%     68%
qwen2.5:7b           20     0.0%     -   +4.9%       46   10.0%  30%     27%     55%
```

The skills learned, the causes of death and the occasions of the
councils follow as tables of their own, a share of the games each.

___

## Heatmaps

A heatmap is drawn per land, player and set: the window of the land, its
biomes dimmed, and over it four panes of what the games did on every
cell, summed over the draws.

| Pane        | Counts on a cell                                           |
|-------------|------------------------------------------------------------|
| `walked`    | the ticks a band stood or walked on it                     |
| `camped`    | the ticks it camped there, a winter camp marked apart      |
| `starved`   | the ticks it spent there in starvation or thirst           |
| `died`      | the people who died there, by any cause                    |

Every pane runs from no colour to full on a scale of its own, written on
it, so a land played by two players compares by eye. The pictures are
small and are kept in the repository with the run.

___

## The land by biome

Lands differ, so heatmaps do not add up across them. What adds up is the
biome: over all lands, the share of the band's time spent in each biome,
the people who died there per thousand days lived there, and the starving
ticks per hundred days there. A biome that is visited and kills is a
biome to look at.

___

## Does the voice matter

The seat is worth playing only if a player can do better than backing
the leader. Three measures say whether it can.

| Measure    | Is                                                              |
|------------|-----------------------------------------------------------------|
| `turned`   | the share of councils a player carried against the leader       |
| `worked`   | the share of those turns judged `worked`                        |
| `gain`     | the `reached` and `growth` of a player less those of `leader` on the same games |

A gain of nothing for every player, a mind trained for it included,
means the council decides nothing, whatever the numbers of the band.

___

## Open points

- **The reward** - its parts and weights are a first guess; a mind that
  learns to survive without growing would show the reward is wrong.
- **Fairness of the land** - whether every land should be able to reach
  150, or some are meant to be lost, is decided by the person reading the
  reports, not here.
