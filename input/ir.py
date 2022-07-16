from input.basic_monitor import BasicEventMonitor
from piir.decode import decode
from time import sleep
from logging import getLogger
import pigpio


class IrMonitor(BasicEventMonitor):

    def __init__(self, queue_handler, ir_gpio_pin):
        self.logger = getLogger('MoodeIrController.IrMonitor')
        self.ir_gpio_pin = ir_gpio_pin
        super(IrMonitor, self).__init__(queue_handler=queue_handler)

    def receive(self, gpio, glitch=100, timeout=200):
        last_tick = 0
        in_code = False
        recording = False
        pulses = []

        def callback(_gpio, _level, _tick):
            nonlocal last_tick, in_code, recording
            usec = pigpio.tickDiff(last_tick, _tick)
            last_tick = _tick
            if _level == pigpio.TIMEOUT:
                if in_code:
                    in_code = False
                    recording = False
            else:
                if in_code:
                    pulses.append(usec)
                else:
                    # Ignore the first one (time since last timeout).
                    in_code = True

        pi = pigpio.pi()    # Connect to Pi.

        if not pi.connected:
            raise IOError

        pi.set_mode(gpio, pigpio.INPUT)     # IR RX connected to this GPIO.
        pi.set_glitch_filter(gpio, glitch)  # Ignore glitches.
        pi.set_watchdog(gpio, timeout)
        pi.callback(gpio, pigpio.EITHER_EDGE, callback)

        while self.is_running:
            recording = True
            while recording and self.is_running:
                sleep(0.01)
            if pulses:
                break

        pi.stop()

        return pulses

    @staticmethod
    def _parse_code(code):
        """
        Parse received code to a json compatible format

        :param code: list
        :return: dict
        """

        if not code:
            return

        if isinstance(code, list):
            code = code[0]

        if isinstance(code, dict):
            if not ({'data', 'preamble', 'postamble'} < set(code.keys())):
                # Required fields
                return

            if not isinstance(code['data'], bytes):
                return

            code['data'] = code['data'].hex()
            keys_to_remove = ['gap', 'timebase']
            for key in keys_to_remove:
                if key in code:
                    del code[key]

            for key, value in code.items():
                if isinstance(value, set) or isinstance(value, tuple):
                    code[key] = list(value)

            return code

    def run(self):
        while self.is_running:
            code = decode(self.receive(self.ir_gpio_pin))
            parsed = self._parse_code(code)
            if parsed:
                self.logger.debug(f'Received code {parsed}')
                self.queue_handler.enqueue(parsed)
