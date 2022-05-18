from threading import Condition


MAX_QUEUE_LEN = 10


class Queue:

    def __init__(self):
        self._condition = Condition()
        self._queue = list()
        self._running = True

    @property
    def is_running(self):
        return self._running

    def stop(self):
        self._running = False

    def enqueue(self, item, *args, **kwargs):
        with self._condition:
            # Do not queue too many commands at the same time
            if len(self._queue) < MAX_QUEUE_LEN:
                self._queue.append(item)
            self._condition.notify()

    def dequeue(self):
        with self._condition:
            while not self.has_more() and self.is_running:
                self._condition.wait(timeout=1.0)

            if not self.has_more():
                return None
            return self._queue.pop(0)

    def has_more(self) -> bool:
        with self._condition:
            return len(self._queue) > 0
