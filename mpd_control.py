from handlers.base_handler import BaseActionHandler
from handlers.shell import ShellCommandsHandler
from handlers.spotify import SpotifyHandler
from handlers.moode import MoodeHandler
from handlers.bluetooth import BluetoothHandler
from piir.io import receive
from piir.decode import decode
from pprint import pformat
from typing import Optional, List, Dict
from os import path
from copy import deepcopy
import json
import sys


DIR = path.dirname(path.realpath(__file__))


class Config(object):

    def __init__(self):
        self.ir_gpio_pin: Optional[int] = None
        self.remotes: List[str] = []
        self.spotify: Dict[str, str] = {}

    def load(self):
        with open(path.join(DIR, 'config.json')) as file:
            config: Dict = json.load(file)
            for key, value in config.items():
                setattr(self, key, value)

        if 'default.json' not in self.remotes:
            self.remotes.append('default.json')


class IrHandler(object):

    def __init__(self, test_mode=False):
        self.test_mode = test_mode

        self.config: Config = Config()
        self.config.load()

        self.keymap: Dict[str, List] = dict()
        self.commands: Dict[str, Dict] = dict()

        if not self.test_mode:
            self.handlers: Dict[str, BaseActionHandler] = {
                'shell': ShellCommandsHandler(),
                'spotify': SpotifyHandler(config=self.config.spotify),
                'moode': MoodeHandler(),
                'bluetooth': BluetoothHandler()
            }

        self.load_commands()

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

            if renderer in ['bluetooth'] and command_dict['target'] != renderer:
                # It is not possible to disconnect BT server side, so only allow BT commands when BT is playing.
                return

            if command_dict['target'] in self.handlers:
                handler = self.handlers[command_dict['target']]
                try:
                    handler.call(command_dict)
                except Exception as e:
                    # Do not fail script on exception
                    print(e)

    def verify_commands(self):

        for command_dict in self.commands.values():
            for command in command_dict.values():
                assert 'target' in command, f'\'target\' missing from {command_dict}'
                if command_dict['target'] in self.handlers:
                    handler = self.handlers[command_dict['target']]
                    handler.verify(command_dict)

    @staticmethod
    def clear_keymap():
        with open(path.join(DIR, 'keymaps', 'default.json'), 'w+') as keymap_file:
            keymap_file.write('')

    def load_keymap(self, default_only=False):
        self.keymap.clear()
        remotes = self.config.remotes if not default_only else ['default.json']
        for keymap_name in remotes:
            with open(path.join(DIR, 'keymaps', keymap_name), 'r') as keymap_file:
                keymap: Dict[str, List] = json.load(keymap_file)
                for key_name, codes in keymap.items():
                    if key_name not in self.keymap:
                        self.keymap[key_name] = list()

                    for code in codes:
                        if code not in self.keymap[key_name]:
                            self.keymap[key_name].append(code)

    def load_commands(self):
        with open(path.join(DIR, 'commands', 'base.json'), 'r') as commands_file:
            self.commands = json.load(commands_file)

        with open(path.join(DIR, 'commands', 'custom.json'), 'r') as commands_file:
            custom_commands: Dict = json.load(commands_file)
            for key, value in custom_commands.items():
                assert key not in self.commands, f'Command "{key}" is duplicated!'
                self.commands.update({key: value})

    def _record_key(self):
        while True:
            code = decode(receive(self.config.ir_gpio_pin))
            if code:
                return code[0]

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
                if code in codes:
                    return_codes.append(deepcopy(code))
                else:
                    codes.append(deepcopy(code))

                if len(return_codes) == 2:
                    return codes

            print('Press the key again to verify')

    def setup(self):
        try:
            self.load_keymap(default_only=True)

            for key_name in self.commands.keys():
                if key_name not in self.keymap.values():
                    while True:
                        action = input(f'Button "{key_name}" [(R)ecord / (N)ext / (E)nd]: ')
                        if action.lower() == 'r':
                            codes = self._record()

                            if key_name not in self.keymap:
                                self.keymap[key_name] = list()

                            for code in codes:
                                if code not in self.keymap[key_name]:
                                    self.keymap[key_name].append(code)

                        elif action.lower() == 'n':
                            break

                        elif action.lower() == 'e':
                            return
                else:
                    print(f'Button {key_name} already recorded')

            with open(path.join(DIR, 'keymaps', 'default.json'), 'w') as keymap_file:
                json.dump(self.keymap, keymap_file, indent=2)

        finally:
            print(f'Setup result: \n{pformat(self.keymap)}')

            self.load_keymap()

    def monitor(self):
        self.load_keymap()

        if not self.keymap:
            print("Keymap is empty! Please run 'setup' first.")
            sys.exit(1)

        diff = set(self.commands.keys()) - set(self.keymap.values())
        if diff:
            print(f'Some keys are missing from setup! \n{pformat(diff)}')

        print('Monitoring started')
        while True:
            code = self._record_key()

            try:
                key_name = None
                for _key, _codes in self.keymap.items():
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

    ir_handler = IrHandler(test_mode='test' in sys.argv[1:])

    if 'clear' in sys.argv[1:]:
        ir_handler.clear_keymap()

    if 'setup' in sys.argv[1:]:
        ir_handler.setup()

    if 'setup' in sys.argv[1:] or 'clear' in sys.argv[1:]:
        sys.exit()

    ir_handler.verify_commands()
    ir_handler.monitor()
