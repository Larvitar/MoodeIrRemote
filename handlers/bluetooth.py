from handlers.base_handler import BaseActionHandler
from subprocess import check_output, run, DEVNULL
from re import search


class BluetoothHandler(BaseActionHandler):

    # List of command that require a value
    require_value = ['vol_up', 'vol_dn']

    def __init__(self):
        self.last_volume = 0

    @staticmethod
    def _get_device_status():
        output = check_output(['amixer', '-D', 'bluealsa'])
        status = dict()
        if output:
            match = search(r'Simple mixer control \'(?P<device_name>.*)\',\d\s', output.decode('utf-8'))
            if match:
                status['device_name'] = match.group(1)
            match = search(r'\[(?P<volume>\d{1,3})%\]', output.decode('utf-8'))
            if match:
                status['volume'] = match.group(1)

        return status

    @staticmethod
    def _send_amixer_command(ctype, device_name, command):
        run(['amixer', '-D', 'bluealsa', ctype, device_name, command], stdout=DEVNULL)

    def verify(self, command_dict):
        assert 'command' in command_dict, f'\'command\' missing from {command_dict}'
        assert isinstance(command_dict['command'], str), f'\'{command_dict["command"]}\' ' \
                                                         f'type({type(command_dict["command"])}) value is not allowed!'

        if command_dict['command'] in self.require_value:
            assert 'value' in command_dict, f'\'value\' missing from {command_dict}'
            assert isinstance(command_dict['value'], str) or isinstance(command_dict['value'], int), \
                f'\'{command_dict["command"]}\' type({type(command_dict["command"])}) value is not allowed!'

    def call(self, command_dict):
        command = command_dict['command']

        # No point in disconnecting renderers since we're only running volume commands

        device_status = self._get_device_status()
        if 'device_name' not in device_status:
            return

        if command == 'vol_up':
            if 'volume' in device_status:
                vol = min(int(device_status['volume']) + int(command_dict['value']), 100)
                self._send_amixer_command('sset', device_status['device_name'], f'{vol}%')
        elif command == 'vol_dn':
            if 'volume' in device_status:
                vol = max(int(device_status['volume']) - int(command_dict['value']), 0)
                self._send_amixer_command('sset', device_status['device_name'], f'{vol}%')
        elif command == 'mute':
            if 'volume' in device_status:
                if self.last_volume == 0:
                    self.last_volume = device_status['volume']
                    self._send_amixer_command('sset', device_status['device_name'], '0%')
                else:
                    self._send_amixer_command('sset', device_status['device_name'], f'{self.last_volume}%')
                    self.last_volume = 0
