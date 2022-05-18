from input.basic_monitor import BasicEventMonitor
from input.event_queue import Queue
from logging import getLogger
from keyboard import read_event, hook


class UsbRemoteMonitor(BasicEventMonitor):

    def __init__(self, queue_handler, event_type: str):
        self.logger = getLogger('MoodeIrController.UsbRemoteMonitor')
        self._queue = Queue()
        self.event_type:str = event_type
        super(UsbRemoteMonitor, self).__init__(queue_handler=queue_handler)

    def stop(self):
        self._queue.stop()
        super(UsbRemoteMonitor, self).stop()

    def run(self):
        hook(self._queue.enqueue)
        while self.is_running:
            key = self._queue.dequeue()

            if key is None:
                continue
            if key.event_type != self.event_type.lower():
                continue

            self.logger.debug(f'Received code {key.scan_code}')
            self.queue_handler.enqueue(key.scan_code)
