# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import os
import os.path

from tornado.testing import AsyncTestCase
from tornado.httpclient import AsyncHTTPClient
from tornado.websocket import websocket_connect
from tornado.ioloop import IOLoop
from tornado.queues import Queue
import html5lib

from httpwatcher import HttpWatcherServer

from .utils import *

import json
import logging


class TestHttpWatcherServer(AsyncTestCase):

    temp_path = None
    watcher_server = None
    expected_httpwatcher_js = read_resource(os.path.join("scripts", "httpwatcher.min.js"))
    reload_tracker_queue = None

    def setUp(self):
        super(TestHttpWatcherServer, self).setUp()

        # by default, only log warning messages
        logging.basicConfig(
            level=logging.WARNING,
            format='%(asctime)s\t%(name)s\t%(levelname)s\t%(message)s',
        )
        debug_packages = os.environ.get('DEBUG_PACKAGES', 'httpwatcher').split(',')
        for pkg in debug_packages:
            pkg_logger = logging.getLogger(pkg)
            pkg_logger.setLevel(logging.DEBUG)

        self.temp_path = init_temp_path()
        write_file(
            self.temp_path,
            "index.html",
            "<!DOCTYPE html><html><head><title>Hello world</title></head>" +
            "<body>Test</body></html>"
        )
        self.subfolder_path = os.path.join(self.temp_path, "subfolder")
        os.makedirs(self.subfolder_path)
        write_file(
            self.subfolder_path,
            "index.html",
            "<!DOCTYPE html><html><head><title>Level 1 Test</title></head>" +
            "<body>Level 1 Test Body</body></html>"
        )
        self.subsubfolder_path = os.path.join(self.subfolder_path, "subsubfolder")
        os.makedirs(self.subsubfolder_path)
        write_file(
            self.subsubfolder_path,
            "index.html",
            "<!DOCTYPE html><html><head><title>Level 2 Test</title></head>" +
            "<body>Level 2 Test Body</body></html>"
        )
        self.reload_tracker_queue = Queue()

    def test_watching(self):
        self.watcher_server = HttpWatcherServer(
            self.temp_path,
            host="localhost",
            port=5555,
            watcher_interval=0.1
        )
        self.watcher_server.listen()
        self.exec_watch_server_tests("/")
        self.watcher_server.shutdown()

    def test_watching_non_standard_base_path(self):
        self.watcher_server = HttpWatcherServer(
            self.temp_path,
            host="localhost",
            port=5555,
            watcher_interval=0.1,
            server_base_path="/non-standard/"
        )
        self.watcher_server.listen()
        self.exec_watch_server_tests("/non-standard/")
        self.watcher_server.shutdown()

    def track_reload_custom(self):
        self.reload_tracker_queue.put("Gotcha!")

    def test_custom_callback(self):
        # starts off empty
        self.assertEqual(self.reload_tracker_queue.qsize(), 0)

        self.watcher_server = HttpWatcherServer(
            self.temp_path,
            on_reload=lambda: self.track_reload_custom(),
            host="localhost",
            port=5555,
            watcher_interval=0.1
        )
        self.watcher_server.listen()
        self.exec_watch_server_tests("")
        # make sure our custom callback has been called
        self.assertGreater(self.reload_tracker_queue.qsize(), 0)
        self.watcher_server.shutdown()

    def exec_watch_server_tests(self, base_path):
        _base_path = base_path.strip('/')
        if _base_path:
            _base_path += "/"
        client = AsyncHTTPClient()
        client.fetch("http://localhost:5555/%s" % _base_path, self.stop)
        response = self.wait()

        self.assertEqual(200, response.code)
        html = html5lib.parse(response.body)
        ns = get_html_namespace(html)
        self.assertEqual("Hello world", html_findall(html, ns, "./{ns}head/{ns}title")[0].text.strip())

        script_tags = html_findall(html, ns, "./{ns}body/{ns}script")
        self.assertEqual(2, len(script_tags))
        self.assertEqual("http://localhost:5555/httpwatcher.min.js", script_tags[0].attrib['src'])
        self.assertEqual('httpwatcher("ws://localhost:5555/httpwatcher");', script_tags[1].text.strip())

        # if it's a non-standard base path
        if len(_base_path) > 0:
            # we shouldn't be able to find anything at the root base path
            client.fetch("http://localhost:5555/", self.stop)
            response = self.wait()
            self.assertEqual(404, response.code)

        # test a file from the sub-path
        client.fetch(
            "http://localhost:5555/%ssubfolder/" % _base_path,
            self.stop
        )
        response = self.wait()
        self.assertEqual(200, response.code)
        html = html5lib.parse(response.body)
        ns = get_html_namespace(html)
        self.assertEqual(
            "Level 1 Test",
            html_findall(html, ns, "./{ns}head/{ns}title")[0].text.strip()
        )

        # test fetching from the sub-path without a trailing slash
        client.fetch(
            "http://localhost:5555/%ssubfolder" % _base_path,
            self.stop
        )
        response = self.wait()
        self.assertEqual(200, response.code)

        # test a file from the sub-sub-path
        client.fetch(
            "http://localhost:5555/%ssubfolder/subsubfolder/" % _base_path,
            self.stop
        )
        response = self.wait()
        self.assertEqual(200, response.code)
        html = html5lib.parse(response.body)
        ns = get_html_namespace(html)
        self.assertEqual(
            "Level 2 Test",
            html_findall(html, ns, "./{ns}head/{ns}title")[0].text.strip()
        )

        # test fetching from the sub-sub-path without a trailing slash
        client.fetch(
            "http://localhost:5555/%ssubfolder/subsubfolder" % _base_path,
            self.stop
        )
        response = self.wait()
        self.assertEqual(200, response.code)

        # fetch the httpwatcher.min.js file
        client.fetch("http://localhost:5555/httpwatcher.min.js", self.stop)
        response = self.wait()

        self.assertEqual(200, response.code)
        self.assertEqual(self.expected_httpwatcher_js, response.body)

        # now connect via WebSockets
        websocket_connect("ws://localhost:5555/httpwatcher").add_done_callback(
            lambda future: self.stop(future.result())
        )
        websocket_client = self.wait()

        # trigger a watcher reload
        write_file(self.temp_path, "README.txt", "Hello world!")

        IOLoop.current().call_later(
            1.0,
            lambda: websocket_client.read_message(lambda future: self.stop(future.result()))
        )
        msg = json.loads(self.wait())
        self.assertIn("command", msg)
        self.assertEqual("reload", msg["command"])
