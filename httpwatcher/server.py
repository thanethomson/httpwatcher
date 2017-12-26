# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import os.path
import pkg_resources
import mimetypes
import datetime
import stat
import webbrowser

from tornado import gen
import tornado.web
import tornado.websocket
import tornado.iostream
import tornado.ioloop

from httpwatcher.filesystem import FileSystemWatcher
from httpwatcher.errors import MissingFolderError

import logging
logger = logging.getLogger(__name__)
mimetypes.init()

__all__ = [
    "HttpWatcherServer"
]


class HttpWatcherServer(tornado.web.Application):

    def __init__(self, static_root, watch_paths=None, on_reload=None, host="localhost", port=5555,
                 server_base_path="/", watcher_interval=1.0, recursive=True, open_browser=False,
                 open_browser_delay=1.0, **kwargs):
        """Constructor for the HTTP watcher server.

        Args:
            static_root: The root path from which to serve static files.
            watch_paths: One or more paths to watch for changes. If not specified, it will be assumed that the
                static root is to be monitored for changes.
            on_reload: An optional callback to call prior to triggering the reload operation in connected clients.
            host: The host IP address to which to bind.
            port: The port to which to bind.
            server_base_path: If a non-standard base path is required for the server's static root, specify it here.
            watcher_interval: The maximum refresh rate of the watcher server, in seconds.
            recursive: Should the watch paths be monitored recursively?
            open_browser: Should this watcher server attempt to automatically open the user's default web browser
                at the root of the project?
            open_browser_delay: The number of seconds to wait until attempting to open the user's browser.
        """
        self.static_root = os.path.abspath(static_root)
        if not os.path.exists(self.static_root) or not os.path.isdir(self.static_root):
            raise MissingFolderError(self.static_root)

        self.watch_paths = watch_paths if watch_paths is not None else [static_root]

        if on_reload is not None:
            if not callable(on_reload):
                raise ValueError(
                    "If a callback is supplied for HttpWatcherServer, it must be callable"
                )
        self.on_reload = on_reload

        self.host = host
        self.port = port
        self.server_base_path = server_base_path.strip("/") if server_base_path else ""
        self.server_base_path = ("/%s/" % self.server_base_path) \
            if self.server_base_path else "/"
        self.watcher_interval = watcher_interval
        self.recursive = recursive
        self.open_browser = open_browser
        self.open_browser_delay = open_browser_delay
        self.httpwatcher_js_path = os.path.abspath(
            os.path.realpath(
                pkg_resources.resource_filename(
                    "httpwatcher",
                    os.path.join("scripts", "httpwatcher.min.js")
                )
            )
        )
        logger.debug("httpwatcher.min.js path: %s", self.httpwatcher_js_path)

        handlers = [
            (r"/httpwatcher.min.js", HttpWatcherStaticScriptHandler, {
                "path": self.httpwatcher_js_path
            }),
            (r"/httpwatcher", HttpWatcherWebSocketHandler, {
                "watcher_server": self
            }),
            (r"%s(.*)" % self.server_base_path, HttpWatcherStaticFileHandler, {
                "path": self.static_root,
                "httpwatcher_script_url": "http://%s:%d/httpwatcher.min.js" % (
                    self.host, self.port
                ),
                "websocket_url": "ws://%s:%d/httpwatcher" % (self.host, self.port),
                "server_base_path": self.server_base_path
            })
        ]
        super(HttpWatcherServer, self).__init__(handlers, **kwargs)
        # create our watcher instance for the watch path
        self.watcher = FileSystemWatcher(
            self.watch_paths,
            on_changed=self.trigger_reload,
            interval=self.watcher_interval,
            recursive=recursive
        )
        self.connected_clients = set()

    def listen(self, **kwargs):
        super(HttpWatcherServer, self).listen(self.port, address=self.host, **kwargs)
        self.watcher.start()
        logger.info(
            "Started HTTP watcher server at http://%s:%d%s",
            self.host, self.port, self.server_base_path
        )

        if self.open_browser:
            tornado.ioloop.IOLoop.current().call_later(
                self.open_browser_delay,
                self.trigger_browser_open
            )

    @gen.coroutine
    def trigger_browser_open(self):
        url = "http://%s:%d%s" % (self.host, self.port, self.server_base_path)
        logger.debug("Attempting to open user web browser at: %s", url)
        try:
            webbrowser.open(url)
        except:
            logger.exception("Failed to open user web browser")

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
        logger.debug(
            "Broadcasting message to %d connected client(s)",
            len(self.connected_clients)
        )
        for client in self.connected_clients:
            client.write_message(msg)

    @gen.coroutine
    def trigger_reload(self, *args):
        # call our callback first
        if callable(self.on_reload):
            self.on_reload()

        self.broadcast_to_clients({"command": "reload"})


