# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import os.path

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from tornado import gen
from tornado.ioloop import PeriodicCallback, IOLoop
from tornado.queues import Queue

import logging
logger = logging.getLogger(__name__)

__all__ = [
    "FileSystemWatcher"
]


class FileSystemWatcher(object):

    def __init__(self, watch_path, on_changed=None, interval=1.0, recursive=True):
        """Constructor.

        Args:
            watch_path: The filesystem path to watch for changes.
            on_changed: Callback to call when one or more changes to the watch path are detected.
            interval: The minimum interval at which to notify about changes (in seconds).
            recursive: Should the watch path be monitored recursively for changes?
        """
        assert os.path.isdir(watch_path), "Invalid watch path specified for file system watcher: %s" % watch_path
        self.watch_path = watch_path
        self.interval = interval * 1000.0
        self.recursive = recursive
        self.periodic_callback = PeriodicCallback(self.check_fs_events, self.interval)
        self.on_changed = on_changed
        self.observer = Observer()
        self.observer.schedule(
            WatcherEventHandler(self),
            self.watch_path,
            self.recursive
        )
        self.started = False
        self.fs_event_queue = Queue()

    def track_event(self, event):
        self.fs_event_queue.put(event)

    @gen.coroutine
    def check_fs_events(self):
        drained_events = []
        while self.fs_event_queue.qsize() > 0:
            drained_events.append(self.fs_event_queue.get_nowait())
        if len(drained_events) > 0 and callable(self.on_changed):
            logger.debug("Detected %d file system change(s) - triggering callback" % len(drained_events))
            self.on_changed(drained_events)

    def start(self):
        if not self.started:
            self.observer.start()
            self.periodic_callback.start()
            self.started = True
            logger.debug("Started file system watcher for path: %s" % self.watch_path)

    def shutdown(self, timeout=None):
        if self.started:
            self.periodic_callback.stop()
            self.observer.stop()
            self.observer.join(timeout=timeout)
            self.started = False
            logger.debug("Shut down file system watcher for path: %s" % self.watch_path)


class WatcherEventHandler(FileSystemEventHandler):

    def __init__(self, watcher):
        super(WatcherEventHandler, self).__init__()
        self.watcher = watcher

    def on_any_event(self, event):
        logger.debug("WatcherEventHandler detected filesystem event: %s" % event)
        self.watcher.track_event(event)
