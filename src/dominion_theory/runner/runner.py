"""
A runner owns one game and decides when it steps. The two differ in nothing else.
"""

import asyncio
from collections import deque
from collections.abc import Callable
from dataclasses import asdict
from functools import partial
from pathlib import Path
from typing import Any

from ..core import logger
from ..core.errors import DominionError
from ..core.settings import Settings
from ..engine import Command, Game, StepResult
from ..engine.commands import VOTE
from ..engine.events import COMMAND_ACCEPTED, COMMAND_REFUSED
from ..store import GameStore, Meta
from .record import Judged, RecordWriter, footer_line, tick_lines
from .updates import Ended, Resync, Update

STEP = 'step'
REAL_TIME = 'real-time'
STOPPED = 'stopped'
VERDICTS = (COMMAND_ACCEPTED, COMMAND_REFUSED)
# How often a clock that waits for a council looks for the vote, in seconds.
LOOK_S = 0.05

GAME_ENDED = 'error-game-ended'
CLOCK_RUNNING = 'error-clock-running'

type Listener = Callable[[Update | Ended], None]


class Runner:
    mode = ''

    def __init__(
        self,
        game_id: str,
        game: Game,
        store: GameStore,
        record: RecordWriter,
        settings: Settings,
        seq: int = 0,
    ) -> None:
        self.id = game_id
        self.game = game
        self.seq = seq
        self.ended = False
        self._store = store
        self._record = record
        self._settings = settings
        self._kept: deque[Update] = deque(maxlen=settings.updates_kept)
        self._listeners: list[Listener] = []
        # Kept in step with Game.submit, which does not say whether it took a command.
        commands = game.snapshot()['commands']
        self._sequence: dict[str, int] = dict(commands['sequence'])
        self._seen: set[str] = set(commands['seen'])
        self._held: dict[str, tuple[int, Command]] = {
            held['command']['id']: (held['seq'], Command.read(held['seat'], held['command']))
            for held in commands['pending']
        }

    @property
    def running(self) -> bool:
        return False

    @property
    def waiting(self) -> list[str]:
        return []

    @property
    def record_path(self) -> Path:
        return self._record.path

    @property
    def asked(self) -> list[str]:
        """
        The seats the council of the day still waits for: asked, and with no vote held yet.
        """
        voted = {command.seat for _, command in self._held.values() if command.kind == VOTE}
        return [seat for seat in self.game.asking if seat not in voted]

    def submit(self, command: Command) -> None:
        self._alive()
        taken = self._take(command)
        if taken is not None:
            entry = {'seat': taken.seat, 'command': taken.envelope()}
            self._store.append_changes(self.id, self.game.tick, entry)

    def step(self) -> Update:
        self._alive()
        return self._tick()

    def snapshot(self) -> dict[str, Any]:
        return {
            'seq': self.seq,
            'date': asdict(self.game.date),
            'window': asdict(self.game.window),
            'seat': self.game.seat,
            'units': [] if self.game.band is None else [self.game.band.shown(self.game.window.scale)],
            'waiting': self.waiting,
        }

    def since(self, after: int) -> list[Update] | Resync:
        missed = [update for update in self._kept if update.seq > after]
        if len(missed) != self.seq - after:
            return Resync(self.seq)
        return missed

    def subscribe(self, listener: Listener) -> Callable[[], None]:
        self._listeners.append(listener)
        return partial(self._listeners.remove, listener)

    def pause(self) -> None:
        """
        Stops the clock; a runner without one has nothing to stop.
        """

    def resume(self) -> None:
        """
        Starts the clock, where there is one.
        """

    def set_speed(self, value: float) -> None:
        """
        Sets the multiplier of the clock, where there is one.
        """

    def end(self, outcome: str = STOPPED) -> Ended:
        self._alive()
        self.pause()
        self.ended = True
        ended = Ended(outcome, self.game.tick, self.game.state_hash())
        self._record.close(footer_line(outcome, ended.tick, ended.hash))
        self._store.drop(self.id)
        self._tell(ended)
        return ended

    def save(self) -> None:
        meta = Meta(seed=self.game.seed, params=self.game.params.hash, tick=self.game.tick, mode=self.mode)
        self._store.save_snapshot(self.id, {**self.game.snapshot(), 'seq': self.seq}, meta)

    def catch_up(self, entries: list[dict[str, Any]]) -> None:
        """
        Takes a restored game through what the store holds after its snapshot, in order.
        """
        for entry in entries:
            if 'command' in entry:
                self._take(Command.read(entry['seat'], entry['command']))
            else:
                self._advance()

    def _alive(self) -> None:
        if self.ended:
            raise DominionError(GAME_ENDED, id=self.id)

    def _tell(self, message: Update | Ended) -> None:
        for listener in list(self._listeners):
            listener(message)

    def _take(self, command: Command) -> Command | None:
        seq = self._sequence.get(command.seat, 0) + 1
        name = command.id or f'{command.seat}-{seq}'
        if name in self._seen:
            return None
        command = command.named(name)
        self._seen.add(name)
        self._sequence[command.seat] = seq
        self._held[name] = (seq, command)
        self.game.submit(command)
        return command

    def _advance(self) -> StepResult:
        result = self.game.step()
        judged: list[Judged] = []
        for event in result.events:
            if event.key in VERDICTS:
                seq, command = self._held.pop(event.values['id'])
                judged.append((seq, command, event.key == COMMAND_ACCEPTED))
        self._record.add(result.tick, tick_lines(result, judged))
        self.seq += 1
        return result

    def _tick(self) -> Update:
        per_day = self.game.params.time.parts_per_day
        day = self.game.clock.parts // per_day
        result = self._advance()
        if result.parts // per_day > day:
            self._record.flush()
            self.save()
        else:
            self._store.append_changes(self.id, result.tick, {'changes': result.changes})
        update = Update(self.seq, result.date, result.events, result.changes, [] if self.game.over else self.waiting)
        self._kept.append(update)
        self._tell(update)
        if self.game.over:
            self.end(self.game.outcome or STOPPED)
        return update


