# Skills

#game #band #stage2

How a band learns by living, what it makes and carries of what it
learned, and what that gives it. A band learns a skill from what it
does, where it does it and what it lives through; a skill opens a
resource, a recipe, a role or a council proposal, and the goods held
give the bonuses. Part of the stage 2 design in
[the roadmap](../roadmap.md#skills-learned-by-doing); the band itself is
in [Band](../units/band.md). Every number here is data and a first
guess, to be tuned in the lab.

- [Three layers](#three-layers)
- [The skills](#the-skills)
- [Counters](#counters)
- [Goods](#goods)
- [Gathering goods](#gathering-goods)
- [Stocks and holders](#stocks-and-holders)
- [Handing out](#handing-out)
- [Making](#making)
- [Bonuses](#bonuses)
- [Hunting](#hunting)
- [Sickness and herbs](#sickness-and-herbs)
- [The council](#the-council)
- [Events and the client](#events-and-the-client)
- [What the API shows](#what-the-api-shows)
- [Left to the tribes](#left-to-the-tribes)
- [Parameters](#parameters)
- [Checks](#checks)
- [Open points](#open-points)

___

## Three layers

A skill and the good it makes are two things: the knowledge stays when
the goods are lost, and the goods give nothing without being held.

| Layer     | Is                                    | Gives                                   |
|-----------|---------------------------------------|-----------------------------------------|
| knowledge | what the band learned, `lore.known`   | nothing by itself; it opens a gathering, a recipe, a role or a proposal |
| goods     | what is held, resources of the kind `goods` | the bonuses, while held; they weigh and wear out |
| bonuses   | modifiers over parameter paths        | a changed rate: carry, threat, wear, age |

A bonus is the existing modifier, `{plus: x}` or `{times: x}`, laid over
a path of the tree, so a new bonus is a line of data and no code. A band
that lost its last stone still knows stone tools: it gathers stones
again on the next hills it meets.

___

## The skills

Knowledge belongs to the band, every band its own, so bots of stage 3
learn the same way. A skill is learned at the end of the day its
condition holds and every skill it needs is known; it is never
forgotten. A condition with needs counts from the day the needs were
met, not from the start.

| Skill         | Learned when                                              | Needs                    | Opens |
|---------------|-----------------------------------------------------------|--------------------------|-------|
| `orientation` | 4 biomes seen, or 30 days on the march                    | -                        | a go to a place of the player's own, `go_place` |
| `wintering`   | a winter lived through                                    | -                        | the winter camp, `winter_camp` |
| `stone_tools` | a night on or beside hills, mountain or outcrops          | -                        | gathering `stones` |
| `sticks`      | a night in or beside a forest                             | -                        | gathering `sticks` |
| `litters`     | 8 cells walked in or beside a forest                      | `sticks`, `herbs`        | making `litters` |
| `herbs`       | 90 days in forest, or 90 in grass or floodplain, or 30 in swamp | -                        | gathering `herbs` and `cords` |
| `spears`      | sticks, stones and cords held on the same day             | `stone_tools`, `sticks`, `herbs` | making `spears` and `clothes`, the role `hunter` |
| `waterskins`  | hides and cords held on the same day                      | `spears`, `herbs`        | making `waterskins` |

`orientation` - a band without it backs the ways the others name, but
the player cannot point the band at a place of their own. It is learned
by seeing 4 biomes, or by 30 days on the march: a day the band walked
or roamed, not one it only stood, gathered or built. The user asked for
3 to 4 biomes and 30 to 60 days; the lower days are the first guess.

`wintering` - the first winter is lived without a winter camp; it is
offered from the second winter on. A winter is lived through when a
season that offers no camp begins after one that does, the spring after
the winter, and the band learns it at the end of that day.

`litters` - a litter is lashed with cords, which only `herbs` gives, so
the skill needs it beside sticks and its cells are counted from the day
both are known. A band that learned litters by sticks alone in game
064ea2a3 knew them 75 days before it could make one.

`stone_tools` and `sticks` - one night is enough: every band camps every
evening, so the first night by the right land teaches it.

`spears` and `waterskins` - learned by doing: the band holds the
materials together and finds what they make.

___

## Counters

The band keeps what it learns by in `lore.counts`. A cell entered is
counted as the band walks into it; the rest is brought up to date at
the end of every day, before the skills are checked. A biome is "on
or beside" when the cell of the band or one of the 8 around it is of
that biome.

| Counter         | Counts                                                  |
|-----------------|---------------------------------------------------------|
| `seen`          | the biomes the band ever saw, as a set                  |
| `first`         | the biomes seen on the first day, as a set              |
| `walked`        | per biome, the cells entered of that biome              |
| `walked_by`     | per biome, the cells entered on or beside that biome    |
| `camped_by`     | per biome, the nights spent on or beside that biome     |
| `days_in`       | per biome, the days ended on a cell of that biome       |
| `winters`       | the winters lived through                               |
| `marched`       | the days the band walked or roamed at least once        |

A condition reads one counter with `at_least`, or `holds`, the stores
of the band; `any` and `all` join them. When a skill has needs, the
counts of the day its needs were met are kept beside it, and the
condition reads the counts gained since.

```yaml
orientation:
  learned:
    any:
      - {counter: seen, at_least: 4}
      - {counter: marched, at_least: 30}
litters:
  needs: [sticks, herbs]
  learned: {counter: walked_by, biome: forest, at_least: 8}
spears:
  needs: [stone_tools, sticks, herbs]
  learned: {holds: {sticks: 1, stones: 1, cords: 1}}
```

`biome: new` is any biome that is not in `first`.

___

## Goods

Goods are resources, entries of the section `resources` like food and
water, so the stores, weight and lots already work for them. A resource
gains a kind, a holder, a time to spoil, the uses it wears by, a
quality, a keep and a recipe.

| Good         | Kind  | Held     | Weight | Spoils after       | Wears by                                   | Quality         | Keep                | Made of                    |
|--------------|-------|----------|--------|--------------------|--------------------------------------------|-----------------|---------------------|----------------------------|
| `stones`     | goods | common   | 0.5 kg | -                  | 150 food eaten                             | 0.5 to 1.0, by the place | 0.3 a head  | gathered                   |
| `sticks`     | goods | common   | 1 kg   | 1 year             | 150 heads a night in camp, 1 an attack in camp | 1          | 0.3 a head          | gathered                   |
| `herbs`      | goods | common   | 0.1 kg | 2 months           | 1 a cure                                   | 1               | 0.2 a head          | gathered                   |
| `cords`      | goods | common   | 0.1 kg | 6 months x quality | - (spent in what is made)                  | 0.5 to 1.0, by the place | 0.2 a head  | gathered                   |
| `litters`    | goods | personal | 4 kg   | -                  | 40 days pulled                             | its materials'  | 1 a puller          | 3 sticks, 2 cords          |
| `spears`     | goods | personal | 1.5 kg | -                  | 60 hunts                                   | its materials'  | 1 a hunter          | 1 stick, 1 stone, 1 cord   |
| `hides`      | goods | common   | 2 kg   | 2 months           | - (spent in what is made)                  | 1               | 0.2 a head          | hunted                     |
| `clothes`    | goods | personal | 2 kg   | 8 months x quality | -                                          | its materials'  | 1 a member          | 1 hide, 1 cord             |
| `waterskins` | goods | personal | 0.5 kg | 6 months x quality | -                                          | its materials'  | 1 an adult or elder | 1 hide, 1 cord             |
| `meat`       | food  | common   | 1 kg   | 2 days             | -                                          | -               | -                   | hunted                     |

What each gives is in [Bonuses](#bonuses).

- **Kind** - `food`, `water` or `goods`. Every resource of the kind
  `food` is eaten, oldest lot first across them, and only `meat`
  sickens.
- **Held** - `common` goods stay in the band's stores; `personal` goods
  are handed to a member, see [Handing out](#handing-out).
- **Spoils** - a time, as for food and water: a lot is lost when it is
  over, used or not. For goods it is stretched by the quality of the
  lot. A good without one never spoils.
- **Wears** - the uses a unit of quality 1 serves, by use: a lot of a
  lower quality serves that share, and the oldest lots are worn first.
  A good held and not used does not wear. The uses are `eaten` (a unit
  of food eaten), `nights` (a head that spends a night in camp),
  `attacks` (an encounter met in camp), `cures` (a herb spent on a sick
  member or a wound), `pulled` (a day its holder walked or roamed
  with it) and `hunts` (a tick its holder hunted with it). A litter wears in the kit of its
  holder only: those left in the stores are not pulled. A good has a
  time to spoil, uses, or both; food and water have only the time.
- **Quality** - the third number of a lot, beside the day and the
  amount. Lots of the same day and quality merge.
- **Keep** - how much the band wants to hold, per head or per member of
  a kind. A gathered good below its keep is a need of the gathering; a
  made good below it is made.

___

## Gathering goods

A good is gathered like food and water: a property of the cell, a rate
per person and tick, and a share of the gatherers by its need. Four
properties are added to the band era; `game` is hunted, not gathered.

| Property | Biomes, base                                        | A full cell holds | Recovers in |
|----------|-----------------------------------------------------|-------------------|-------------|
| `stone`  | mountain 0.6, outcrops 0.8, hills 0.5               | 50 units          | 90 days     |
| `wood`   | forest 0.8                                          | 100 units         | 30 days     |
| `plants` | forest 0.5, grass 0.6, floodplain 0.7, swamp 0.8    | 50 units          | 30 days, a quarter in winter |
| `game`   | forest 0.7, grass 0.6, floodplain 0.5, tundra 0.4, hills 0.3, swamp 0.3 | 60 units | 60 days |

| Resource | Property | Rate per person per tick |
|----------|----------|--------------------------|
| `stones` | `stone`  | 0.5                      |
| `sticks` | `wood`   | 1.0                      |
| `herbs`  | `plants` | 0.2                      |
| `cords`  | `plants` | 0.3                      |

The need of a good is the share missing of its keep, weighed by
`weights.goods`, 0.4, against `weights.hunger` 1.5 and `weights.thirst`
1.2. So a fed band spends some of its hands and its carry on stones, at
the cost of the weight of food, and a hungry band spends none.

```text
need of a good = max(0, 1 - held / keep)
```

A gathering of a good takes no more than is missing of its keep: one tick
of a band of 15 in a forest would bring 12 sticks against a keep of 4.5,
and the rest would only weigh and wear out.

A good is gathered beside its biome too: a band by a forest or on the
foot of hills takes a little wood or stone. Of the cell the band stands
on and the eight around it, the one that gives most is gathered from,
and a cell beside gives `units.band.gathering_beside`, 0.3, of what it
would give the band standing on it; its stock falls by what is taken.
Food and water are not gathered beside: they come from the own cell, a
shore and the reach of a winter camp. A band of 15 on grass by a forest
takes 15 x 1.0 x 0.8 x 0.3 = 3.6 sticks a tick. The decisions and the
council see a cell so: its wood, stone and plants are the larger of its
own and of its neighbours' at that share.

The quality of a stone or a cord is drawn when it is gathered, from the
range of the biome of the cell it came from, on a stream of its own,
`goods`, and rounded to two places. The reed of a floodplain makes the
best cords, the bast of a forest the worst.

| Good     | Biome        | Quality      | Serves                       |
|----------|--------------|--------------|------------------------------|
| `stones` | `mountain`   | 0.8 to 1.0   | cuts 120 to 150 food         |
| `stones` | `outcrops`   | 0.65 to 0.9  | cuts about 100 to 135 food   |
| `stones` | `hills`      | 0.5 to 0.75  | cuts about 75 to 110 food    |
| `cords`  | `floodplain` | 0.8 to 1.0   | spoils in about 5 to 6 months |
| `cords`  | `swamp`      | 0.65 to 0.9  | spoils in about 4 to 5.5 months |
| `cords`  | `grass`      | 0.55 to 0.8  | spoils in about 3.5 to 5 months |
| `cords`  | `forest`     | 0.5 to 0.75  | spoils in about 3 to 4.5 months |

A band of 15 eats about 13 food a day with stones held, so its 4.5
stones of the hills last some 30 days and those of a mountain some 45.
Its sticks keep 15 heads a night, 0.1 of a stick, and lose one more to
every attack in camp; on the march they do not wear. Whatever wore out
or spoiled is told in whole units: the rest waits for the next.

Every biome that gives a new property lists the resource, and every
property needs its value in `decisions.unknown`, what a band expects of
land it does not know: `stone` 0.1 and `wood` 0.2, since few biomes give
them, `plants` 0.3 and `game` 0.3. The biomes that do not give a property hold it at a base of 0.

___

## Stocks and holders

What is held is one type, a stock: per resource, its lots. Anyone may
hold one.

| Holder | Field           | Holds                                                |
|--------|-----------------|------------------------------------------------------|
| band   | `stores`        | food, water, the common goods, personal goods no one holds |
| member | `kit`           | one of each personal good: a spear, clothes, a litter, a waterskin |
| place  | later           | a winter camp's cache, a settlement's store, a tribe's |

A personal good weighs in the load of its holder, so the free carry of
a band is what its members carry less its stores and their kits. The
goods of the dead go back to the band's stores, a worn one taken apart,
see [Handing out](#handing-out); taking them from a band
beaten is loot, stage 3.

___

## Handing out

In the first tick of the camp parts, the evening, the band hands its
personal goods to those who lack them, the way food is shared: the
least protected first. A good its holder may no longer use goes back to
the stores first. A good is handed out whole: a member takes one only
while a whole one is in the stores, and a worn one in a kit counts as
one, so it is not topped up. A worn good that comes back to the stores,
from the dead or from a holder who may no longer use it, is taken
apart: its materials go to the stores by the share left of it and at
its quality, so 0.43 of a litter of quality 0.92 gives 1.29 sticks and
0.86 cords of 0.92. The stores hold made goods whole only.

| Good         | Goes to, in order                                        |
|--------------|----------------------------------------------------------|
| `spears`     | the hunters                                              |
| `clothes`    | the children, then the elders, then the adults; the youngest first |
| `litters`    | the pullers: men, then women                             |
| `waterskins` | the adults, then the elders                              |

A puller is an adult gatherer: children do not pull, and nannies,
hunters and the holders of any other role do not either. So a band
never pulls more litters than it has such adults, and the ones over
stay in the stores and weigh as goods.

___

## Making

Making is automatic, with no action and no council: in the camp parts,
the evening and the night, a good whose skill is known and which is
below its keep is made while the materials of its recipe are held.

- The good furthest below its keep, by the share of it missing, is
  made first.
- Every adult makes `making.per_part`, 0.2, of a good in a camp part, so
  a band of 15 adults makes 3 goods in an evening and 3 in the night.
- The materials are taken from the oldest lots. A made good takes the
  mean quality of its materials, 1 for those without one: a spear of a
  mountain stone and a reed cord serves longest, a waterskin is as good
  as its cord allows. Every made good but the spear needs a cord, so
  the reed of a floodplain is worth a detour.
- A good goes into the stores whole. The work done on the next one waits
  in the band's `work`, with the quality of the materials spent on it,
  and a good is made when its work reaches one. So a band of 3 adults
  makes a litter in two camp parts, and no member holds a share of one.
- Every good made is in the event `goods-made`.

An adult here is a member of a stage that gathers, whatever its role.
The keep of a personal good counts the goods in the stores, every kit
holding one as one, worn or not, and the work begun, so a band of 10
pullers holding 10 litters makes no more. Making goes before the handing out of the evening, so a litter
made in the evening is pulled the next day.

Litters are the first good made: a band of 15 adults holding its keep
of 4.5 sticks and 3 cords makes a litter and half of the next in an
evening, every stick and cord spent, and gathers them again up to its
keep. A
litter takes the mean quality of its 3 sticks and 2 cords, so one of
reed cords serves some 37 to 40 days pulled and one of forest bast some
32 to 36.

___

## Bonuses

A bonus is laid over the parameters the band reads, by the goods it
holds and the roles it has. It is laid either on a member or on the band.
Its field `to` names which, `band` or `member`; it is not called `on`,
since YAML reads a key `on` as true.

- **On a member** - the bonus of a personal good holds for its holder:
  injury, frailty and carry are already drawn and summed per member.
- **On the band** - the bonus is laid by a share from 0 to 1: of the
  keep held for a common good, of the members equipped for a personal
  one, of the quota filled for a role. A share lays `{times: x}` as
  `1 + (x - 1) * share` and `{plus: x}` as `x * share`.

| Laid by      | On     | Path                                    | Modifier       | Share or condition         |
|--------------|--------|-----------------------------------------|----------------|----------------------------|
| `stones`     | band   | `units.band.consumption_per_day.forage` | times 0.9      | keep held                  |
| `stones`     | band   | `units.band.people.age.begins`          | plus 1 year    | keep held                  |
| `sticks`     | band   | `units.band.threat.camp`                | times 0.8      | keep held                  |
| `litters`    | member | `units.band.carry_kg`, of a man         | times 2.0      | -                          |
| `litters`    | member | `units.band.carry_kg`, of a woman       | times 1.5      | -                          |
| `litters`    | band   | `units.band.speed.base`                 | times 0.85     | members pulling            |
| `clothes`    | member | `units.band.people.injury.per_day`      | times 0.7      | -                          |
| `clothes`    | member | `units.band.people.exposure.encounter`  | times 0.8      | -                          |
| `clothes`    | member | `units.band.people.exposure.frailty`    | times 0.7      | in winter                  |
| `clothes`    | band   | `units.band.threat.camp` and `.march`   | times 0.9      | members holding            |
| `waterskins` | member | `units.band.carry_water_kg`             | plus 3 kg      | -                          |
| `waterskins` | band   | `resources.water.spoils`                | times 1.5      | adults and elders holding  |
| `hunter`     | band   | `units.band.threat.camp` and `.march`   | times 0.8      | quota filled               |

`units.band.threat` is new: `{camp: 1.0, march: 1.0}`, multiplied into
the threat of the encounters and of the safety of wellbeing, like
`winter_camp.threat`. `camp` holds in the ticks the band camps or
builds, `march` in the others. What the band sees of the land is not
changed: the land is as dangerous as before, the band is better
guarded.

A litter in a band of 15 adults, 8 men and 7 women, all pulling, adds
8 x 6 + 7 x 3 = 69 kg free to the 90 kg the band carries, at 85% of
its pace; the litters themselves are carried on top. There is no death of cold; the frailty of winter stands for it.

The parameters with the bonuses laid over them are computed once and
kept, like the census, until the goods, the members or the roles change:
a gathering, a meal, the wear and spoiling of goods and the handing out
forget them.
The pluses of a path are added before its times multiply, and a plus of
a span, like the year of `age.begins`, is laid in days. A bonus of
seasons holds only where the code that reads it names the season.

`units.band.people.exposure` is new: `{encounter: 1.0, frailty: 1.0}`,
what the goods of a member leave of its weights for those causes of
death, multiplied into the weights of its stage.

Every bonus of the table is built: a band
holding 0.3 stones a head eats 0.9 of its forage and dies of age a year
later, one holding 0.3 sticks a head meets 0.8 of the threat in camp,
and one whose pullers all pull a litter carries more at 0.85 of its
base pace. The carry of a member is its stage's share of `carry_kg`
with the bonuses of its own kit laid over. A bonus on the carry is
net: the good that lays it weighs in the load and adds its own weight
to the carry, so a man pulling a litter has 12 kg free and a woman 9.

`units.band.carry_water_kg` is new, 0: the water a member carries
beside its load, which only a waterskin gives, 3 kg. The water the
skins hold weighs nothing on the carry, so the room for water is the
room of the band and what its skins still take, and the room for
anything else is not cut by the water in them. A band of 15 adults,
all holding a skin, carries 45 kg of water beside its 90 kg of load,
and its water keeps 8 days instead of 5: a skin weighs 0.5 kg and a
day of water for the band 15.

___

## Hunting

The role `hunter` opens with `spears`. One member in 5, 0.2 of the
band, rounded down, may hunt; never more than there are spears, never
the player and never a nanny. Men come first, the youngest adults
first. The roles are laid at the end of the day, like the nanny's.

The members the role would take, adults of a stage that gathers and of
no role that cares, are those the keep of spears counts: the band makes
a spear for each and hands it to them in the evening. One of them
becomes a hunter at the end of a day while it holds a spear, so a band
never has more hunters than spears, and one without a spear pulls a
litter like any gatherer. A role with a `share` lays its bonuses on the
band by the share of it filled, the hunters over the members it would
take.

A hunter hunts only while the band stands: in the active ticks it
gathers, builds or camps. While the band walks or roams, a hunter
gathers like a gatherer.

```text
meat a tick  = hunters * hunting.meat * value(game, cell)
hides a tick = meat * hunting.hides
```

`hunters` counts the hunters as `gatherers` counts the gatherers: a
wounded, hungry or sick hunter brings its share, and the fatigue of the
band lowers it the same way. `hunting.meat` is 4.0 kg and
`hunting.hides` 0.05, one hide for 20 kg of meat. A hide is a material,
held in the stores until it is sewn into clothes or a waterskin, and
rots in 2 months if it is not. A hunt brings no more than the room
holds, meat and hides together, and no more hides than are missing of
their keep, 0.2 a head: three hunters bring about a hide a day, and the
rest would only weigh. The hunt pays the `game` of the cell, or of the
best cell in the reach of a winter camp, and lowers its stock by the
meat over the 60 units a full cell holds. Every hunter wears its spear
by a hunt a tick. Meat is food: it is eaten like forage and spoils in 2
days.

The game of a forest is the richest: more beasts live there, and cover lets
the hunters near them, so one value stands for both. Three hunters on
a cell of game 0.6 bring about 7 kg of meat a tick,
some 20 kg a day the band stands: more than a band of 15 eats, and the
cell is emptied in about three days.

___

## Sickness and herbs

A member is sick for `sickness.lasts`, 5 days, and gathers at 0.5 and walks
at 0.7 for that time; its frailty weight is doubled. A member falls sick
two ways.

- **Raw meat** - at the end of a day, each member who ate meat that day
  and is not sick yet falls sick with the chance `sickens` of meat,
  0.03, times the share of its ration that was meat.
- **Bad water** - the encounter `poisoning`, in a swamp or a marsh, takes
  its share as before; it `sickens`, so with herbs held the first of
  the members it takes are sick instead of dead, one for every herb, and
  the herbs are spent.

Herbs cure poisoning of any source and light wounds. At the end of a
day, while a whole herb is held, one is spent on every sick member,
whose sickness ends, then on every wound not treated yet whose severity
has a `treated` below 1, the light one, whose days left are cut to it,
half. The event `people-cured` counts them. The sick of the day's meat
are cured the same evening while herbs last, so herbs make meat safe at
the cost of a herb a sickness.

___

## The council

Two skills gate what the council offers and what the player may say.

- **Without `orientation`** - a `vote` that proposes a place no option of
  the table names is refused with `refused-not-learned`. Backing a go
  the others named is allowed. The council says it in `place`, so a
  client offers no cell of the player's own.
- **Without `wintering`** - the winter camp is not offered, to the
  player or to the band's own decision; a `vote` that names it is
  refused with `refused-not-learned`.

A council called by a new skill, an occasion, is a later bridge to the
encounters between bands and is not built now.

___

## Events and the client

Every event goes the existing way: an engine event, the record and the
update of the tick, a line of the client from the catalogues `en` and
`ru`.

| Event            | Values                         | The client says                        |
|------------------|--------------------------------|----------------------------------------|
| `skill-learned`  | `skill`                        | The band has learned stone tools.      |
| `goods-made`     | `resource`, `count`            | Made: litters 2.                       |
| `goods-spoiled`  | `resource`, `count`            | Spoiled: sticks 2.                     |
| `goods-worn`     | `resource`, `count`            | Worn out: stones 3.                    |
| `people-sickened`| `count`, `cause`               | 2 people are sick from raw meat.       |
| `people-cured`   | `count`                        | Herbs helped 2 people.                 |

The `cause` of `people-sickened` is `meat`, or the kind of the
encounter that sickened, `poisoning`.

The band line of the client shows the skills known and the kit: how
many hold a spear, clothes, a litter, a waterskin. The stores line shows
the goods like food and water. Every skill and every good is a name in
both catalogues, `skill-<name>` and `resource-<name>`.

The reference of lives keeps the day every skill was learned, and the
report of a tick gains the counters `skills`, `hunters` and `sick`.

___

## What the API shows

The unit of the snapshot gains four fields; `roles` gains the hunter
and `stores` the common goods. `goods` sums every good the band holds,
in its stores and in the kits of its members, per good; `kit` counts
the members holding each personal good and `sick` the members who are.

```json
{
  "lore": ["orientation", "sticks", "stone_tools"],
  "goods": {"stones": 4.0, "sticks": 2.0, "spears": 2.0},
  "kit": {"clothes": 9, "litters": 6, "spears": 2, "waterskins": 0},
  "sick": 1,
  "roles": {"gatherer": 10, "nanny": 1, "hunter": 2},
  "stores": {"water": 30.0, "forage": 22.5, "stones": 4.0, "sticks": 2.0}
}
```

The counters of `lore.counts` stay in the state of the game, which takes
a new format: the band gains `lore`, a member gains `kit` and `sick`,
and a lot gains its quality.

___

## Left to the tribes

Fire and how to make it is left to the tribes of stage 5, and drying
and smoking go with it. The other skills raised for the band era are in
[the roadmap](../roadmap.md#skills-learned-by-doing) and get their
design when they are reached.

___

## Parameters

A sketch of the data, every number a first guess. The skills are a new
section `skills`; the goods extend `resources`; the rest extends
`units.band`.

```yaml
skills:
  orientation:
    learned:
      any:
        - {counter: seen, at_least: 4}
        - {counter: marched, at_least: 30}
    opens: {proposals: [go_place]}
  wintering:
    learned: {counter: winters, at_least: 1}
    opens: {proposals: [winter_camp]}
  stone_tools:
    learned: {counter: camped_by, biomes: [hills, mountain, outcrops], at_least: 1}
    opens: {gathers: [stones]}
  sticks:
    learned: {counter: camped_by, biome: forest, at_least: 1}
    opens: {gathers: [sticks]}
  litters:
    needs: [sticks, herbs]
    learned: {counter: walked_by, biome: forest, at_least: 8}
    opens: {makes: [litters]}
  herbs:
    learned:
      any:
        - {counter: days_in, biome: forest, at_least: 90}
        - {counter: days_in, biomes: [grass, floodplain], at_least: 90}
        - {counter: days_in, biome: swamp, at_least: 30}
    opens: {gathers: [herbs, cords]}
  spears:
    needs: [stone_tools, sticks, herbs]
    learned: {holds: {sticks: 1, stones: 1, cords: 1}}
    opens: {makes: [spears, clothes], roles: [hunter]}
  waterskins:
    needs: [spears, herbs]
    learned: {holds: {hides: 1, cords: 1}}
    opens: {makes: [waterskins]}
```

```yaml
resources:
  water: {kind: water, property: water, weight_kg: 1.0, spoils: {days: 5}}
  forage: {kind: food, property: food, weight_kg: 1.0, spoils: {days: 3}}
  meat: {kind: food, weight_kg: 1.0, spoils: {days: 2}, sickens: 0.03}
  stones:
    kind: goods
    property: stone
    weight_kg: 0.5
    wears: {eaten: 150}
    quality: {mountain: {min: 0.8, max: 1.0}, outcrops: {min: 0.65, max: 0.9}, hills: {min: 0.5, max: 0.75}}
    keep: {per: head, amount: 0.3}
    gives:
      - {to: band, path: units.band.consumption_per_day.forage, times: 0.9}
      - {to: band, path: units.band.people.age.begins, plus: {years: 1}}
  sticks:
    kind: goods
    property: wood
    weight_kg: 1.0
    spoils: {years: 1}
    wears: {nights: 150, attacks: 1}
    keep: {per: head, amount: 0.3}
    gives:
      - {to: band, path: units.band.threat.camp, times: 0.8}
  herbs: {kind: goods, property: plants, weight_kg: 0.1, spoils: {months: 2}, wears: {cures: 1}, keep: {per: head, amount: 0.2}}
  cords:
    kind: goods
    property: plants
    weight_kg: 0.1
    spoils: {months: 6}
    quality:
      floodplain: {min: 0.8, max: 1.0}
      swamp: {min: 0.65, max: 0.9}
      grass: {min: 0.55, max: 0.8}
      forest: {min: 0.5, max: 0.75}
    keep: {per: head, amount: 0.2}
  litters:
    kind: goods
    held: personal
    weight_kg: 4.0
    wears: {pulled: 40}
    keep: {per: puller, amount: 1}
    made: {sticks: 3, cords: 2}
    gives:
      - {to: member, sex: male, path: units.band.carry_kg, times: 2.0}
      - {to: member, sex: female, path: units.band.carry_kg, times: 1.5}
      - {to: band, path: units.band.speed.base, times: 0.85}
  spears:
    kind: goods
    held: personal
    weight_kg: 1.5
    wears: {hunts: 60}
    keep: {per: hunter, amount: 1}
    made: {sticks: 1, stones: 1, cords: 1}
  hides: {kind: goods, weight_kg: 2.0, spoils: {months: 2}, keep: {per: head, amount: 0.2}}
  clothes:
    kind: goods
    held: personal
    weight_kg: 2.0
    spoils: {months: 8}
    keep: {per: member, amount: 1}
    made: {hides: 1, cords: 1}
    gives:
      - {to: member, path: units.band.people.injury.per_day, times: 0.7}
      - {to: member, path: units.band.people.exposure.encounter, times: 0.8}
      - {to: member, path: units.band.people.exposure.frailty, times: 0.7, seasons: [winter]}
      - {to: band, path: units.band.threat.camp, times: 0.9}
      - {to: band, path: units.band.threat.march, times: 0.9}
  waterskins:
    kind: goods
    held: personal
    weight_kg: 0.5
    spoils: {months: 6}
    keep: {per: adult, amount: 1}
    made: {hides: 1, cords: 1}
    gives:
      - {to: member, path: units.band.carry_water_kg, plus: 3.0}
      - {to: band, path: resources.water.spoils, times: 1.5}
```

```yaml
units:
  band:
    threat: {camp: 1.0, march: 1.0}
    carry_water_kg: 0.0
    gathering: {stones: 0.5, sticks: 1.0, herbs: 0.2, cords: 0.3}
    decisions:
      unknown: {stone: 0.1, wood: 0.2, plants: 0.3, game: 0.3}
      weights: {goods: 0.4}
    people:
      roles:
        hunter:
          gathers: 1.0
          share: 0.2
          needs: spears
          gives:
            - {to: band, path: units.band.threat.camp, times: 0.8}
            - {to: band, path: units.band.threat.march, times: 0.8}
      sickness: {lasts: {days: 5}, pace: 0.7, gathers: 0.5, frailty: 2.0}
      exposure: {encounter: 1.0, frailty: 1.0}
      injury:
        severities:
          light: {days: 10, pace: 0.8, gathers: 0.7, treated: 0.5}
    making: {per_part: 0.2}
    hunting: {meat: 4.0, hides: 0.05}
eras:
  band:
    capacity: {stone: 50, wood: 100, plants: 50, game: 60}
    recovery: {plants: {winter: 0.25}}
encounters:
  kinds:
    poisoning: {sickens: true}
```

The four new properties go into the biome files with a base and a
recovery each, as [Gathering goods](#gathering-goods) lists them.

___

## Checks

A game does not start from skills and goods that do not add up.

- Every skill a skill needs exists, and no skill needs itself through
  others.
- A condition names a known counter, biomes of the section `biomes` and
  resources of the section `resources`.
- Everything a skill opens exists: a resource, a recipe, a role, a
  proposal.
- A good of the kind `goods` has a time to spoil, uses to wear by, or
  both, and the uses are known ones; a range of quality lies in 0 to 1
  and names biomes that give its property.
- A recipe names resources only, with amounts above 0, and no good is
  made of itself.
- A bonus names a path of the tree that holds a number, and `to` is
  `band` or `member`.
- A role that `needs` a good names a personal one; the share of a role
  lies in 0 to 1, and its bonuses go to the band. Exactly one role cares
  for nobody and has no share: the common one.
- The resources a hunt brings, `meat` and `hides`, exist.

___

## Open points

- **Knowledge that dies** - knowledge stays with the band. Whether a
  skill is lost when the people who held it die is weighed beside the
  roles of members.
- **A council on a new skill** - an occasion that calls the council
  when a skill is learned is a later bridge to the encounters between
  bands.
- **Who makes** - every adult makes at the same pace. A maker who gets
  better with the doing belongs with the finer roles of a tribe.
- **Goods in a camp** - a winter camp could keep a cache of goods left
  behind; the holder `place` is ready for it.
- **Loot** - the goods of a beaten band belong to stage 3.
- **Complex goods** - every good made so far is made in the camp parts of
  any day, since the band camps in them. A complex good, marked so in
  its recipe, will be made only at a standing camp - the camp parts of a
  day the band did not walk or roam - or in a built winter camp. None is
  complex yet: spears and waterskins are made in any camp part.
- **Game in the decisions** - a band does not weigh the `game` of a cell
  when it chooses where to go: the hunters take what the land the band
  stands on gives. A pull of meat beside the pull of forage is weighed
  in the lab.
- **A card of a member** - a member will get a name and a card with its
  stats and its kit. Goods are handed out whole so that a card shows
  things, not shares of them.
