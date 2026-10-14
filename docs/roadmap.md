# Roadmap

#roadmap #dev

The ordered list of development stages, from repository cleanup up to the
first era transition. Each stage says what is built, how it is built, which
documents it produces and what "done" means.

- [How a stage is worked](#how-a-stage-is-worked)
- [Target architecture](#target-architecture)
- [Decisions](#decisions)
- [Stage pre - repository](#stage-pre---repository)
- [Stage 0 - API and core](#stage-0---api-and-core)
- [Stage 1 - biomes](#stage-1---biomes)
- [Stage 2 - band](#stage-2---band)
- [Stage 3 - bots](#stage-3---bots)
- [Stage lab - LLM players and statistics](#stage-lab---llm-players-and-statistics)
- [Stage 4 - web](#stage-4---web)
- [Stage 5 - era transition](#stage-5---era-transition)
- [World scale](#world-scale)
- [Later](#later)
- [Open questions](#open-questions)

___

## How a stage is worked

Every stage goes through the same five steps, and the next stage does not
start before the current one is closed.

1. **Design docs** - the documents listed under the stage are written first
   and agreed. They describe rules and numbers, not code.
2. **Plan** - the agreed design becomes a plan with a file set and a
   definition of done.
3. **Implementation** - code is written against the plan only.
4. **Verification** - tests and linters are run, on request.
5. **Docs refresh** - the documents are corrected to match what was built.

___

## Target architecture

The game is a server-side simulation with thin clients. Nothing in the
simulation knows how it is displayed.

```text
+-----------+     +-----------+
| web client|     |unity (opt)|
+-----+-----+     +-----+-----+
      |  HTTP + WebSocket, JSON, versioned schema
+-----+-----------------+-----+
|            api              |  sessions, commands in, state out
+--------------+--------------+
|            engine           |  tick loop, world state, rules, bots
+--------------+--------------+
|  biomes | units | eras      |  game content, declared as data
+-----------------------------+
```

- **engine** - pure Python, no I/O, no rendering. Deterministic: the same
  seed and the same commands give the same state.
- **api** - the only way in or out. Clients send commands and receive
  snapshots and per-tick events.
- **content** - biomes, units, resources and eras are data with a
  registry, so a new one is added without touching the engine.
- **clients** - draw state and send the player's will. They hold no rules.

___

## Decisions

What is already settled and binds every stage.

- **Biome** is the word for a kind of land. "Terrain" is not used.
- **A turn is a tick.** The tick is the only step the engine knows.
- **A day is exactly five ticks in era 0.** A tick stands for about five
  hours, but rules never count hours: every rate is given per tick or per
  day.
- **The game time in a tick belongs to the era.** A band lives in fifths of
  a day; later eras may step by a day or a season.
- **The length of a tick in real time is a server setting**, 500 ms by
  default. It sets the speed of play and never changes the outcome.
- **The calendar is short and configurable.** The default is ten days in a
  month and ten months in a year: 500 ticks, about four minutes at the
  default speed.
- **Demography is accelerated and configurable**, tuned to the short year
  rather than to real growth rates.
- **Every balance number is a parameter**, set per game, so that a run can
  be repeated with one value changed.
- **A game can be played by a program**, a local LLM included, and every
  run can be measured. This is built in from stage 0, not added later.
- **There is no headman.** A band of foraging nomads is run by a council,
  and the player is one voice in it. The weight of that voice is the
  player's status: decisions that end in hunger or loss lower it, and a
  player whose status is gone is banished, which ends the game.
- **A band acts on its own, and the council meets every morning.** The
  others put their votes on what the band could do, the player sees how
  they lie and backs an option, proposes another or does not vote, which
  costs status. Status moves only with what the player changed.
- **A proposal is said the way a nomad would say it**: "we go where the sun
  rises", "we follow the pole star", "we rest here", "we stay, we are
  short of food".
- **A proposal the player carried is judged by what follows**, at the
  next council. If it worked out, status rises; if not, it falls; if it
  ended in disaster, a large loss of people, it falls hard. Backing what
  the band would have done anyway moves nothing.
- **A long rest always raises status** and makes the band grow, but nobody
  gathers, so food and water run down.
- **Staying to gather raises status**, unless a chance encounter, a bear
  for one, takes people.
- **The council meets once a day**, decided by the user on 2026-10-14 in
  place of a council called by the player with a gap between two. The
  others' votes lie by how good each option looks to the band; the
  player's voice always weighs more than one, and more with status. A
  player outvoted pays a little, a player who does not vote pays more.
- **A meeting with another band is an emergency council**, outside the
  morning: attack, ally or ignore. It is designed with stage 3.
- **A proposal is judged by supplies and people**: the days of food and
  water in the stores at the call and at the close of the window, and
  the share of people lost. A fifth of the band lost is a disaster.
- **A band gathers on its own cell only.** The shallows can be entered
  at the very shore, where water and food are plenty and the threat is
  high; a river gives more water; the water of a swamp may poison.
- **A season changes food, water and movement** through modifiers of the
  biome, and winter slows what grows back. Frost comes later.
- **Every amount and every window here is a parameter.**
- **The game speaks English and Russian from the start.** The engine never
  produces text: it names a message by a key and gives its values, and the
  words come from a catalogue per language. Documentation and code stay in
  English.
- **Everybody starts as a band**, the player and every other people alike.
- **The game is not about humanity.** Its peoples are invented races, not
  humans, and nothing in the rules or the words assumes they are.
- **Balance is tuned once the band era is whole**, decided by the user on
  2026-10-14: bands with encounters between them, skills, seasons,
  weather, and a seat an assistant can play through an MCP server. Until
  then the numbers stay first guesses, and the references only show that
  they moved.
- **Other peoples are simulated by a simplified model.** A map holds the
  player and five to ten other bands; when one of them dies, a new one is
  spawned. When the player becomes a tribe, some of the bands, chosen at
  random and preferably far from the player, are raised to tribes too.
- **An LLM plays as a person does**: it takes the player's seat in the
  council. It does not replace the band's own decisions.
- **Weather and seasons are coming.** Nothing is built for them yet, but
  the calendar, the climate of the planet and the properties of a biome
  are shaped so that they can change through the year.
- **The year has four seasons**: spring two months, summer three, autumn
  two, winter three, on the year of ten months. The lengths are
  parameters, and later a season may come early or run long.
- **A biome is data with a generation rule**: ranges over elevation,
  relief, moisture, temperature and flow that must all hold, and an order; the
  first biome by order takes the cell. A new biome is a data file, its
  name in both catalogues, a document and a test.
- **The starting biomes are fifteen**: grass, forest, hills, mountain,
  outcrops, water, shallows, desert, tundra, swamp, floodplain, marsh,
  dunes, snow and ice.
- **A threshold of generation is a share of the planet**, not a number of
  the noise: the sea is the share of the planet under water, and a height
  is the share of land lying lower.
- **A river is a line and a mark**, not a biome: it is traced by flow from
  its source on a divide down to the sea, through the lakes on its way, a cell it crosses keeps its biome, can be crossed and gets
  the river's modifiers.
- **A property is a base with modifiers**: what is added first, what
  multiplies after, held between 0 and 1, worked out when asked and stored
  nowhere. A season, a river and the state of a cell are modifiers.
- **A cell remembers a stock per property that recovers**, and only cells
  that were touched are kept.
- **One person per game.** Multiplayer comes much later; nothing is built
  for it now.
- **A running game lives in a key-value store**, not in the database:
  an in-process fake by default, a [Valkey](https://valkey.io/) server
  when one is configured.
- **Profiles and other lasting records live in a relational database**
  through [SQLModel](https://sqlmodel.tiangolo.com/), tied to no engine:
  SQLite by default and for everything local, PostgreSQL when configured.
- **A tribe forms in two ways**: a band grows to the threshold, or bands
  merge.

___

## Stage pre - repository

Bring the repository to the shape the neighbouring projects have.

**What:**

- A root `Makefile`: `install` creates the virtualenv, installs the tooling
  and wires the git hooks; a bare `make` opens a subshell with the
  virtualenv active; `help`, `lint`, `test`.
- Git hooks installed and passing. The hook list is cut down to what is
  needed now: mypy, flake8, ruff, black, a Markdown linter that needs no
  Node, and the wyld-cz commit message check. Everything else is removed.
- Python 3.14 as the supported version, with no upper bound.
- Dependencies declared in `pyproject.toml`, runtime and development apart.
- A test runner and one smoke test for the map generator.
- Dependabot configured for the Python dependencies and the workflows.
- The untracked sketches (`tribes`, `units`, `resources`) removed, so the
  tree is clean before stage 0.
- `README.md` rewritten as a project description with a quick start.
- Existing docs fixed: typos, broken links, lint errors.

**How:**

- The Makefile holds every command in full, no wrapper scripts.
- Hook environments live in the repository, not in the home directory.

**Docs**: `README.md`, `docs/dev/setup.md` (SOP: install, lint, test, run).

**Done**: a fresh clone reaches a passing `make lint` and `make test` with
`make install` alone.

___

## Stage 0 - API and core

The skeleton everything else hangs on.

**What:**

- The `engine` package: world state, the tick loop, the command queue, the
  event log, a seeded random source owned by the game.
- The time model: tick, day, month, year, and the scale of a tick per era.
- The parameter set of a game: one tree of named values with defaults,
  overridden when a game is created and stored with it.
- Two clocks: real time, where a tick fires every N milliseconds, and step
  mode, where the game waits until every player has answered. Step mode is
  what a slow player such as an LLM needs, and what a fast batch run needs.
- The run record: seed, parameters, every command and a row of counters
  per tick, enough to replay a game and to compare two of them.
- State serialisation: a full snapshot and per-tick changes.
- The game store: the state of a running game behind one interface, with
  the in-process fake and Valkey as its two backends.
- The database layer: the player's profile as the first table, SQLite by
  default, the connection string as the only thing that picks the engine.
- Localisation: message keys with values in every event and every name the
  game shows, catalogues for English and Russian, the language kept in the
  player's profile.
- The `api` package: create a game, read a snapshot, send a command,
  subscribe to the stream of updates.
- A versioned message schema that a client in any language can be built
  from.

**How:**

- The engine is a library first. A headless run from a test or the command
  line needs no server.
- Request and response over HTTP, the update stream over WebSocket, JSON in
  both. Proposed stack: FastAPI, pydantic, uvicorn; SQLModel for the
  database; fakeredis and a Valkey client for the game store.
- Tables are plain: no foreign keys, no cascades, a new feature in a new
  table. Tests and smoke runs use SQLite and the fake store only.
- Coordinates, identifiers and enumerations are fixed here, since every
  later stage and every client depends on them.
- The existing map generator moves under the engine unchanged; pygame stays
  only as a developer tool until stage 4 replaces it.

- A player is a seat in a game, and whoever holds it - a person in a
  client, a bot, an LLM - sees the same observation and sends the same
  commands.
- A test fails when a key is missing from one of the catalogues, so a
  stage cannot add a string in one language only.
- Russian counts people in three forms, so the catalogue format has to
  know plurals. The format is [Fluent](https://projectfluent.org/), which
  has them and has free libraries for Python and for the browser.

**Docs**: `docs/architecture/overview.md`, `docs/architecture/time.md`,
`docs/architecture/parameters.md`, `docs/architecture/records.md`,
`docs/architecture/storage.md`, `docs/architecture/localisation.md`,
`docs/api/protocol.md` (messages, with examples), `docs/api/commands.md`.

**Done**: a game is created over the API, advances by ticks, and a
WebSocket client prints the events. A test proves that two runs with the
same seed end in the same state.

___

## Stage 1 - biomes

The starting biome types, built so that more can be added later.

**What:**

- A biome registry instead of four hard-coded fields.
- A biome is declared as data: identifier, generation rule, colour,
  properties, collectible resources.
- Properties are keyed by era: each era opens its own set of properties on
  the same biome. Era 0 has `water`, `food`, `threat`, `passability`.
- The starting set: grass, forest, hills, mountain, rocky outcrops, water,
  with rivers as lines across them. Desert and tundra joined it in the
  design, because a whole planet has dry and cold land; swamp was added
  last, to close the stage.
- The planet: the skeleton of continents and climate, the window of the
  band era on it, and the rule that picks a habitable place for it.
- A property is a base value with modifiers on top, so that a season or
  the weather can later change it without a new data model.
- Cell state apart from biome type: a cell is depleted by gathering and
  recovers over time.
- The map is served through the API.

**How:**

- Biome definitions are frozen at start; only cell state changes at run
  time.
- Generator defects are fixed here: mountains sit on mid elevations, rivers
  ignore the seed and always run down the screen, the default seed is fixed
  at import time.

**Docs**: `docs/biomes/overview.md` (model, how to add one), one file per
biome, `docs/biomes/generation.md`. `docs/biomes.md` is folded in.

**Done**: a fifth biome is added by one data file and one test. The same
seed gives the same map, rivers included.

The stage is closed. Swamp was the proof: it arrived by its data file,
its name in two catalogues, its document and one test, and eight more
biomes followed the same way. Looking at drawn maps widened the stage:
mountain ranges, lakes, rivers with beds and deltas, a climate, the count
of continents and presets for other planets were built in it. The numbers
were tuned on maps drawn by the developer tool; see
[Setup](dev/setup.md#look-at-a-map).

___

## Stage 2 - band

The first unit, and the rules of indirect control.

**What:**

- Band properties: population, speed, carrying capacity, gathering and
  consumption rates, stored resources with weight and expiration.
- States: `normal`, `starvation`, `thirst`, `tiredness`, with what triggers
  each, what it does and how it ends.
- Actions: `move`, `gather`, `camp`. The turn of five actions.
- How a band decides: needs are scored against what it knows about the
  cells around it, and the best action wins.
- Movement: eight directions, no water, no occupied cell, cost from
  passability and band size.
- Population growth and loss.
- Indirect control: a council every morning. The others' votes are laid
  out over the options - to move in a direction, to rest, to stay and
  gather - and the player backs one, proposes another or abstains. How
  the vote goes, how what the player carried is judged and moves status,
  what abstaining costs, banishment at zero.
- Chance encounters, driven by the threat of the biome.

**How:**

- The decision function is the same for the player's band and for bots. The
  player only adds proposals on top.
- Every number lives in data, not in code, so balance is tuned without
  edits to the engine.
- The design docs settled the contradictions of the old notes: the rates
  of gathering and consumption on the five-tick day, the vote, the
  judgement, the seasons. What they left is under
  [Open questions](#open-questions) and in their own open points.

**Docs**: `docs/units/band.md` (rewritten), `docs/game/01_bands.md`
(rewritten), `docs/game/indirect_control.md`, `docs/game/decisions.md`,
`docs/values/` kept current.

**Done**: one band lives on a map headless for a long run: it moves, gathers,
camps, starves when it should. A proposal made over the API changes what
the band does, and the outcome moves the player's status.

___

## Stage 3 - bots

Other bands on the same map: rivals or allies.

**What:**

- Several bands in one game, each run by the stage 2 decision function:
  five to ten beside the player, with a new one spawned when one dies.
- Temperaments: sets of weights that make bands behave differently.
- What bands know about each other and when they notice one another.
- Relations: neutral, rival, ally, and what moves a band between them.
- Interaction: competing for a depleted cell, avoiding, following, and
  whichever of conflict, exchange and merging the design doc keeps.
- A meeting of two bands is an emergency council at once, whatever the
  part of the day: attack, ally or ignore. Ignoring may still be answered
  by an attack.
- A band's own threat: every band carries a level of how dangerous it is
  known to be. Attacking raises it, allying and ignoring lower it; what
  other bands do on a meeting follows from it and from their temperament.
  A band with a low threat that meets an aggressive one is attacked.
- An attack is decided by strength: the people who can fight, so a band
  of many children and elders is weaker and a poor target to provoke;
  dogs, once they exist, add to it. The attacked band flees and loses
  people and stores, or stands and may be destroyed.
- A band that wins may carry off young or females, and two bands may
  merge. Every band is of one race until races are added at the end; then
  offspring may take traits of the other race, as far as the two races
  are compatible, and races that cannot mix attack each other more often;
  see [Races](#races).

**How:**

- A bot has no private access to the engine: it produces the same commands
  a client would send.
- Bots are stepped inside the tick, in a fixed order, from the game's own
  random source, so a run stays reproducible.

**Docs**: `docs/game/bots.md`, `docs/game/relations.md`,
`docs/game/indirect_control.md` (the emergency council).

**Done**: a headless game with many bands runs a long session without
errors, and a summary shows that temperaments give different outcomes.

___

## Stage lab - LLM players and statistics

A bench where programs play the game and the numbers are measured, used to
design and tune every later stage.

**What:**

- An LLM player: it takes a seat, receives the observation as text, and
  answers with one of the commands on offer.
- An MCP server over the API, so that an assistant such as Claude can sit
  in the player's seat: read the band, the table of the council and the
  map it knows, and vote. It is how the band era is played for balance.
- A runner: many games in step mode from one description - seeds, player
  kinds, parameter overrides.
- Statistics over run records: survival time, population curves, how often
  each state and action occurs, status over time, time to the era
  transition.
- Heatmaps over the map: where bands walk, gather, camp, starve and die.
- A comparison of two parameter sets on the same seeds.

**How:**

- The LLM player is an ordinary API client and lives outside the engine.
  It talks to a local model server over a chat endpoint, with the address
  and the model name in its own settings.
- An answer that is not a valid command is counted and replaced by "no
  command", so a weak model cannot stall or break a run.
- Runs are reproducible on the engine side: the record keeps the commands,
  so a game is replayed without the model.
- The LLM plays a council member, as a person would: it sees what a client
  shows and raises its voice. The band's own decisions stay with the
  engine.

**Docs**: `docs/lab/llm_player.md`, `docs/lab/runs.md` (SOP: describe a
batch, run it, read the result), `docs/lab/metrics.md`, `docs/lab/mcp.md`.

**Done**: one command runs a batch of games with LLM and scripted players
and prints a table that compares two parameter sets, and an assistant plays
a game through the MCP server.

___

## Stage 4 - web

A browser client to watch the game, bots only at first.

**What:**

- The map drawn from the API, with pan and zoom.
- Bands on the map, with an inspector: population, state, resources, last
  decision and why it was taken.
- Time controls: pause, step, speed.
- An event log.
- Overlays for biome properties, replacing the pygame tools.
- After spectating works: the player's band and the council controls.

**How:**

- The client talks to the stage 0 API only. Anything it needs and cannot
  get is added to the protocol, not worked around.
- The framework and the rendering approach are chosen in the design doc.
  The default proposal is TypeScript and a canvas, served as static files.
- pygame leaves the dependencies when the overlays are ported.

**Docs**: `docs/web/client.md`, `docs/dev/setup.md` extended with the client.

**Done**: `make run` starts the server and the client, and a game of bots is
watched in the browser from start to extinction or transition.

___

## Stage 5 - era transition

A band gathers population and becomes a tribe.

**What:**

- The era model: what an era is, what a unit carries across a transition,
  what an era unlocks - biome properties, actions, resources.
- The transition condition for era 0, by both paths: a band grows to the
  threshold, 150 people in the notes, or bands merge into one.
- The tribe as a unit: a minimal set of properties, enough to exist on the
  map after the transition.
- What happens to the council and the player's status.
- The other peoples: which bands are raised to tribes with the player, how
  far from the player they have to be, and who is placed on the land that
  comes into view.
- The zoom of the map, as described under [World scale](#world-scale).

**How:**

- The transition is a generic mechanism, not a special case of the band, so
  settlements, cities and states reuse it.
- Stage 1 already keys biome properties by era; this stage adds the
  second key and proves the design.

**Docs**: `docs/game/eras.md`, `docs/game/02_tribes.md`,
`docs/units/tribe.md`.

**Done**: a band that meets the condition becomes a tribe in a running
game, the client shows it, and the biome under it exposes era 1
properties.

___

## World scale

How the map relates to the world, and how it changes from era to era.

- **There is one world map, and an era shows a piece of it.** A planet is
  generated once from the seed: a skeleton of continents, oceans and
  climate first, detail on top. The map of the band era is a small region
  of it.
- **Each era zooms out.** A cell covers more land and the map takes in
  more of the planet. As an illustration only: a field of 5 by 5 cells of
  10 km becomes one cell of 50 km when a band turns into a tribe, since
  herding makes 10 km nothing. Every number here is a parameter.
- **The first step is from 10 km to 50 km**, five cells to a side. Later
  steps are set when the mechanics of those eras are known.
- **The camera pulls back and other peoples come into view**, if there are
  any within the new window.
- **Space and time grow together.** A longer tick and a larger cell keep
  movement near one cell per tick in every era.
- **A coarse cell is built from the fine cells it covers**: the dominant
  biome, averaged properties and state. Land that was never played is
  sampled from the planet at the new cell size.
- **The planet is a continuous function** of the seed and planet
  coordinates, so any window at any cell size can be produced, and rivers
  are lines on the planet rather than chains of cells.
- **The shape and the climate of a planet are parameters.** The count of
  continents, two by default, the belts of moisture by latitude, how dry
  land gets inland and how warm the planet is are numbers of the tree,
  and a preset makes another planet of them: one continent, several,
  islands only, a desert world.
- **The world is as close to a planet as it can be**: it wraps from east to
  west, and latitude drives temperature. It is a cylinder, not a sphere:
  every row is as long as the equator.
- **The planet is 40000 km around and 20000 km from pole to pole**, 4000
  by 2000 cells of the band era. A skeleton with a node every 100 km is
  worked out once per game for what needs the whole planet: the sea
  level, the shares, the rivers. It is not part of the state.
- **The first window is habitable**: forest, hills, a river, some rocky
  outcrops. It is 512 by 256 cells, placed in the temperate north by
  tries drawn from the seed, or by hand.
- **In a single-player game the player's transition moves the era.**
- **Layers, for multiplayer later.** The fine map is kept as a layer below
  the coarse one, and what happens above is merged down onto it. A tribe
  plays on the larger map and acts with more force; it does not see the
  bands below. The bands go on growing in the same world, and they do see
  the tribe and what it does.

___

## Later

Wanted, agreed and on no stage yet, raised by the user on 2026-10-14. Each
gets its design doc before it is placed. Every number is data, as
everywhere.

### Ages in a band

A band counts young, adults and elders, and males and females, instead
of heads alone.

- They are born young, grow into adults and age into elders by the
  calendar; elders die faster.
- The young and elders eat and drink less than adults.
- The young and elders slow the band: speed falls with their share.
- Only adults fight: a band of many young and elders is weaker in the
  conflicts of stage 3.
- Females and the young are what a winning band may carry off, and what
  carries a race into the next generation.
- Answers the open point "who dies" of the band.

### Races

Six invented races, none of them human. A race is data: a set of traits,
each a modifier over the band's rates. Decided by the user on 2026-10-14:
everything is built for one race, and races are added last, when all the
rest of the band era is ready.

- Some are cleverer: they learn faster, see further or remember longer.
- Some are stronger: they carry more and fight better.
- Some are faster: they walk further in a day.
- A race costs something for what it gives, so that none is best
  everywhere.

Two races are compatible, partly compatible or not compatible, and that
decides what young or females carried off, or a merged band, bring into
the next generations.

| Pair             | Offspring inherit                                      |
|------------------|--------------------------------------------------------|
| compatible       | one trait of the other race with a high chance, and one more with a low chance |
| partly compatible| one trait with a low chance                            |
| not compatible   | nothing; they cannot continue the population           |

Races that cannot mix attack each other more often, and compatible races
less often. The table of pairs is data too.

### Skills learned by doing

A band learns by living, not by a tree of research: what it does, where
it does it and what happens to it add experience, and a skill comes when
enough of it is gathered. A skill may need another first. Skills are
data: what teaches them, what they need and what they change.

Raised by the user:

- **Spears of sticks** - from long time in a forest. Better hunting and
  defence; needed for traps.
- **Litters** - from long walking with full loads. A band carries more.
- **Cages and traps** - from a forest, with spears. A predator met can be
  caught instead of only fought, by chance.
- **Dogs** - from caught wolves. A band with dogs meets predators less
  often and is stronger in a fight with a band, and the dogs eat and
  drink.

Proposed for the band era and agreed in principle by the user on
2026-10-14; the list is discussed when the item is reached:

- **Fire** - from camping, most in the cold. Food goes further, and the
  cold of winter costs less.
- **Drying and smoking** - from fire and much gathering of food. Forage
  spoils later.
- **Skins for water** - from gathering water often. More water is
  carried and it keeps longer.
- **Stone tools** - from outcrops and hills. Gathering is faster; needed
  for spears.
- **Fishing** - from gathering in shallows and on rivers. Food from
  water cells.
- **Swimming and rafts** - from time at the shore and on rivers. Fewer
  drownings; the bed of a great river can be crossed.
- **Herb lore** - from gathering in swamps, marshes and forests. Fewer
  poisonings, and hunger and thirst kill fewer.
- **Hides and shelters** - from winters in tundra and snow. Winter costs
  less, and camping rests better.
- **Climbing** - from hills and mountains. Fewer accidents, faster on
  steep land.
- **Tracking** - from encounters with predators survived. Hunting gives
  more food, and a predator is seen before it strikes.
- **Desert lore** - from time in deserts and dunes. Water is found in
  dry land.
- **Stars** - from long walks. A band remembers longer and keeps its
  way at night.

Open: whether a skill is lost when the people who held it die, and
whether a skill crosses to the tribe of stage 5.

### Weather

Weather is one more source of modifiers over the properties of a cell,
beside the season, the river and the stock, as the biomes were shaped
for: a dry spell, a wet one, a cold snap. It goes with frost, a later
item of its own.

### Balance of the band era

Once bands meet, skills, seasons, weather and the MCP seat are built,
the numbers of the band era are tuned: by the references of lives, by
the lab and by an assistant playing the seat. Until then nothing is
tuned.

___

## Open questions

Each is answered in the design doc of the stage named.

- **Merging** (stage 3, stage 5) - when two bands agree to merge, and how
  the two councils and the status of their members become one.
- **Land that comes into view** (stage 5) - whether the peoples placed
  there are raised bands only, or new ones as well.
- **The sea** (not set) - sea and lake are one biome, so a band that
  wades into the shallows drinks at the sea shore too. Telling salt
  water from fresh needs a second biome or a mark like the river's.
- **The size of the first window** (stage 3) - 5120 km across is a lot of
  land for one band and five to ten others. It is set again when it is
  known how often bands should meet.
- **The seam and the south** (stage 5) - the first window keeps clear of
  the seam and lies in the north, where the seasons are true. A window
  that grows may have to cross the seam and the equator.
- **Valleys** (not set) - a river is not cut into the land, so it may
  cross a cell of hills.
- **Frost and a climate that changes** (later) - water,
  rivers and land that freeze by season are a modifier of properties
  driven by the season and the temperature of the cell, not biomes. A
  planet that warms is the same with one more shift of temperature; the
  biomes `snow` and `ice` then become frost that never ends.
