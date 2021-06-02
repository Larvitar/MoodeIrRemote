from bottle import Bottle, request, ServerAdapter
from typing import Optional
from threading import Thread


class MyWSGIRefServer(ServerAdapter):
    """
    https://stackoverflow.com/questions/11282218/bottle-web-framework-how-to-stop
    @mike, @Basj
    """
    server = None

    def run(self, handler):
        from wsgiref.simple_server import make_server, WSGIRequestHandler
        if self.quiet:
            class QuietHandler(WSGIRequestHandler):
                def log_request(*args, **kw): pass
            self.options['handler_class'] = QuietHandler
        self.server = make_server(self.host, self.port, handler, **self.options)
        self.server.serve_forever()

    def stop(self):
        self.server.shutdown()


class AuthServer(object):

    def __init__(self, spotify_auth, listen_ip, listen_port):
        self._app = Bottle()

        self.listen_ip = listen_ip
        self.listen_port = listen_port

        self.spotify_auth = spotify_auth
        self.code = ''

        self._app.route('/', method='GET', callback=self.main)
        self._app.route('/auth', method='GET', callback=self.auth)

        self.server: Optional[MyWSGIRefServer] = None
        self.thread: Optional[Thread] = None

    def main(self):
        auth_url = self.spotify_auth.get_authorize_url()
        return f'<body style="background: #181818"><p align="center" style="display: block; margin-top: 5em;"><a ' \
               f'href="{auth_url}" style="background-color: #1ED760; color: #FFF; text-decoration: none; border: 1px ' \
               f'solid transparent; border-radius: 4px; align-items: center; display: inline-flex; padding-left: 1em;' \
               f' padding-right: 1em; "><span>Authenticate with <b>Spotify</b></span></a></p></body>'

    def auth(self):
        try:
            self.code = request.params['code']
        except Exception:
            return '<body style="background: #181818"><p align="center" style="display: block; margin-top: 5em;">' \
                   '<span style="background-color: #D61D39; color: #FFF; text-decoration: none; border: 1px solid ' \
                   'transparent; border-radius: 4px; align-items: center; display: inline-flex; padding-left: 1em; ' \
                   'padding-right: 1em; ">Authentication failed</span></p></body>'
        else:
            return '<body style="background: #181818"><p align="center" style="display: block; margin-top: 5em;">' \
                   '<span style="background-color: #1ED760; color: #FFF; text-decoration: none; border: 1px solid ' \
                   'transparent; border-radius: 4px; align-items: center; display: inline-flex; padding-left: 1em; ' \
                   'padding-right: 1em; ">Authentication success</span></p></body>'

    def start(self):
        self.server = MyWSGIRefServer(host=self.listen_ip, port=self.listen_port)
        self.thread = Thread(target=self._app.run, kwargs=dict(server=self.server))
        self.thread.start()

    def close(self):
        if self.server:
            self.server.stop()
            self.server = None

        if self.thread:
            self.thread.join()
            self.thread = None
