from handlers.base_handler import BaseActionHandler
from handlers.shell import ShellCommandsHandler
from handlers.spotify import SpotifyHandler
from handlers.moode import MoodeHandler
from handlers.bluetooth import BluetoothHandler
from input.basic_monitor import BasicEventMonitor
from input.ir import IrMonitor
from input.usb_remote import UsbRemoteMonitor
from input.event_queue import Queue
from pprint import pformat
from typing import Optional, List, Dict, Tuple
from os import path, makedirs
from logging import getLogger, StreamHandler, Formatter, basicConfig
from logging.handlers import TimedRotatingFileHandler
from requests.exceptions import ConnectionError
from time import sleep, time
from copy import deepcopy
import json
import sys
import atexit


DIR = path.dirname(path.realpath(__file__))
INIT_TIMEOUT = 120


class Config(object):

    def __init__(self):
        self.ir_gpio_pin: Optional[int] = None
        self.enable_ir_remote: bool = True
        self.enable_usb_remote: bool = False
        self.keyboard_event_type: str = 'up'
        self.remotes: List[str] = []
        self.spotify: Dict[str, str] = {}
        self.default_moode_set: str = "set_playlist"
        self.logging = {
            "level": "INFO",
            "file_level": "DEBUG",
            "global_level": "WARNING",
            "log_all_to_file": True
        }

    def load(self):
        with open(path.join(DIR, 'config.json')) as file:
            config: Dict = json.load(file)
            for key, value in config.items():
                setattr(self, key, value)


