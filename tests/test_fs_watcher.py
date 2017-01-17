# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import os
import os.path

from tornado.ioloop import IOLoop
from tornado.testing import AsyncTestCase

from httpwatcher import FileSystemWatcher
from .utils import *

import logging
logger = logging.getLogger(__name__)


CHECK_DELAY = 0.1


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
        self.event_counter = 0

    def track_change_events(self, events):
        self.event_counter += len(events)

    def report_event_counter(self):
        c = self.event_counter
        self.event_counter = 0
        self.stop(c)

    def test_basic_watcher(self):
        watcher = FileSystemWatcher(
            self.temp_path,
            on_changed=lambda events: self.track_change_events(events),
            interval=0.01,
            recursive=True
        )
        watcher.start()

        write_file(self.temp_path, "file1", "Test file 1 contents")
        write_file(self.temp_path, "file2", "Test file 2 contents")

        IOLoop.current().call_later(CHECK_DELAY, lambda: self.report_event_counter())
        self.assertGreater(self.wait(), 0)

        os.makedirs(os.path.join(self.temp_path, "subfolder1"))

        IOLoop.current().call_later(CHECK_DELAY, lambda: self.report_event_counter())
        self.assertGreater(self.wait(), 0)

        # do nothing for a bit - no filesystem events
        IOLoop.current().call_later(CHECK_DELAY, lambda: self.report_event_counter())
        self.assertEqual(0, self.wait())

        os.remove(os.path.join(self.temp_path, "file1"))
        os.remove(os.path.join(self.temp_path, "file2"))

        IOLoop.current().call_later(CHECK_DELAY, lambda: self.report_event_counter())
        self.assertGreater(self.wait(), 0)

        watcher.shutdown()
