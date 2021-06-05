from handlers.base_handler import BaseActionHandler
from handlers.shell import ShellCommandsHandler
from handlers.spotify import SpotifyHandler
from handlers.moode import MoodeHandler
from handlers.bluetooth import BluetoothHandler
from piir.io import receive
from piir.decode import decode
from pprint import pformat
from typing import Optional, List, Dict
from os import path, makedirs
from copy import deepcopy
from logging import getLogger, StreamHandler, Formatter, basicConfig
from logging.handlers import TimedRotatingFileHandler
import json
import sys


DIR = path.dirname(path.realpath(__file__))


class Config(object):

    def __init__(self):
        self.ir_gpio_pin: Optional[int] = None
        self.remotes: List[str] = []
        self.spotify: Dict[str, str] = {}
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


class IrHandler(object):

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

        if not self.test_mode:
            self.handlers: Dict[str, BaseActionHandler] = {
                'shell': ShellCommandsHandler(),
                'spotify': SpotifyHandler(config=self.config.spotify),
                'moode': MoodeHandler(),
                'bluetooth': BluetoothHandler()
            }
        else:
            self.handlers: Dict[str, BaseActionHandler] = {}

        self.load_commands()

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

    def call(self, action: dict):
        renderer = MoodeHandler().get_active_renderer()
        if renderer in action.keys():
            commands = action[renderer]
        elif 'global' in action.keys():
            commands = action['global']
        else:
            return

        if not isinstance(commands, list):
            commands = [commands]

        for command_dict in commands:

            if command_dict['target'] in self.handlers:
                handler = self.handlers[command_dict['target']]
                try:
                    self.logger.debug(f"Running command {command_dict}")
                    handler.call(command_dict)
                except Exception as e:
                    # Do not fail script on exception
                    self.logger.exception(e)

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
                    assert key not in self.commands, f'Command "{key}" is duplicated!'
                    self.commands.update({key: value})
        else:
            self.logger.warning('custom.json file not found!')

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

    def _record_key(self):
        while True:
            code = decode(receive(self.config.ir_gpio_pin))
            parsed = self._parse_code(code)
            if parsed:
                self.logger.debug(f'Received code {parsed}')
                return parsed

    def _record(self):
        codes = []
        return_codes = []
        while True:
            code = self._record_key()
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
                        codes = self._record()

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
            code = self._record_key()

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

            self.call(command)


if __name__ == '__main__':
    if '-h' in sys.argv[1:] or 'help' in sys.argv[1:]:
        print('')  # TODO

    _test_mode = 'test' in sys.argv[1:] or 'setup' in sys.argv[1:]
    ir_handler = IrHandler(test_mode=_test_mode)

    _file_name = 'default.json'
    for arg in sys.argv[1:]:
        if arg.endswith('json'):
            _file_name = arg
            break

    if 'setup' in sys.argv[1:]:
        ir_handler.setup(_file_name)
        sys.exit()

    if _test_mode:
        ir_handler.monitor(_file_name)
    else:
        ir_handler.verify_commands()
        ir_handler.monitor()
