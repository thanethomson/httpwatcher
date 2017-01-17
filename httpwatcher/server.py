# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import os.path
import pkg_resources
import mimetypes
import datetime
import stat

from tornado import gen
import tornado.web
import tornado.websocket
import tornado.iostream

from httpwatcher.filesystem import FileSystemWatcher

import logging
logger = logging.getLogger(__name__)
mimetypes.init()

__all__ = [
    "HttpWatcherServer"
]


class HttpWatcherServer(tornado.web.Application):

    def __init__(self, watch_path, host="localhost", port=5555, server_base_path="/", watcher_interval=1.0,
                 recursive=True, **kwargs):
        self.watch_path = os.path.abspath(os.path.realpath(watch_path))
        assert os.path.exists(self.watch_path) and os.path.isdir(self.watch_path), \
            "Watch path must be an existing folder: %s" % self.watch_path

        self.host = host
        self.port = port
        self.server_base_path = ("/%s/" % server_base_path.strip("/")) if server_base_path != "/" else "/"
        self.watcher_interval = watcher_interval
        self.recursive = recursive
        self.livereload_js_path = os.path.abspath(os.path.realpath(pkg_resources.resource_filename(
            "httpwatcher",
            os.path.join("scripts", "livereload.js")
        )))
        logger.debug("livereload.js path: %s" % self.livereload_js_path)

        handlers = [
            (r"/livereload.js", LiveReloadStaticScriptHandler, {
                "path": self.livereload_js_path
            }),
            (r"/livereload", LiveReloadWebSocketHandler, {
                "watcher_server": self
            }),
            (r"%s(.*)" % self.server_base_path, LiveReloadStaticFileHandler, {
                "path": self.watch_path,
                "livereload_script_url": "http://%s:%d/livereload.js" % (self.host, self.port),
                "websocket_url": "ws://%s:%d/livereload" % (self.host, self.port)
            })
        ]
        super(HttpWatcherServer, self).__init__(handlers, **kwargs)
        # create our watcher instance for the watch path
        self.watcher = FileSystemWatcher(
            self.watch_path,
            on_changed=self.trigger_reload,
            interval=self.watcher_interval,
            recursive=recursive
        )
        self.connected_clients = set()

    def listen(self, **kwargs):
        super(HttpWatcherServer, self).listen(self.port, address=self.host, **kwargs)
        self.watcher.start()
        logger.info("Started HTTP watcher server at http://%s:%d%s" % (self.host, self.port, self.server_base_path))

    def shutdown(self):
        """Mechanism for cleanly shutting down the file system watcher. Must be called when Tornado's IO loop
        terminates."""
        logger.info("Shutting down HTTP watcher server...")
        self.watcher.shutdown()
        logger.info("HTTP watcher server terminated")

    def register_client(self, client):
        self.connected_clients.add(client)

    def deregister_client(self, client):
        if client in self.connected_clients:
            self.connected_clients.remove(client)

    def broadcast_to_clients(self, msg):
        logger.debug("Broadcasting message to %d connected client(s)" % len(self.connected_clients))
        for client in self.connected_clients:
            client.write_message(msg)

    @gen.coroutine
    def trigger_reload(self, *args):
        self.broadcast_to_clients({"command": "reload"})


