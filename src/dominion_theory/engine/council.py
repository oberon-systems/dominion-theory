"""
The council of the day: the plans on the table, the decision, the judgement and status, as
docs/game/indirect_control.md states them.
"""

import math
from collections.abc import Callable, Iterator, Mapping, Sequence
from functools import partial
from typing import Any

from ..content import Params
from . import band as bands
from . import decisions, routes
from .band import Band, voters
from .cells import Place
from .clock import SeasonSchedule
from .commands import ABSTAIN, CAMP, DIRECTION, EXPLORE, GOING, PROPOSALS, ROAM, TO, WAYS
from .events import NO_LEADER, PROPOSAL

WORKED = 'worked'
EVEN = 'even'
FAILED = 'failed'
CAMPING = {'kind': CAMP}
# The words of a camp in its season.
WINTERING = 'winter-camp'
HIGHEST = 100.0
OCCASION = 'occasion-'
# What calls a council, in the order the first that holds is named: docs/game/indirect_control.md, Occasions.
FIRST = 'first'
DEATH = 'death'
HUNGER = 'hunger'
THIRST = 'thirst'
ENCOUNTER = 'encounter'
FOUND = 'found'
SPENT = 'spent'
TERM = 'term'
SEASON = 'season'
OCCASIONS = (FIRST, DEATH, HUNGER, THIRST, ENCOUNTER, FOUND, SPENT, TERM, SEASON)
# Why a plan was spent.
REACHED = 'reached'
NOTHING = 'nothing'
CLOSED = 'closed'
EXPECTED = (decisions.FOOD, bands.WATER, decisions.THREAT)
# The nearest unknown cells of a way a route is sought to before the way leads nowhere.
TRIES = 4
# The state that holds when the stores no longer cover a need.
UNCOVERED = {need: state for need, state in decisions.NEEDS.values()}


type Proposal = dict[str, Any]
type Table = list[dict[str, Any]]
type Inside = Callable[[int, int], bool]
# A plan, the band's score of it and the cell it is aimed at.
type Day = tuple[Proposal, float, Place]


def answer(fields: Mapping[str, Any]) -> Proposal | None:
    """
    The proposal of a vote, abstaining included, or None when the rules know no such answer.
    """
    held = fields.get('proposal')
    if set(fields) != {'proposal'} or not isinstance(held, Mapping):
        return None
    kind = held.get('kind')
    if kind == ABSTAIN and set(held) == {'kind'}:
        return {'kind': ABSTAIN}
    if not isinstance(kind, str) or kind not in PROPOSALS:
        return None
    named = set(held) - {'kind'}
    if kind == CAMP:
        return dict(CAMPING) if not named else None
    if len(named) != 1 or not named <= set(PROPOSALS[kind]):
        return None
    if DIRECTION in held:
        return heading(kind, held[DIRECTION]) if held[DIRECTION] in WAYS else None
    to = held[TO]
    if not isinstance(to, Mapping) or set(to) != {'x', 'y'} or not all(_whole(to[name]) for name in to):
        return None
    return going(kind, (to['x'], to['y']))


