from logging import getLogger
from typing import Tuple, Callable, Dict, Union
from handlers.base_handler import BaseActionHandler
from threading import Condition, Thread


MAX_QUEUE_LEN = 5


class Executor:

    def __init__(self, get_handler: Callable, get_renderer: Callable):
        self._queue = Executor.Queue()
        self._runner = Executor.Runner(self._queue, get_handler, get_renderer)

        self._runner.start()

    def enqueue(self, action: Dict):
        self._queue.enqueue(action)

    def stop(self):
        if self._runner:
            if self._runner.is_running:
                self._queue.enqueue((self._runner.stop, []), now=True)
            self._runner.join()

    def __del__(self):
        self.stop()

    class Queue:

        def __init__(self):
            self._condition = Condition()
            self._queue = list()

        def enqueue(self, action: Union[Dict, Tuple], now: bool = False):
            with self._condition:
                # Do not queue too many commands at the same time
                if now:
                    self._queue.insert(0, action)
                elif len(self._queue) < MAX_QUEUE_LEN:
                    self._queue.append(action)
                self._condition.notify()

        def dequeue(self) -> Union[Dict, Tuple]:
            with self._condition:
                while not self.has_more():
                    self._condition.wait()
                return self._queue.pop(0)

        def has_more(self) -> bool:
            with self._condition:
                return len(self._queue) > 0

    class Runner(Thread):

        def __init__(self, queue, get_handler: Callable, get_renderer: Callable):
            super().__init__()
            self._queue = queue
            self._get_renderer = get_renderer
            self._get_handler = get_handler
            self.logger = getLogger('MoodeIrController.Executor')

            self._running = True

        def run(self):
            while self._running:
                action = self._queue.dequeue()
                if isinstance(action, tuple):
                    self._execute(action)
                elif isinstance(action, dict):
                    renderer = self._get_renderer()
                    if renderer in action.keys():
                        commands = action[renderer]
                    elif 'global' in action.keys():
                        commands = action['global']
                    else:
                        continue

                    if not isinstance(commands, list):
                        commands = [commands]

                    for command_dict in commands:
                        handler: BaseActionHandler = self._get_handler(command_dict['target'])
                        if handler:
                            self._execute((handler.call, [command_dict]))

        def _execute(self, element: Tuple):
            (func, args) = element
            self.logger.debug(f"Running command {args}")
            try:
                func(*args)
            except Exception as e:
                self.logger.exception(e)

        @property
        def is_running(self):
            return self._running

        def stop(self):
            self._running = False
