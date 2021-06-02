from handlers.base_handler import BaseActionHandler
from handlers.shell import ShellCommandsHandler
from handlers.spotify import SpotifyHandler
from piir.io import receive
from piir.decode import decode
from pprint import pformat
from typing import Optional, List, Dict
from os import path
import json
import sys


class Config(object):

    def __init__(self):
        self.ir_gpio_pin: Optional[int] = None
        self.remotes: List[str] = []
        self.spotify: Dict[str, str] = {}

    def load(self):
        with open(path.join(path.realpath(__file__), 'config.json')) as file:
            config: Dict = json.load(file)
            for key, value in config.items():
                setattr(self, key, value)

        self.remotes.append('default.json')

    # TODO: Verify config


class IrHandler(object):

    def __init__(self, test_mode=False):
        self.test_mode = test_mode

        self.config: Config = Config()
        self.config.load()

        self.keymap: Dict[str, List] = dict()
        self.commands: Dict[str, Dict] = dict()

        self.handlers: Dict[str, BaseActionHandler] = {
            'shell': ShellCommandsHandler(),
            'spotify': SpotifyHandler(device_name=self.config.spotify['device_name'],
                                      client_id=self.config.spotify['client_id'],
                                      client_secret=self.config.spotify['client_secret'],
                                      redirect_uri=self.config.spotify['redirect_uri'],
                                      listen_ip=self.config.spotify['auth_server_listen_ip'],
                                      listen_port=self.config.spotify['auth_server_listen_port'])
        }

        self.load_commands()

    def call(self, action: dict):
        if 'global' in action.keys() and len(action) == 1:
            command_dict = action['global']
        else:
            # TODO: Read current renderer
            renderer = None
            if renderer in action.keys():
                command_dict = action[renderer]
            elif 'global' in action.keys():
                command_dict = action['global']
            else:
                return

        if command_dict['target'] in self.handlers:
            handler = self.handlers[command_dict['target']]
        else:
            return

        try:
            handler.call(command_dict)
        except Exception as e:
            # Do not fail script on exception
            print(e)

    @staticmethod
    def clear_keymap():
        with open(path.join(path.realpath(__file__), 'keymaps', 'default.json'), 'w+') as keymap_file:
            keymap_file.write('')

    def load_keymap(self, default_only=False):
        self.keymap.clear()
        remotes = self.config.remotes if not default_only else 'default.json'
        for keymap_name in remotes:
            with open(path.join(path.realpath(__file__), 'keymaps', keymap_name), 'r') as keymap_file:
                if keymap_file.read():
                    keymap: Dict[str, List] = json.load(keymap_file)
                    for key_name, codes in keymap.items():
                        if key_name not in self.keymap:
                            self.keymap[key_name] = list()

                        for code in codes:
                            if code not in self.keymap[key_name]:
                                self.keymap[key_name].append(code)

    def load_commands(self):
        with open(path.join(path.realpath(__file__), 'commands', 'base.json'), 'r') as commands_file:
            if commands_file.read():
                self.commands = json.load(commands_file)

        with open(path.join(path.realpath(__file__), 'commands', 'custom.json'), 'r') as commands_file:
            if commands_file.read():
                custom_commands: Dict = json.load(commands_file)
                for key, value in custom_commands.items():
                    assert key not in self.commands, f'Command "{key}" is duplicated!'
                    self.commands.update({key, value})

    def setup(self):
        try:
            self.load_keymap(default_only=True)

            for key_name in self.commands.keys():
                if key_name not in self.keymap.values():
                    while True:
                        action = input(f'Button "{key_name}" [(R)ecord / (N)ext / (E)nd]: ')
                        if action.lower() == 'r':
                            code = str(decode(receive(self.config.ir_gpio_pin)))
                            if key_name not in self.keymap:
                                self.keymap[key_name] = list()

                            if code not in self.keymap[key_name]:
                                print(f'Recorded "{code}"')
                                self.keymap[key_name].append(code)
                            else:
                                print(f'Already recorded "{code}"   ')

                        elif action.lower() == 'n':
                            break

                        elif action.lower() == 'e':
                            return
                else:
                    print(f'Button {key_name} already recorded')

            with open(path.join(path.realpath(__file__), 'keymaps', 'default.json'), 'w') as keymap_file:
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
            code = str(decode(receive(self.config.ir_gpio_pin)))

            if self.test_mode:
                print(f'Code "{code}" received.')
            try:
                key_name = None
                for _key, _codes in self.keymap.items():
                    if code in _codes:
                        key_name = _key

                command = self.commands[key_name]
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

    if 'setup' or 'clear' in sys.argv[1:]:
        sys.exit()

    ir_handler.monitor()
