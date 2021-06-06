from handlers.base_handler import BaseActionHandler
from typing import Optional
from time import sleep, time
from logging import getLogger
from urllib.parse import quote
import json
import requests


class MoodeHandler(BaseActionHandler):

    # List of command that require a value
    require_value = ['vol_up', 'vol_dn', 'playlist', 'radio', 'custom']

    def __init__(self):
        self.logger = getLogger('MoodeIrController.MoodeHandler')
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
        response = self._send_command('GET', 'moode.php?cmd=readcfgsystem')
        return json.loads(response.content.decode('utf-8'))

    def _read_mpd_status(self):
        response = self._send_command('GET', 'moode.php?cmd=getmpdstatus')
        return json.loads(response.content.decode('utf-8'))

    def verify(self, command_dict):
        assert 'command' in command_dict, f'\'command\' missing from {command_dict}'
        assert isinstance(command_dict['command'], str), f'\'{command_dict["command"]}\' ' \
                                                         f'type({type(command_dict["command"])}) value is not allowed!'

        if command_dict['command'] in self.require_value:
            assert 'value' in command_dict, f'\'value\' missing from {command_dict}'
            assert isinstance(command_dict['value'], str) or isinstance(command_dict['value'], int), \
                f'\'{command_dict["command"]}\' type({type(command_dict["command"])}) value is not allowed!'

    def disconnect_renderer(self, desired_state):

        active_renderer = self.get_active_renderer()
        if active_renderer != desired_state and active_renderer in self.svc_map:
            # Make sure nothing else is playing
            response = self._send_command('POST', 'moode.php?cmd=disconnect-renderer',
                                          data={'job': self.svc_map[active_renderer]})

            start_time = time()
            while time() - start_time < 15:     # Max 15s
                sleep(1)
                if self.get_active_renderer() == 'moode':
                    break

            self.logger.info(f"{active_renderer} disconnected")

            return response

    def _send_command(self, req_type, command, data=None):
        assert req_type in ['GET', 'POST']

        response = None
        if req_type == 'GET':
            response = requests.get(self.base_url + command)
        elif req_type == 'POST':
            assert data
            response = requests.post(self.base_url + command, data=data)

        if response and response.status_code != 200:
            self.logger.error(f'{response.status_code}: {response.content}')

        return response

    def call(self, command_dict):
        command = command_dict['command']
        current_status = self._read_mpd_status()

        self.disconnect_renderer(desired_state='moode')

        # Worker commands
        if command == 'poweroff':
            self._send_command('GET', 'moode.php?cmd=poweroff')
        elif command == 'reboot':
            self._send_command('GET', 'moode.php?cmd=reboot')

        # Moode commands
        elif command == 'play':
            self._send_command('GET', '?cmd=play')
        elif command == 'pause':
            self._send_command('GET', '?cmd=pause')
        elif command == 'toggle':
            if current_status['state'] == 'play':
                self._send_command('GET', '?cmd=pause')
            else:
                self._send_command('GET', '?cmd=play')
        elif command == 'next':
            self._send_command('GET', '?cmd=next')
        elif command == 'previous':
            self._send_command('GET', '?cmd=previous')
        elif command == 'random':
            random = (int(current_status['random']) + 1) % 2
            self._send_command('GET', 'index.php?cmd=random+{value}'.format(value=random))
        elif command == 'repeat':
            repeat = (int(current_status['repeat']) + 1) % 2
            self._send_command('GET', 'index.php?cmd=repeat+{value}'.format(value=repeat))
        elif command == 'disconnect-renderer':
            self.disconnect_renderer(desired_state='moode')
        elif command == 'mute':
            self._send_command('GET', '?cmd=vol.sh+mute')
        elif command == 'fav-current-item':
            response = self._send_command('GET', 'moode.php?cmd=playlist')
            if response and response.status_code == 200:
                playlist = json.loads(response.content)
                if playlist and isinstance(playlist, list) and len(playlist) > int(current_status['song']):
                    playlist_element = playlist[int(current_status['song'])]
                    if isinstance(playlist_element, dict) and 'file' in playlist_element:
                        self._send_command('GET', 'moode.php?cmd=addfav&favitem=' +
                                           quote(playlist_element['file'], safe=''))

        # Commands with values
        elif command == 'vol_up':
            self._send_command('GET', '?cmd=vol.sh+up+{value}'.format(value=command_dict['value']))
        elif command == 'vol_dn':
            self._send_command('GET', '?cmd=vol.sh+dn+{value}'.format(value=command_dict['value']))
        elif command == 'playlist':
            self._send_command('POST', 'moode.php?cmd=clear_play_item', data={'path': command_dict['value']})
        elif command == 'radio':
            self._send_command('POST', 'moode.php?cmd=clear_play_item',
                               data={'path': f"RADIO/{command_dict['value']}.pls"})

        elif command == 'custom':
            # Allow for any other command as defined by user
            if 'data' in command_dict:
                self._send_command('POST', command_dict['value'], data=command_dict['data'])
            else:
                self._send_command('GET', command_dict['value'])