class HttpWatcherStaticFileHandler(tornado.web.RequestHandler):
    """Similar to tornado.web.StaticFileHandler, but without all of the caching mechanisms and with the
    WebSocket JavaScript injection ability."""

    WEBSOCKET_JS_TEMPLATE = '<script type="application/javascript" src="{httpwatcher_script_url}"></script>\n' \
                            '<script type="application/javascript">httpwatcher("{websocket_url}");</script>\n' \
                            '</body>'

    static_path = None
    default_filenames = ["index.html", "index.htm"]
    httpwatcher_script_url = None
    websocket_url = None
    websocket_js_template = None
    request_abspath = None
    modified = None
    content_type = None

    stat_result = None

    def initialize(self, **kwargs):
        for param in ["path", "httpwatcher_script_url", "websocket_url", "server_base_path"]:
            if param not in kwargs:
                raise ValueError(
                    "Parameter \"%s\" for HttpWatcherStaticFileHandler is missing" % param
                )

        self.static_path = kwargs.pop("path")
        if not os.path.isabs(self.static_path):
            raise ValueError(
                "Parameter \"path\" for HttpWatcherStaticFileHandler must be absolute"
            )

        if "default_filenames" in kwargs:
            if not isinstance(kwargs["default_filenames"], list):
                raise ValueError(
                    "Default filenames for HttpWatcherStaticFileHandler must be supplied as a list"
                )
            self.default_filenames = kwargs.pop("default_filenames")

        self.httpwatcher_script_url = kwargs.pop("httpwatcher_script_url")
        self.websocket_url = kwargs.pop("websocket_url")
        self.websocket_js_template = HttpWatcherStaticFileHandler.WEBSOCKET_JS_TEMPLATE.format(
            httpwatcher_script_url=self.httpwatcher_script_url,
            websocket_url=self.websocket_url
        ).encode("utf-8")
        self.server_base_path = kwargs.pop('server_base_path')

    def head(self, path):
        return self.get(path, include_body=False)

    @gen.coroutine
    def get(self, path, include_body=True):
        if path == "":
            path = "/"

        abspath = self.validate_path(
            path,
            os.path.join(self.static_path, self.parse_url_path(path))
        )
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
                self.redirect(
                    "%s%s/" % (self.server_base_path, url_path.strip('/')),
                    permanent=True
                )
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


class HttpWatcherStaticScriptHandler(tornado.web.RequestHandler):

    path = None
    contents = None

    def initialize(self, **kwargs):
        if "path" not in kwargs or not os.path.exists(kwargs['path']) or \
                not os.path.isabs(kwargs['path']) or not os.path.isfile(kwargs['path']):
            raise ValueError(
                "HttpWatcherStaticScriptHandler expects an absolute filesystem path for the " +
                "httpwatcher.min.js script file"
            )
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


class HttpWatcherWebSocketHandler(tornado.websocket.WebSocketHandler):

    watcher_server = None

    def initialize(self, **kwargs):
        if "watcher_server" not in kwargs:
            raise ValueError("Watcher server must be supplied to HttpWatcherWebSocketHandler")
        self.watcher_server = kwargs.pop('watcher_server')
        super(HttpWatcherWebSocketHandler, self).initialize()

    def open(self, *args, **kwargs):
        self.watcher_server.register_client(self)
        logger.debug("Client WebSocket connection opened")

    def on_close(self):
        self.watcher_server.deregister_client(self)
        logger.debug("Client WebSocket connection closed")

    def on_message(self, message):
        logger.debug("Ignoring message from WebSocket client: %s", message)