class ControllerApp(object):

    def __init__(self, test_mode=False):
        self.test_mode = test_mode

        self.config: Config = Config()
        self.config.load()

        self.logger = getLogger('MoodeIrController')
        self._logger_init()

        if not self.config.remotes:
            self.logger.error('There are no remotes configured!')

        self.keymap: Dict[str, Optional[List, str]] = dict()
        self.commands: Dict[str, Dict] = dict()

        self.handlers: Dict[str, BaseActionHandler] = {}
        if not self.test_mode:
            self._wait_for_moode()
            self.handlers = {
                'shell': ShellCommandsHandler(),
                'spotify': SpotifyHandler(config=self.config.spotify, cache_path=path.join(DIR, '.cache')),
                'moode': MoodeHandler(),
                'bluetooth': BluetoothHandler()
            }
            self.handlers['moode'].default_set = self.config.default_moode_set
            self.handlers['moode'].current_set = self.config.default_moode_set

        self.load_commands()

        self.event_queue = Queue()
        self._load_input_handlers()

        atexit.register(self.stop)

    def _load_input_handlers(self):
        self.input_handlers: List[BasicEventMonitor] = []
        if self.config.enable_ir_remote:
            self.input_handlers.append(IrMonitor(self.event_queue, self.config.ir_gpio_pin))
        if self.config.enable_usb_remote:
            self.input_handlers.append(UsbRemoteMonitor(self.event_queue, self.config.keyboard_event_type))

        for _ih in self.input_handlers:
            _ih.start()

    def stop(self):
        if self.event_queue:
            self.event_queue.stop()
        for _ih in self.input_handlers:
            _ih.stop()
            _ih.join()
        if 'spotify' in self.handlers:
            self.handlers['spotify'].stop()

    def get_handler(self, handler_name):
        if handler_name in self.handlers:
            return self.handlers[handler_name]
        return None

    @staticmethod
    def _wait_for_moode():
        start = time()
        while True:
            try:
                if MoodeHandler().read_cfg_system():
                    return
            except ConnectionError:
                pass

            if time() - start > INIT_TIMEOUT:
                raise TimeoutError("Timeout while waiting for Moode to initialize")

            sleep(5)

    def _logger_init(self):
        self.logger.setLevel("DEBUG")

        formatter = Formatter("%(asctime)s - %(name)s:%(levelname)s - %(message)s")
        stream = StreamHandler()
        stream.setLevel(self.config.logging["level"])
        stream.setFormatter(formatter)
        self.logger.propagate = False

        self.logger.addHandler(stream)

        # Rotate every day, keep for 3 days
        log_file_name = path.join(DIR, 'logs', 'main.log')

        if not path.exists(path.dirname(log_file_name)):
            makedirs(path.dirname(log_file_name))

        file_handler = TimedRotatingFileHandler(filename=log_file_name,
                                                when='midnight', interval=1, backupCount=3)
        file_handler.setLevel(self.config.logging["file_level"])
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

        basicConfig(format="%(asctime)s - %(name)s:%(levelname)s - %(message)s",
                    level=self.config.logging["global_level"])
        if self.config.logging["log_all_to_file"]:
            getLogger().addHandler(file_handler)

    def verify_commands(self):

        for command_dict in self.commands.values():
            for command in command_dict.values():
                assert 'target' in command, f'\'target\' missing from {command_dict}'
                if command['target'] in self.handlers:
                    handler = self.handlers[command['target']]
                    handler.verify(command)

    def load_keymap(self, file_name=None):
        self.keymap.clear()
        remotes = self.config.remotes if not file_name else [file_name]
        for keymap_name in remotes:
            if not path.exists(path.join(DIR, 'keymaps', keymap_name)):
                self.logger.error(f'File not found: {keymap_name}!')
                continue
            with open(path.join(DIR, 'keymaps', keymap_name), 'r') as keymap_file:
                keymap: Dict[str, List] = json.load(keymap_file)
                for key_name, codes in keymap.items():
                    if isinstance(codes, str):
                        # Keymap description fields
                        self.keymap[key_name] = codes

                    if key_name not in self.keymap:
                        self.keymap[key_name] = list()

                    for code in codes:
                        if code not in self.keymap[key_name]:
                            self.keymap[key_name].append(code)

    def load_commands(self):
        with open(path.join(DIR, 'commands', 'base.json'), 'r') as commands_file:
            self.commands = json.load(commands_file)

        if path.exists(path.join(DIR, 'commands', 'custom.json')):
            with open(path.join(DIR, 'commands', 'custom.json'), 'r') as commands_file:
                custom_commands: Dict = json.load(commands_file)
                for key, value in custom_commands.items():
                    if key in self.commands:
                        self.logger.warning(
                            f'"{key}" is duplicated. Value from "custom.json" replaces value from "base.json"!')
                    self.commands[key] = value
        else:
            self.logger.warning('custom.json file not found!')

    def record_key(self) -> list:
        codes = []
        return_codes = []
        while True:
            code = self.event_queue.dequeue()
            if code is None:
                continue

            if codes and code == codes[-1]:
                # Same code twice in a row
                return [deepcopy(code)]
            else:
                # Some remotes use 2 alternating codes for the same button
                if code in codes and code not in return_codes:
                    return_codes.append(deepcopy(code))

                codes.append(deepcopy(code))

                if len(return_codes) == 2:
                    return return_codes

            print('\t\tPress the key again to verify')

    def setup(self, file_name):
        try:
            self.load_keymap(file_name)

            print(f'Running setup of {file_name}')

            for key_name in self.commands.keys():
                while True:
                    recorded_len = len(self.keymap[key_name]) if key_name in self.keymap else 0
                    action = input(f'Button "{key_name}" \t(recorded: {recorded_len}) '
                                   f'[(R)ecord / (D)elete last / (C)lear all / (N)ext / (E)nd]: ')
                    if action.lower() == 'r':
                        codes = self.record_key()

                        if key_name not in self.keymap:
                            self.keymap[key_name] = list()

                        for code in codes:
                            if code not in self.keymap[key_name]:
                                self.keymap[key_name].append(code)

                    elif action.lower() == 'd':
                        if self.keymap[key_name]:
                            self.keymap[key_name].pop(-1)

                    elif action.lower() == 'c':
                        self.keymap[key_name] = list()

                    elif action.lower() == 'n':
                        if key_name in self.keymap and len(self.keymap[key_name]) == 0:
                            del self.keymap[key_name]
                        break

                    elif action.lower() == 'e':
                        if key_name in self.keymap and len(self.keymap[key_name]) == 0:
                            del self.keymap[key_name]
                        return

        finally:
            print(f'Setup result: \n{pformat(self.keymap)}')

            if self.keymap:
                with open(path.join(DIR, 'keymaps', file_name), 'w') as keymap_file:
                    json.dump(self.keymap, keymap_file, indent=2)

            self.load_keymap()

    def _execute(self, element: Tuple):
        (func, args) = element
        self.logger.debug(f"Running command {args}")
        try:
            func(*args)
        except Exception as e:
            self.logger.exception(e)

    def monitor(self, file_name=None):
        self.load_keymap(file_name=file_name)

        if file_name:
            self.logger.info(f'Loaded keymap {file_name}')

        if not self.keymap:
            self.logger.error("Keymap is empty! Please run 'setup' first.")
            sys.exit(1)

        diff = set(self.commands.keys()) - set(self.keymap.keys())
        if diff:
            self.logger.info(f'Some keys are missing from setup! \n\t{pformat(diff)}')

        self.logger.info('Monitoring started' + (f' (test mode)' if self.test_mode else ''))
        while True:
            code = self.event_queue.dequeue()
            try:
                key_name = None
                for _key, _codes in self.keymap.items():
                    if isinstance(_codes, str):
                        # Keymap description fields
                        continue

                    if code in _codes:
                        key_name = _key

                command = self.commands[key_name]
                if self.test_mode:
                    print(f'Key "{key_name}" received.')
                    continue
            except KeyError:
                continue

            if isinstance(command, tuple):
                self._execute(command)
            elif isinstance(command, dict):
                renderer = MoodeHandler().get_active_renderer()
                if renderer in command.keys():
                    commands = command[renderer]
                elif 'global' in command.keys():
                    commands = command['global']
                else:
                    continue

                if not isinstance(commands, list):
                    commands = [commands]

                for command_dict in commands:
                    handler: BaseActionHandler = self.get_handler(command_dict['target'])
                    if handler:
                        self._execute((handler.call, [command_dict]))


if __name__ == '__main__':
    if '-h' in sys.argv[1:] or 'help' in sys.argv[1:]:
        print('')  # TODO

    _test_mode = 'test' in sys.argv[1:] or 'setup' in sys.argv[1:]
    controller_app = ControllerApp(test_mode=_test_mode)

    _file_name = 'default.json'
    for arg in sys.argv[1:]:
        if arg.endswith('json'):
            _file_name = arg
            break

    if 'setup' in sys.argv[1:]:
        controller_app.setup(_file_name)
        controller_app.stop()
        sys.exit()

    if _test_mode:
        controller_app.monitor(_file_name)
        controller_app.stop()
        sys.exit()

    controller_app.verify_commands()
    controller_app.monitor()
    controller_app.stop()
