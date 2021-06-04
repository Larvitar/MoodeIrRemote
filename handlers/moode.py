from handlers.base_handler import BaseActionHandler
from typing import Optional
import json
import requests


class MoodeHandler(BaseActionHandler):

    # List of command that require a value
    require_value = ['vol_up', 'vol_dn', 'playlist', 'radio']

    def __init__(self):
        self.base_url = 'http://localhost/command/'
        self.renderers = {
            'rbactive': 'roonbridge',
            'aplactive': 'airplay',
            'btactive': 'bluetooth',
            'slactive': 'squeezelite',
            'spotactive': 'spotify',
            'inpactive': 'input'
        }

        self.svc_map = {
            'roonbridge': 'rbsvc',
            'airplay': 'airplaysvc',
            'bluetooth': 'btsvc',
            'squeezelite': 'slsvc',
            'spotify': 'spotifysvc',
            'input': 'gpio_svc'     # maybe?
        }

    def get_active_renderer(self) -> Optional[str]:
        sys_config = self.read_cfg_system()

        for config_name, player in self.renderers.items():
            if config_name in sys_config and int(sys_config[config_name]) == 1:
                return player

        return 'moode'

    def read_cfg_system(self):
        response = requests.get(self.base_url + 'moode.php?cmd=readcfgsystem')
        return json.loads(response.content.decode('utf-8'))

    def _read_mpd_status(self):
        response = requests.get(self.base_url + 'moode.php?cmd=getmpdstatus')
        return json.loads(response.content.decode('utf-8'))

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
        current_status = self._read_mpd_status()

        active_renderer = self.get_active_renderer()
        if active_renderer != 'moode':
            # Make sure nothing else is playing
            requests.post(self.base_url + 'moode.php?cmd=disconnect-renderer',
                          data={'job': self.svc_map[active_renderer]})

        response = None
        # Worker commands
        if command == 'poweroff':
            response = requests.get(self.base_url + 'moode.php?cmd=poweroff')
        elif command == 'reboot':
            response = requests.get(self.base_url + 'moode.php?cmd=reboot')

        # Moode commands
        elif command == 'play':
            response = requests.get(self.base_url + '?cmd=play')
        elif command == 'pause':
            response = requests.get(self.base_url + '?cmd=pause')
        elif command == 'toggle':
            if current_status['state'] == 'play':
                response = requests.get(self.base_url + '?cmd=pause')
            else:
                response = requests.get(self.base_url + '?cmd=play')
        elif command == 'next':
            response = requests.get(self.base_url + '?cmd=next')
        elif command == 'previous':
            response = requests.get(self.base_url + '?cmd=previous')
        elif command == 'random':
            random = (int(current_status['random']) + 1) % 2
            response = requests.get(self.base_url + 'index.php?cmd=random+{value}'.format(value=random))
        elif command == 'repeat':
            repeat = (int(current_status['repeat']) + 1) % 2
            response = requests.get(self.base_url + 'index.php?cmd=repeat+{value}'.format(value=repeat))
        elif command == 'disconnect-renderer':
            response = requests.post(self.base_url + 'moode.php?cmd=disconnect-renderer',
                                     data={'job': self.svc_map[active_renderer]})
        elif command == 'mute':
            response = requests.get(self.base_url + '?cmd=vol.sh+mute')

        # Commands with values
        elif command == 'vol_up':
            response = requests.get(self.base_url + '?cmd=vol.sh+up+{value}'.format(value=command_dict['value']))
        elif command == 'vol_dn':
            response = requests.get(self.base_url + '?cmd=vol.sh+dn+{value}'.format(value=command_dict['value']))
        elif command == 'playlist':
            response = requests.post(self.base_url + 'moode.php?cmd=clear_play_item',
                                     data={'path': command_dict['value']})
        elif command == 'radio':
            response = requests.post(self.base_url + 'moode.php?cmd=clear_play_item',
                                     data={'path': 'RADIO/' + command_dict['value']})

        elif command == 'custom':
            # Allow for any other command as defined by user
            if 'data' in command_dict:
                response = requests.post(self.base_url + command_dict['value'], data=command_dict['data'])
            else:
                response = requests.post(self.base_url + command_dict['value'])

        print(f'{response.status_code}: {response.content}')
