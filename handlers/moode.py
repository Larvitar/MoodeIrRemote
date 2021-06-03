from typing import Optional
from handlers.base_handler import BaseActionHandler
import requests
import sqlite3


class MoodeHandler(BaseActionHandler):

    def __init__(self):
        self.db_path = '/var/local/www/db/moode-sqlite3.db'
        self.base_url = 'http://localhost/command/'
        self.name_map = {
            'spotactive': 'spotify',
            'btactive': 'bluetooth'
        }

    def get_active_renderer(self) -> Optional[str]:
        # TODO: Check if file is accessible
        conn = sqlite3.connect(self.db_path)
        records = conn.execute("SELECT param, value FROM cfg_system WHERE param IN ('rbactive', 'aplactive',"
                               " 'btactive', 'slactive', 'spotactive', 'inpactive')")
        players = dict(records)
        conn.close()

        for player, value in players:
            if int(value):
                if player in self.name_map:
                    return self.name_map[player]
                else:
                    return player

        return 'moode'

    def _set_to_db(self, table, param, value):
        conn = sqlite3.connect(self.db_path)
        conn.execute(f"UPDATE {table} SET value='{value}' WHERE param='{param}")
        conn.close()

    def _read_cfg_system(self):
        response = requests.get(self.base_url + 'moode.php?cmd=readcfgsystem')
        return eval(response.content.decode('utf-8'))

    def _read_mpd_status(self):
        response = requests.get(self.base_url + 'moode.php?cmd=getmpdstatus')
        return eval(response.content.decode('utf-8'))

    def call(self, command_dict):
        command = command_dict['command']
        current_config = self._read_cfg_system()
        current_status = self._read_mpd_status()
        # active_renderer = self.get_active_renderer()

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
            response = requests.get(self.base_url + 'moode.php?cmd=disconnect-renderer')
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

        print(response)
