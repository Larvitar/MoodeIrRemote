from threading import Thread


class BasicEventMonitor(Thread):

    def __init__(self, queue_handler):
        super().__init__()
        self.queue_handler = queue_handler
        self._running = True

    def run(self):
        raise NotImplementedError

    @property
    def is_running(self):
        return self._running

    def stop(self):
        self._running = False