class LiveReloadStaticFileHandler(tornado.web.RequestHandler):
    """Similar to tornado.web.StaticFileHandler, but without all of the caching mechanisms and with the
    WebSocket JavaScript injection ability."""

    WEBSOCKET_JS_TEMPLATE = '<script type="application/javascript" src="{livereload_script_url}"></script>\n' \
                            '<script type="application/javascript">livereload("{websocket_url}");</script>\n' \
                            '</body>'

    static_path = None
    default_filenames = ["index.html", "index.htm"]
    livereload_script_url = None
    websocket_url = None
    websocket_js_template = None
    request_abspath = None
    modified = None
    content_type = None

    stat_result = None

    def initialize(self, **kwargs):
        assert "path" in kwargs, "Path parameter for LiveReloadStaticFileHandler is missing"
        assert "livereload_script_url" in kwargs, "LiveReload script URL for LiveReloadStaticFileHandler is missing"
        assert "websocket_url" in kwargs, "WebSocket URL for LiveReloadStaticFileHandler is missing"

        self.static_path = kwargs.pop("path")
        assert os.path.isabs(self.static_path), "Path parameter for LiveReloadStaticFileHandler must be absolute"

        if "default_filenames" in kwargs:
            assert isinstance(kwargs["default_filenames"], list), \
                "Default filenames for LiveReloadStaticFileHandler must be supplied as a list"
            self.default_filenames = kwargs.pop("default_filenames")

        self.livereload_script_url = kwargs.pop("livereload_script_url")
        self.websocket_url = kwargs.pop("websocket_url")
        self.websocket_js_template = LiveReloadStaticFileHandler.WEBSOCKET_JS_TEMPLATE.format(
            livereload_script_url=self.livereload_script_url,
            websocket_url=self.websocket_url
        ).encode("utf-8")

    def head(self, path):
        return self.get(path, include_body=False)

    @gen.coroutine
    def get(self, path, include_body=True):
        if path == "":
            path = "/"

        abspath = self.validate_path(path, os.path.join(self.static_path, self.parse_url_path(path)))
        if abspath is None:
            return

        self.request_abspath = abspath
        self.stat_file()
        self.set_modified_time()
        self.set_content_type()
        self.set_headers()

        if include_body:
            content = self.get_content(self.request_abspath)
            if isinstance(content, bytes):
                content = [content]
            for chunk in content:
                try:
                    self.write(chunk)
                    yield self.flush()
                except tornado.iostream.StreamClosedError:
                    return
        else:
            assert self.request.method == "HEAD"

    def validate_path(self, url_path, abspath):
        if ".." in url_path or "~" in url_path:
            raise tornado.web.HTTPError(403, "Invalid request URI")

        # if it's an existing directory
        if os.path.exists(abspath) and os.path.isdir(abspath):
            if not url_path.endswith("/"):
                self.redirect(url_path+"/", permanent=True)
                return

            abspath = self.find_first_default_file(abspath)

        if not os.path.exists(abspath):
            raise tornado.web.HTTPError(404)

        if not os.path.isfile(abspath):
            raise tornado.web.HTTPError(403, "%s is not a file", url_path)

        return abspath

    def find_first_default_file(self, base_path):
        for filename in self.default_filenames:
            abspath = os.path.join(base_path, filename)
            if os.path.exists(abspath) and os.path.isfile(abspath):
                return abspath
        raise tornado.web.HTTPError(404)

    def set_modified_time(self):
        self.modified = datetime.datetime.utcfromtimestamp(
            self.stat_result[stat.ST_MTIME]
        )

    def stat_file(self):
        if self.stat_result is None:
            self.stat_result = os.stat(self.request_abspath)

    def set_content_type(self):
        self.content_type = self.guess_content_type(self.request_abspath)

    def set_headers(self):
        if self.modified is not None:
            self.set_header("Last-Modified", self.modified)

        if self.content_type is not None:
            self.set_header("Content-Type", self.content_type)

        self.set_header("Content-Length", self.get_content_size())

    def get_content_size(self):
        if self.content_type == "text/html":
            return len([h for h in self.get_content(self.request_abspath)][0])
        else:
            return self.stat_result[stat.ST_SIZE]

    def get_content(self, abspath, start=None, end=None):
        # if it's an HTML file
        if self.content_type == "text/html":
            # read it all into memory at once, and insert our script tag
            with open(abspath, "rb") as file:
                yield file.read().replace(b"</body>", self.websocket_js_template)
            return
        else:
            with open(abspath, "rb") as file:
                yield file.read()
            return

    @classmethod
    def parse_url_path(cls, path):
        return os.path.join(*(path.strip("/").split("/")))

    @classmethod
    def guess_content_type(cls, abspath):
        mime_type, encoding = mimetypes.guess_type(abspath)
        if encoding == "gzip":
            return "application/gzip"
        elif encoding is not None:
            return "application/octet-stream"
        elif mime_type is not None:
            return mime_type
        else:
            return "application/octet-stream"


class LiveReloadStaticScriptHandler(tornado.web.RequestHandler):

    path = None
    contents = None

    def initialize(self, **kwargs):
        assert "path" in kwargs and os.path.exists(kwargs['path']) and os.path.isabs(kwargs['path']) and \
            os.path.isfile(kwargs['path']), \
            "LiveReloadStaticScriptHandler expects an absolute filesystem path for the livereload.js script file"
        self.path = kwargs['path']
        with open(self.path, "rb") as f:
            self.contents = f.read()

    @gen.coroutine
    def get(self, *args, **kwargs):
        self.set_header("Content-Type", "application/javascript")
        self.set_header("Content-Length", len(self.contents))

        try:
            self.write(self.contents)
            yield self.flush()
        except tornado.iostream.StreamClosedError:
            return


class LiveReloadWebSocketHandler(tornado.websocket.WebSocketHandler):

    watcher_server = None

    def initialize(self, **kwargs):
        assert "watcher_server" in kwargs, "Watcher server must be supplied to LiveReloadWebSocketHandler"
        self.watcher_server = kwargs.pop('watcher_server')
        super(LiveReloadWebSocketHandler, self).initialize()

    def open(self, *args, **kwargs):
        self.watcher_server.register_client(self)
        logger.debug("Client WebSocket connection opened")

    def on_close(self):
        self.watcher_server.deregister_client(self)
        logger.debug("Client WebSocket connection closed")

    def on_message(self, message):
        logger.debug("Ignoring message from WebSocket client: %s" % message)