def _whole(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def going(kind: str, to: Place) -> Proposal:
    return {'kind': kind, TO: {'x': to[0], 'y': to[1]}}


def heading(kind: str, way: str) -> Proposal:
    return {'kind': kind, DIRECTION: way}


def target(proposal: Proposal) -> Place | None:
    """
    The cell a plan names, None for a camp or a direction.
    """
    to = proposal.get(TO)
    return None if to is None else (to['x'], to['y'])


def sector(at: Place, to: Place) -> str:
    """
    The way of the eight a cell lies from another, each the 45 degrees around it, clockwise from the north.
    """
    bearing = math.atan2(to[0] - at[0], at[1] - to[1])
    return WAYS[round(bearing / (math.pi / 4)) % len(WAYS)]


def key(proposal: Proposal | None, band: Band | None = None, winter: bool = False) -> str:
    """
    The words of a plan: a camp in its season is a winter camp, a roam or an explore is told by its way, that of
    its cell from the band when it names one.
    """
    if proposal is None:
        return NO_LEADER
    kind = proposal['kind']
    if kind == CAMP:
        return f'{PROPOSAL}{WINTERING if winter else CAMP}'
    way = proposal.get(DIRECTION)
    to = target(proposal)
    if way is None and to is not None and band is not None and to != band.place:
        way = sector(band.place, to)
    return f'{PROPOSAL}{kind}' if way is None else f'{PROPOSAL}{kind}-{way}'


def winters(params: Params, band: Band, wintering: bool) -> bool:
    """
    Whether a camp is the winter camp: in its season for a band that knows how, on land safe for one.
    """
    return wintering and not unsafe(params, band)


def _value(params: Params, band: Band, era: str, at: Place, wanted: dict[str, float]) -> float:
    """
    What land is worth to go to, weighed by distance and visits as a pull is.
    """
    cell = decisions.looks(params, band, era, at)
    if cell is None:
        return -math.inf
    value = decisions.worth(params, band, cell, wanted, band.unease)[0]
    return decisions.weighed(params, band, at, value, decisions.far(band.place, at))


def _routed(params: Params, band: Band, era: str, inside: Inside, to: Place) -> bool:
    looks = partial(decisions.looks, params, band, era)
    return routes.lay(params, band, to, inside, looks, decisions.needs(params, band)) is not None


def _better(params: Params, band: Band, era: str, inside: Inside) -> dict[str, Place]:
    """
    The best known land each way that is worth more to go to than staying, the earlier cell of a tie.
    """
    wanted = decisions.needs(params, band)
    staying = decisions.here(params, band, wanted, era)
    best: dict[str, tuple[float, Place]] = {}
    for at in sorted(band.known):
        if at == band.place or not inside(*at) or not decisions.reachable(band, at):
            continue
        value = _value(params, band, era, at, wanted)
        way = sector(band.place, at)
        if value > staying + bands.NOTHING and (way not in best or value > best[way][0]):
            best[way] = value, at
    return {way: at for way, (_, at) in best.items()}


def _unknown(params: Params, band: Band, era: str, inside: Inside, way: str) -> Place | None:
    """
    The nearest cell that way the band does not know and a route reaches, nearest the middle of the way first;
    None when the first `TRIES` of them have no route, or a horizon of 0 turns the unknown off.
    """
    window = params.planet.window
    middle = WAYS.index(way) * math.pi / 4
    tried = 0
    if not params.units.band.decisions.horizon:
        return None

    def off(at: Place) -> tuple[float, int, int]:
        bearing = math.atan2(at[0] - band.x, band.y - at[1])
        return abs(math.remainder(bearing - middle, 2 * math.pi)), at[1], at[0]

    for ring in range(1, max(window.width, window.height) + 1):
        cells = [
            (band.x + dx, band.y + dy)
            for dx in range(-ring, ring + 1)
            for dy in range(-ring, ring + 1)
            if max(abs(dx), abs(dy)) == ring
        ]
        found = [at for at in cells if inside(*at) and at not in band.known and sector(band.place, at) == way]
        for at in sorted(found, key=off):
            if _routed(params, band, era, inside, at):
                return at
            tried += 1
            if tried >= TRIES:
                return None
    return None


def aims(params: Params, band: Band, era: str, inside: Inside) -> Iterator[tuple[Proposal, Place]]:
    """
    The plans with a way the band could take and the cell each is aimed at, in the fixed order: the roams
    clockwise from the north, then the explores the same.
    """
    better = _better(params, band, era, inside)
    for way in WAYS:
        if way in better:
            yield heading(ROAM, way), better[way]
    for way in WAYS:
        at = _unknown(params, band, era, inside, way)
        if at is not None:
            yield heading(EXPLORE, way), at


def aim(params: Params, band: Band, era: str, inside: Inside, proposal: Proposal) -> Place | None:
    """
    The cell a plan goes to next: the own for a camp, the one it names, or the first target of its way; None
    when that way leads nowhere.
    """
    if proposal['kind'] == CAMP:
        return band.place
    to = target(proposal)
    if to is not None:
        return to
    way = proposal[DIRECTION]
    if proposal['kind'] == ROAM:
        return _better(params, band, era, inside).get(way)
    return _unknown(params, band, era, inside, way)


def fits(params: Params, band: Band, era: str, inside: Inside, proposal: Proposal) -> bool:
    """
    Whether the cell a plan names is one it may go to: land the band knows for a roam, land it does not know for an
    explore, not its own, inside the window, with a route.
    """
    to = target(proposal)
    if to is None:
        return True
    if to == band.place or not inside(*to) or (to in band.known) != (proposal['kind'] == ROAM):
        return False
    if to in band.known and not decisions.reachable(band, to):
        return False
    return _routed(params, band, era, inside, to)


def score(
    params: Params,
    band: Band,
    era: str,
    inside: Inside,
    extra: Sequence[Proposal] = (),
    wintering: bool = False,
    cold: bool = True,
) -> list[Day]:
    """
    What every plan is worth to the band, in the fixed order: the camp, a winter camp in its season to a band that
    knows how, then a roam and an explore each way, then every extra plan; two aimed at the same cell are the
    first of them. In the season of the camp, cold, camping in a built camp is worth its kept more while its reach
    still feeds the band a day.
    """
    weights = params.units.band.decisions.weights
    wanted = decisions.needs(params, band)
    here = decisions.here(params, band, wanted, era)
    sheltered = cold and bands.sheltered(band) and not decisions.stripped(params, band, era)
    kept = params.units.band.winter_camp.kept if sheltered else 0.0
    own = decisions.wintering(params, band, era) if winters(params, band, wintering) else here
    drawn = lure(params, band, era)
    days: list[Day] = [(dict(CAMPING), weights.move * (own + kept), band.place)]
    aimed = {band.place}
    for proposal, at in aims(params, band, era, inside):
        if at not in aimed:
            aimed.add(at)
            days.append((proposal, weights.move * _pull(params, band, era, proposal, at, wanted, drawn), at))
    for proposal in extra:
        if proposal['kind'] not in GOING or any(held == proposal for held, _, _ in days):
            continue
        named = aim(params, band, era, inside, proposal)
        if named is not None and fits(params, band, era, inside, proposal):
            value = _pull(params, band, era, proposal, named, wanted, drawn)
            days.append((dict(proposal), weights.move * value, named))
    return days


def _pull(
    params: Params, band: Band, era: str, proposal: Proposal, at: Place, wanted: dict[str, float], drawn: float
) -> float:
    """
    What a plan's first target is worth to go to, an explore by its lure; land worth nothing is not made worse by it.
    """
    value = _value(params, band, era, at, wanted)
    return value * drawn if proposal['kind'] == EXPLORE and value > 0 else value


def lure(params: Params, band: Band, era: str) -> float:
    """
    What draws the council to land the band does not know: docs/game/decisions.md, The lure of the unknown.
    """
    held = params.units.band.decisions.lure
    return 1.0 + held.poor * _poor(params, band, era) + held.crowded * _crowded(params, band, era)


def _poor(params: Params, band: Band, era: str) -> float:
    """
    The share of what the band hopes of the unknown that the best known land within sight, visits weighed, leaves
    wanting: 1 when nothing it knows is worth anything, 0 when it hopes for nothing.
    """
    wanted = decisions.needs(params, band)
    hoped = decisions.worth(params, band, decisions.expected(params, band), wanted, band.unease)[0]
    if hoped <= 0:
        return 0.0
    best = 0.0
    for at in (band.place, *bands.around(band.place, params.units.band.sight)):
        cell = decisions.seen(params, band, at, era) if decisions.reachable(band, at) else None
        if cell is not None:
            value = decisions.worth(params, band, cell, wanted, band.unease)[0]
            best = max(best, decisions.weighed(params, band, at, value, 0))
    return max(0.0, 1.0 - best / hoped)


def _crowded(params: Params, band: Band, era: str) -> float:
    """
    How far the band eats over `lure.from` of what the known land within sight grows back.
    """
    eaters = bands.census(params, band).eaters
    # Land that feeds nobody is no more crowded than land that feeds one: the lure stays finite.
    fed = max(decisions.feeding(params, band, era), 1.0)
    return max(0.0, eaters / fed - params.units.band.decisions.lure.from_)


def stands(params: Params, band: Band, era: str) -> bool:
    """
    Whether a band on a leg stands now: a starving or thirsting band never does, a tired one does until it has
    rested. Else it finishes the step it is on, marches on land that gives no day's food or with a load it could not
    add to, and otherwise while its stores hold `plan.march` days, once it stands until they hold `plan.stock`.
    """
    if bands.STARVATION in band.states or bands.THIRST in band.states:
        return False
    if bands.TIREDNESS in band.states:
        return True
    # A gathering loses the way into the next cell: a stand each morning would never cross slow land.
    if band.progress > 0 or decisions.barren(params, band, era) or _laden(params, band):
        return False
    rhythm = params.units.band.plan
    holding = band.intent is not None and band.intent['standing']
    days = min(bands.held_days(params, band, prop) for prop in decisions.NEEDS)
    return days < (rhythm.stock if holding else rhythm.march)


def _laden(params: Params, band: Band) -> bool:
    """
    Whether the band could carry no more of what it eats and drinks.
    """
    gathered = [name for name in params.units.band.gathering if params.resources[name].property in decisions.NEEDS]
    return all(bands.room(params, band, name) <= bands.NOTHING for name in gathered)


def unsafe(params: Params, band: Band) -> bool:
    """
    Whether the land the band stands on is too dangerous for a winter camp: its threat with the dread of the band,
    times what the guard of the band leaves of it over a day, reaches `winter_camp.unsafe`.
    """
    cell = band.known.get(band.place)
    threat = 0.0 if cell is None else bands.perceived(band, band.place, cell.get(decisions.THREAT, 0.0))
    return threat * decisions.guarded(params, band) >= params.units.band.winter_camp.unsafe


def survived(params: Params, band: Band, era: str, days: list[Day]) -> list[Day]:
    """
    What survival leaves of the plans, before any score is weighed: a band whose food or water ran out and whose
    people go short keeps only the plans off its land - off the reach of a winter camp it ranges from, where it
    gathers already - to land that gives more of what it lacks, the best of it by distance and visits, the
    nearest of those; on land that gives as much as any of them it camps to gather. A band that neither starves
    nor thirsts and keeps to its camp has no way off.
    """
    if bands.STARVATION not in band.states and bands.THIRST not in band.states:
        return [held for held in days if held[0]['kind'] == CAMP] if stocked(params, band) else days
    wanted = decisions.needs(params, band)
    reach = params.units.band.winter_camp.reach if bands.ranging(params, band) else 0
    away = [held for held in days if decisions.far(band.place, held[2]) > reach]
    if not away:
        return days
    gives = [decisions.feeds(decisions.looks(params, band, era, at) or {}, wanted) for _, _, at in away]
    own = decisions.feeds(decisions.seen(params, band, band.place, era) or {}, wanted)
    if own >= max(gives) - bands.NOTHING:
        return days
    weighed = []
    for held, given in zip(away, gives, strict=True):
        cells = decisions.far(band.place, held[2])
        if given > own + bands.NOTHING:
            weighed.append((held, decisions.weighed(params, band, held[2], given, cells), cells))
    best = max(value for _, value, _ in weighed) - bands.NOTHING
    nearest = min(cells for _, value, cells in weighed if value >= best)
    return [held for held, value, cells in weighed if value >= best and cells == nearest]


def stocked(params: Params, band: Band) -> bool:
    """
    Whether a band keeps to its built winter camp: in the seasons of the camp, on land still safe for one, while
    leaving it would drop food, not only spare goods and water over a day of drinking.
    """
    if band.season not in params.units.band.winter_camp.seasons or unsafe(params, band):
        return False
    return bands.abandoned(params, band) > bands.spared(params, band) + bands.NOTHING


def offered(params: Params, day: int) -> bool:
    """
    Whether a winter camp is offered on a day of the game: in one of its seasons, or in the days before one of
    them begins.
    """
    window = params.units.band.winter_camp.offered
    per_year = params.time.days_per_year
    schedule = SeasonSchedule(params.time, 1)
    today = day % per_year + 1
    if schedule.season(today) in window.seasons:
        return True
    before = params.days(window.before)
    return any(0 < (start - today) % per_year <= before for name, start in schedule.starts if name in window.seasons)


def until(params: Params, day: int, winter: bool) -> int:
    """
    The day the term of a plan decided on a day ends: a month on, or for a winter camp the first day that offers
    none.
    """
    if not winter:
        return day + max(params.days(params.council.term), 1)
    end = day + 1
    while offered(params, end) and end < day + params.time.days_per_year:
        end += 1
    return end


def votes(scores: list[float], members: int, spread: float) -> list[int]:
    """
    Whole votes by the weight exp(score / spread) of every option, by the largest remainder, ties to the earlier
    score.
    """
    if not scores:
        return []
    top = max(scores)
    weights = [math.exp((held - top) / spread) for held in scores]
    total = sum(weights)
    exact = [weight / total * members for weight in weights]
    whole = [math.floor(share) for share in exact]
    for index in sorted(range(len(exact)), key=lambda at: (whole[at] - exact[at], at))[: members - sum(whole)]:
        whole[index] += 1
    return whole


def table(
    params: Params,
    band: Band,
    era: str,
    inside: Inside,
    extra: Sequence[Proposal] = (),
    wintering: bool = False,
    cold: bool = True,
    behind: Place | None = None,
) -> Table:
    """
    How the others' votes lie over the plans survival leaves the band, each with its words, the cell it is aimed at
    and what the band expects there, and the band's score of it as the council remembers its last decision, which
    left the land `behind`; options without a vote are left out.
    """
    days = survived(params, band, era, score(params, band, era, inside, extra, wintering, cold))
    days = remembered(params, band, days, behind)
    given = votes([held for _, held, _ in days], voters(params, band) - 1, params.council.spread)
    winter = winters(params, band, wintering)
    laid = [
        _entry(params, band, era, proposal, day, held, at, winter)
        for (proposal, day, at), held in zip(days, given, strict=True)
    ]
    return [entry for entry in laid if entry['votes']]


def _entry(
    params: Params, band: Band, era: str, proposal: Proposal, day: float, held: int, at: Place, winter: bool
) -> dict[str, Any]:
    cell = decisions.looks(params, band, era, at) if proposal['kind'] in GOING else None
    return {
        'proposal': proposal,
        'key': key(proposal, band, winter),
        'to': None if cell is None else {'x': at[0], 'y': at[1]},
        'offset': None if cell is None else {'dx': at[0] - band.x, 'dy': at[1] - band.y},
        'expect': None if cell is None else {name: round(cell.get(name, 0.0), 4) for name in EXPECTED},
        'votes': held,
        'score': round(day, 4),
    }


def stores(params: Params, band: Band) -> dict[str, float | None]:
    """
    The days of food and of water the stores hold, None when nobody eats it.
    """
    found: dict[str, float | None] = {}
    for prop in decisions.NEEDS:
        days = bands.held_days(params, band, prop)
        found[prop] = None if math.isinf(days) else round(days, 1)
    return found


def remembered(params: Params, band: Band, days: list[Day], behind: Place | None) -> list[Day]:
    """
    The plans as the council remembers its last decision: the plan in force keeps `momentum`, a plan back to the
    land that decision left loses `back`.
    """
    weights = params.units.band.decisions.weights
    standing = None if band.intent is None else band.intent['proposal']
    found = []
    for proposal, held, at in days:
        if proposal['kind'] in GOING and proposal == standing:
            held += weights.momentum
        if proposal['kind'] in GOING and at == behind:
            held -= weights.move * weights.back
        found.append((proposal, held, at))
    return found


def behind(params: Params, band: Band, day: int) -> Place | None:
    """
    The land the last decision of the council left, while the band remembers it: through the decision in force,
    then `memory` days from the day its plan ended.
    """
    held = band.decision
    if held is None:
        return None
    standing = band.intent is not None and band.intent['proposal'] == held['proposal']
    if not standing and day > held['day'] + params.days(params.council.memory):
        return None
    return held['from'][0], held['from'][1]


def hungers(params: Params, band: Band, need: str) -> bool:
    """
    Whether a need, hunger or thirst, calls the council: once the stores no longer cover it, when its state holds
    or a member dies tonight of it.
    """
    return UNCOVERED[need] in band.states or decisions.needs(params, band)[need] >= 1.0


def leader(laid: Table) -> Proposal | None:
    """
    The option with the most votes of the others, the first in the fixed order of a tie.
    """
    if not laid:
        return None
    most = max(entry['votes'] for entry in laid)
    return next(dict(entry['proposal']) for entry in laid if entry['votes'] == most)


def decide(laid: Table, proposal: Proposal, spoken: float) -> tuple[Proposal, float]:
    """
    The winner once the player's voice is added to the proposal, and the votes of the proposal; a tie goes to
    the player, and among the others to the fixed order.
    """
    options = [(dict(entry['proposal']), float(entry['votes'])) for entry in laid]
    if all(option != proposal for option, _ in options):
        options.append((dict(proposal), 0.0))
    counted = [(option, held + spoken if option == proposal else held) for option, held in options]
    best = max(range(len(counted)), key=lambda at: (counted[at][1], counted[at][0] == proposal, -at))
    return counted[best][0], next(held for option, held in counted if option == proposal)


def settled(laid: Table, spoken: float) -> bool:
    """
    Whether the leader wins whatever the player says: no other option, one with no votes included, reaches its
    votes with the player's voice added.
    """
    if not laid:
        return False
    votes: list[int] = sorted((entry['votes'] for entry in laid), reverse=True)
    return (votes[1] if len(votes) > 1 else 0) + spoken < votes[0]


def voice(params: Params, voting: int, status: float) -> float:
    held = params.council.voice
    return max(held.least, held.share * voting * status / HIGHEST)


def worth(params: Params, band: Band, era: str, wanted: dict[str, float], unease: float) -> float:
    """
    What the cell the band stands on is worth to it, weighed by the needs and the unease given.
    """
    cell = decisions.seen(params, band, band.place, era)
    return decisions.worth(params, band, cell, wanted, unease)[0] if cell else 0.0


def expected(
    params: Params,
    band: Band,
    era: str,
    inside: Inside,
    leader: Proposal | None,
    wintering: bool = False,
    cold: bool = True,
) -> float:
    """
    The plan the leader promised, or the camp when nobody voted.
    """
    days = score(params, band, era, inside, () if leader is None else (leader,), wintering, cold)
    return next((held for proposal, held, _ in days if proposal == leader), days[0][1])


def reached(params: Params, band: Band, era: str, wanted: dict[str, float], unease: float) -> float:
    return params.units.band.decisions.weights.move * worth(params, band, era, wanted, unease)


def verdict(params: Params, judgement: dict[str, Any], now: float) -> str:
    """
    How a plan ended: the land reached against what the leader promised, then against the land the band left.
    Deaths are no part of it: each is paid once, by whoever voted for the plan.
    """
    if now >= judgement['expected']:
        return WORKED
    return EVEN if now >= judgement['before'] - params.council.judgement.slack else FAILED


def amount(params: Params, proposal: Proposal, found: str) -> float:
    """
    What a verdict does to status.
    """
    moved: float = getattr(params.council.status, f'{proposal["kind"]}_{found}')
    return moved


def scaled(amount: float, status: float) -> float:
    """
    A change of status as the height of status weighs it: above the middle gains shrink towards the top and
    losses grow; below it every amount is paid in full, so that a player can still fall to banishment.
    """
    middle = HIGHEST / 2
    if amount > 0:
        return amount * min((HIGHEST - status) / middle, 1.0)
    return amount * max(status / middle, 1.0)


def held(status: float) -> float:
    return min(max(status, 0.0), HIGHEST)
