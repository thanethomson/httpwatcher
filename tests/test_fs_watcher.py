# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import os
import os.path

from tornado import gen
from tornado.queues import Queue
from tornado.ioloop import IOLoop
from tornado.testing import AsyncTestCase

from httpwatcher import FileSystemWatcher
from .utils import *

import logging
logger = logging.getLogger(__name__)


class TestFileSystemWatcher(AsyncTestCase):

    temp_path = None

    def setUp(self):
        super(TestFileSystemWatcher, self).setUp()

        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s\t%(name)s\t%(levelname)s\t%(message)s',
        )

        self.temp_path = init_temp_path()
        write_file(self.temp_path, "README", "This will be the first and only file in the temporary folder (for now)")

    def test_basic_watcher(self):

        tracked_events = Queue()

        @gen.coroutine
        def track_change_events(events):
            for e in events:
                tracked_events.put(e)

        @gen.coroutine
        def get_queue_size(callback):
            counter = 0
            while tracked_events.qsize() > 0:
                tracked_events.get_nowait()
                counter += 1
            callback(counter)

        watcher = FileSystemWatcher(self.temp_path, on_changed=track_change_events, interval=0.01, recursive=True)
        watcher.start()

        write_file(self.temp_path, "file1", "Test file 1 contents")
        write_file(self.temp_path, "file2", "Test file 2 contents")

        IOLoop.current().call_later(0.1, get_queue_size, self.stop)
        self.assertGreater(self.wait(), 0)

        os.makedirs(os.path.join(self.temp_path, "subfolder1"))

        IOLoop.current().call_later(0.1, get_queue_size, self.stop)
        self.assertGreater(self.wait(), 0)

        # do nothing for a bit - no filesystem events
        IOLoop.current().call_later(0.1, get_queue_size, self.stop)
        self.assertEqual(0, self.wait())

        os.unlink(os.path.join(self.temp_path, "file1"))
        os.unlink(os.path.join(self.temp_path, "file2"))

        IOLoop.current().call_later(0.1, get_queue_size, self.stop)
        self.assertGreater(self.wait(), 0)
