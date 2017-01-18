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


WATCHER_INTERVAL = float(os.environ.get('HTTPWATCHER_TEST_WATCHER_INTERVAL', 0.1))
CHECK_DELAY = float(os.environ.get('HTTPWATCHER_TEST_CHECK_DELAY', 0.2))


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
        logger.debug("Using CHECK_DELAY = %.3f" % CHECK_DELAY)

    def track_change_events(self, events):
        self.event_counter += len(events)
        logger.debug("Got %d incoming events" % len(events))

    def report_event_counter(self):
        c = self.event_counter
        self.event_counter = 0
        self.stop(c)

    def check_for_fs_events(self, should_be_none=False):
        IOLoop.current().call_later(CHECK_DELAY, lambda: self.report_event_counter())
        if should_be_none:
            self.assertEqual(0, self.wait(timeout=CHECK_DELAY*1.2))
        else:
            self.assertGreater(self.wait(timeout=CHECK_DELAY*1.2), 0)

    def test_basic_watcher(self):
        watcher = FileSystemWatcher(
            self.temp_path,
            on_changed=lambda events: self.track_change_events(events),
            interval=WATCHER_INTERVAL,
            recursive=True
        )
        watcher.start()

        logger.debug("Creating 2 files...")

        write_file(self.temp_path, "file1", "Test file 1 contents")
        write_file(self.temp_path, "file2", "Test file 2 contents")
        self.check_for_fs_events()

        logger.debug("Creating 1 directory...")
        os.makedirs(os.path.join(self.temp_path, "subfolder1"))
        self.check_for_fs_events()

        logger.debug("Doing nothing...")
        # do nothing for a bit - no filesystem events
        self.check_for_fs_events(True)

        logger.debug("Deleting 2 files...")
        os.remove(os.path.join(self.temp_path, "file1"))
        os.remove(os.path.join(self.temp_path, "file2"))
        self.check_for_fs_events()

        watcher.shutdown()

    def test_multi_path_watching(self):
        watch_paths = [os.path.join(self.temp_path, watch_path) for watch_path in ["watch1", "watch2"]]

        # create our 3 watch directories
        for p in watch_paths:
            os.makedirs(p)
        # this one should be ignored
        ignored_path = os.path.join(self.temp_path, "watch3")
        os.makedirs(ignored_path)

        watcher = FileSystemWatcher(
            watch_paths,
            on_changed=lambda events: self.track_change_events(events),
            interval=WATCHER_INTERVAL,
            recursive=True
        )
        watcher.start()

        logger.debug("Creating 1 file in base temp directory")
        write_file(self.temp_path, "file1", "Test file 1 contents")
        # should have no effect
        self.check_for_fs_events(True)

        logger.debug("Creating 1 file in watch1 directory")
        write_file(self.temp_path, os.path.join("watch1", "file1"), "Test file 1 contents")
        self.check_for_fs_events()

        logger.debug("Creating 1 file in ignored directory")
        write_file(self.temp_path, os.path.join("watch3", "ignored-file"), "This file should be ignored")
        # should have no effect
        self.check_for_fs_events(True)

        logger.debug("Creating 1 file in watch2 directory")
        write_file(self.temp_path, os.path.join("watch2", "file2"), "Test file 2 contents")
        self.check_for_fs_events()

        watcher.shutdown()
