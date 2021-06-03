from handlers.base_handler import BaseActionHandler
from handlers.spotify_auth import AuthServer
from spotipy.oauth2 import SpotifyOAuth
from spotipy import Spotify
from time import time, sleep
from typing import Dict


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

    def __init__(self, config: Dict):
        self.device_id = None

        if {'device_name', 'client_id', 'client_secret', 'redirect_uri', 'listen_ip'} <= config.keys() or \
                False in [bool(value) for value in config.values()]:
            print('ERROR')
            return

        self.spotify_auth = AuthHandler(
            listen_ip=config['auth_server_listen_ip'],
            listen_port=config['auth_server_listen_port'],
            client_id=config['client_id'],
            client_secret=config['client_secret'],
            redirect_uri=config['redirect_uri'],
            scope=SCOPE
        )

        self.spotify = Spotify(auth_manager=self.spotify_auth)

        try:
            self.device_id = self._get_id(config['device_name'])
        except TimeoutError as e:
            print(e)

        self.spotify_auth.initiated = True
        self.last_volume = 0

    def verify(self, command_dict):
        assert 'command' in command_dict
        assert isinstance(command_dict['command'], str)

        if command_dict['command'] in self.require_value:
            assert 'value' in command_dict
            assert isinstance(command_dict['value'], str) or isinstance(command_dict['value'], int)

    def call(self, command_dict):
        command = command_dict['command']

        if not self.device_id:
            # Spotify was not authenticated
            return

        device_status = self._get_device_status()
        if not device_status:
            print('ERROR')
            return

        if not device_status['is_active'] and command not in self.allowed_inactive:
            return

        current = self.spotify.current_playback()

        if command == 'toggle':
            if current['is_playing']:
                self.spotify.pause_playback(self.device_id)
            else:
                self.spotify.start_playback(self.device_id)
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
            self.spotify.shuffle(not current['shuffle_state'], self.device_id)
        elif command == 'repeat':
            repeat_values = ["track", "context", "off"]
            new = (repeat_values.index(current['repeat_state']) + 1) % 3
            self.spotify.shuffle(repeat_values[new], self.device_id)
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
        elif command == 'playlist':
            playlist_uri = self._find_playlist(command_dict['value'])
            if playlist_uri:
                self.spotify.start_playback(self.device_id, playlist_uri)
        elif command == 'album':
            album_uri = self._find_user_saved_album(command_dict['value'])
            if album_uri:
                self.spotify.start_playback(self.device_id, album_uri)

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
                return playlist['uri']
        return None

    def _find_user_saved_album(self, name):
        # TODO: Expand to multiple pages
        albums = self.spotify.current_user_saved_albums()
        for album in albums['items']:
            if album['album']['name'] == name:
                return album['album']['uri']
        return None