class StepRunner(Runner):
    """
    A tick when every seat has answered, or when asked.
    """

    mode = STEP

    @property
    def waiting(self) -> list[str]:
        answered = {command.seat for _, command in self._held.values()}
        return [seat for seat in self.game.seats if seat not in answered]

    def submit(self, command: Command) -> None:
        super().submit(command)
        if not self.waiting:
            self._tick()


class RealTimeRunner(Runner):
    """
    A tick every tick_ms of the settings, divided by the speed, while not paused; a council stops the clock
    until the seat votes or council_wait_s runs out.
    """

    mode = REAL_TIME

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._task: asyncio.Task[None] | None = None
        self._speed = 1.0

    @property
    def running(self) -> bool:
        return self._task is not None

    def step(self) -> Update:
        if self.running:
            raise DominionError(CLOCK_RUNNING, id=self.id)
        return super().step()

    def pause(self) -> None:
        if self._task is not None:
            self._task.cancel()
            self._task = None

    def resume(self) -> None:
        self._alive()
        if self._task is None:
            self._task = asyncio.get_running_loop().create_task(self._run())

    def set_speed(self, value: float) -> None:
        if value <= 0:
            raise ValueError('the speed is a multiplier above zero')
        self._speed = value

    async def _run(self) -> None:
        while True:
            await asyncio.sleep(self._settings.tick_ms / 1000 / self._speed)
            waited = 0.0
            while self.asked and waited < self._settings.council_wait_s:
                await asyncio.sleep(LOOK_S)
                waited += LOOK_S
            try:
                self._tick()
            except Exception:
                logger.exception('the clock of the game %s stopped', self.id)
                self._task = None
                return


RUNNERS: dict[str, type[Runner]] = {STEP: StepRunner, REAL_TIME: RealTimeRunner}
