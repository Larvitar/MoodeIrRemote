from handlers.base_handler import BaseActionHandler
from handlers.spotify_auth import AuthServer
from handlers.moode import MoodeHandler
from spotipy.oauth2 import SpotifyOAuth
from spotipy import Spotify
from time import time, sleep
from typing import Dict
from logging import getLogger
from random import randint


SCOPE = ['user-read-playback-state', 'user-modify-playback-state', 'user-read-currently-playing',
         'user-read-recently-played', 'user-top-read', 'user-read-playback-position', 'playlist-read-private',
         'playlist-read-collaborative', 'user-library-read']
AUTH_TIMEOUT = 120


class AuthenticationException(Exception):
    pass


class AuthHandler(SpotifyOAuth):

    def __init__(self, listen_ip, listen_port, *args, **kwargs):
        super(AuthHandler, self).__init__(*args, **kwargs)
        self.auth_server = AuthServer(spotify_auth=self, listen_ip=listen_ip, listen_port=listen_port)
        self.initiated = False

    def get_auth_response(self, open_browser=None):
        if self.initiated:
            raise AuthenticationException("Authentication token expired! Restart and login again.")

        getLogger('MoodeIrController.AuthHandler').warning('Starting Spotify AuthServer.')
        self.auth_server.start()
        start_time = time()
        while not self.auth_server.code:
            sleep(0.1)
            if time() - start_time > AUTH_TIMEOUT:
                raise TimeoutError("Spotify authentication timeout!")
        self.auth_server.close()

        return self.auth_server.code


class SpotifyHandler(BaseActionHandler):

    # List of commands allowed in inactive mode
    allowed_inactive = ['playlist', 'album']
    # List of command that require a value
    require_value = ['vol_up', 'vol_dn', 'seek', 'playlist', 'album']

    def __init__(self, config: Dict, cache_path):
        self.logger = getLogger('MoodeIrController.SpotifyHandler')

        self.device_id = None
        self.device_name = None

        if {'client_id', 'client_secret', 'redirect_uri', 'listen_ip'} <= config.keys() or \
                False in [bool(value) for value in config.values()]:
            self.logger.error('Spotify config is missing')
            return

        self.spotify_auth = AuthHandler(
            listen_ip=config['auth_server_listen_ip'],
            listen_port=config['auth_server_listen_port'],
            client_id=config['client_id'],
            client_secret=config['client_secret'],
            redirect_uri=config['redirect_uri'],
            cache_path=cache_path,
            scope=SCOPE
        )

        self.spotify = Spotify(auth_manager=self.spotify_auth)

        try:
            self.device_name = MoodeHandler().read_cfg_system()['spotifyname']
            self.device_id = self._get_id(self.device_name)
        except TimeoutError as e:
            self.logger.exception(e)

        self.spotify_auth.initiated = True
        self.last_volume = 0

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

        device_name = MoodeHandler().read_cfg_system()['spotifyname']
        if device_name != self.device_name or not self.device_id:
            self.device_name = device_name
            self.device_id = None
            self.device_id = self._get_id(self.device_name)

        if not self.device_id:
            self.logger.debug('Spotify is not authenticated')
            return

        MoodeHandler().disconnect_renderer(desired_state='spotify')

        device_status = self._get_device_status()
        if not device_status:
            self.logger.error('Error when reading device ID')
            return

        if not device_status['is_active'] and command not in self.allowed_inactive:
            return

        if not device_status['is_active']:
            self.spotify.transfer_playback(self.device_id)

        current = self.spotify.current_playback()

        if command == 'toggle':
            if not current or not current['is_playing']:
                self.spotify.start_playback(self.device_id)
            else:
                self.spotify.pause_playback(self.device_id)
        elif command == 'pause':
            self.spotify.pause_playback(self.device_id)
        elif command == 'play':
            if device_status['is_active']:
                self.spotify.start_playback(self.device_id)
            else:
                self.spotify.transfer_playback(self.device_id)
        elif command == 'next':
            self.spotify.next_track(self.device_id)
        elif command == 'previous':
            self.spotify.previous_track(self.device_id)
        elif command == 'shuffle':
            if current:
                self.spotify.shuffle(not current['shuffle_state'], self.device_id)
        elif command == 'repeat':
            repeat_values = ["track", "context", "off"]
            new = (repeat_values.index(current['repeat_state']) + 1) % 3
            self.spotify.repeat(repeat_values[new], self.device_id)
        elif command == 'mute':
            if self.last_volume == 0:
                self.last_volume = device_status['volume_percent']
                self.spotify.volume(0, self.device_id)
            else:
                self.spotify.volume(self.last_volume, self.device_id)
                self.last_volume = 0

        # Commands with a value
        elif command == 'vol_up':
            self.spotify.volume(min(device_status['volume_percent'] + int(command_dict['value']), 100), self.device_id)
        elif command == 'vol_dn':
            self.spotify.volume(max(device_status['volume_percent'] - int(command_dict['value']), 0), self.device_id)
        elif command == 'seek':
            self.spotify.seek_track(int(current['progress_ms']) + int(command_dict['value']), self.device_id)
        elif command in ['playlist', 'album']:
            if command == 'playlist':
                uri, count = self._find_playlist(command_dict['value'])
            else:
                uri, count = self._find_user_saved_album(command_dict['value'])

            if uri:
                # None -> do not change, False -> disable, True -> enabled
                shuffle_state = False if not current else current['shuffle_state']
                shuffled = shuffle_state if 'shuffled' not in command_dict else command_dict['shuffled']

                if shuffled != shuffle_state:
                    self.spotify.shuffle(shuffled, self.device_id)
                offset = randint(0, count - 1) if shuffled else 0

                self.spotify.start_playback(self.device_id, context_uri=uri, offset={"position": offset})

    def _get_id(self, device_name):
        response = self.spotify.devices()
        if 'devices' not in response:
            return None

        for device in response['devices']:
            if device['name'] == device_name:
                return device['id']

        return None

    def _get_device_status(self):
        response = self.spotify.devices()
        if 'devices' not in response:
            return None

        for device in response['devices']:
            if device['id'] == self.device_id:
                return device
        return None

    def _find_playlist(self, name):
        # TODO: Expand to multiple pages
        playlists = self.spotify.current_user_playlists()
        for playlist in playlists['items']:
            if playlist['name'] == name:
                return playlist['uri'], playlist['tracks']['total']
        return None, None

    def _find_user_saved_album(self, name):
        # TODO: Expand to multiple pages
        albums = self.spotify.current_user_saved_albums()
        for album in albums['items']:
            if album['album']['name'] == name:
                return album['album']['uri'], album['album']['total_tracks']
        return None, None
