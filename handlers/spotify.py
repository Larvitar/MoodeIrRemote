from handlers.base_handler import BaseActionHandler
from spotipy.oauth2 import SpotifyOAuth
from spotipy import Spotify
from handlers.spotify_auth import AuthServer
from time import time, sleep


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
    allowed_inactive = ['playlist']
    # List of command that require a value
    require_value = ['seek', 'playlist', 'album']

    def __init__(self, device_name, client_id, client_secret, redirect_uri, listen_ip, listen_port):
        self.device_id = None

        if not device_name or not client_id or not client_secret or not redirect_uri or not listen_ip \
                or not listen_port:
            return

        self.spotify_auth = AuthHandler(
            listen_ip=listen_ip,
            listen_port=listen_port,
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scope=SCOPE
        )

        self.spotify = Spotify(auth_manager=self.spotify_auth)

        try:
            self.device_id = self._get_id(device_name)
        except TimeoutError as e:
            print(e)

        self.spotify_auth.initiated = True
        self.last_volume = 0

    def call(self, command_dict):
        if not self.device_id:
            # Spotify was not authenticated
            return

        device_status = self._get_device()
        if not device_status:
            print('ERROR')
            return

        command = command_dict['command']

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
        elif command == 'prev':
            self.spotify.previous_track(self.device_id)
        elif command == 'shuffle':
            self.spotify.shuffle(not current['shuffle_state'], self.device_id)
        elif command == 'repeat':
            repeat_values = ["track", "context", "off"]
            new = (repeat_values.index(current['repeat_state']) + 1) % 3
            self.spotify.shuffle(repeat_values[new], self.device_id)

        elif command == 'vol_up':
            self.spotify.volume(min(device_status['volume_percent'] + 2, 100), self.device_id)
        elif command == 'vol_dn':
            self.spotify.volume(max(device_status['volume_percent'] - 2, 0), self.device_id)
        elif command == 'mute':
            if self.last_volume == 0:
                self.last_volume = device_status['volume_percent']
                self.spotify.volume(0, self.device_id)
            else:
                self.spotify.volume(self.last_volume, self.device_id)
                self.last_volume = 0

        # Commands with a value
        elif command == 'seek':
            self.spotify.seek_track(int(current['progress_ms']) + int(command_dict['value']), self.device_id)
        elif command == 'playlist':
            playlist_uri = self._find_playlist(command_dict['value'])
            if not playlist_uri:
                # Playlist not found
                return
            self.spotify.start_playback(self.device_id, playlist_uri)
        elif command == 'album':
            album_uri = self._find_playlist(command_dict['value'])
            if not album_uri:
                # Album not found
                return
            self.spotify.start_playback(self.device_id, album_uri)

    def _get_id(self, device_name):
        for device in self.spotify.devices()['devices']:
            if device['name'] == device_name:
                return device['id']

        return None

    def _get_device(self):
        for device in self.spotify.devices()['devices']:
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
