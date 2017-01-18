# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from past.builtins import basestring

import os.path

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from httpwatcher.errors import MissingFolderError

from tornado import gen
from tornado.ioloop import PeriodicCallback
from tornado.queues import Queue

import logging
logger = logging.getLogger(__name__)

__all__ = [
    "FileSystemWatcher"
]


class FileSystemWatcher(object):

    def __init__(self, watch_paths, on_changed=None, interval=1.0, recursive=True):
        """Constructor.

        Args:
            watch_paths: A list of filesystem paths to watch for changes.
            on_changed: Callback to call when one or more changes to the watch path are detected.
            interval: The minimum interval at which to notify about changes (in seconds).
            recursive: Should the watch path be monitored recursively for changes?
        """
        if isinstance(watch_paths, basestring):
            watch_paths = [watch_paths]

        watch_paths = [os.path.abspath(path) for path in watch_paths]
        for path in watch_paths:
            if not os.path.exists(path) or not os.path.isdir(path):
                raise MissingFolderError(path)

        self.watch_paths = watch_paths
        self.interval = interval * 1000.0
        self.recursive = recursive
        self.periodic_callback = PeriodicCallback(self.check_fs_events, self.interval)
        self.on_changed = on_changed
        self.observer = Observer()
        for path in self.watch_paths:
            self.observer.schedule(
                WatcherEventHandler(self),
                path,
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
            logger.debug("Started file system watcher for paths:\n%s" % "\n".join(self.watch_paths))

    def shutdown(self, timeout=None):
        if self.started:
            self.periodic_callback.stop()
            self.observer.stop()
            self.observer.join(timeout=timeout)
            self.started = False
            logger.debug("Shut down file system watcher for path:\n%s" % "\n".join(self.watch_paths))


class WatcherEventHandler(FileSystemEventHandler):

    def __init__(self, watcher):
        super(WatcherEventHandler, self).__init__()
        self.watcher = watcher

    def on_any_event(self, event):
        logger.debug("WatcherEventHandler detected filesystem event: %s" % event)
        self.watcher.track_event(event)
