# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import argparse
import httpwatcher

import tornado.ioloop

import logging

__all__ = [
    "watch",
    "main"
]


def watch(static_root, watch_paths=None, host='localhost', port=5555, server_base_path="/", watcher_interval=1.0,
          recursive=True, verbose=False):
    """Initialises an HttpWatcherServer to watch the given path for changes. Watches until the IO loop
    is terminated, or a keyboard interrupt is intercepted.

    Args:
        static_root: The path whose contents are to be served and watched.
        watch_paths: The paths to be watched for changes. If not supplied, this defaults to the static root.
        host: The host to which to bind our server.
        port: The port to which to bind our server.
        server_base_path: If the content is to be served from a non-standard base path, specify it here.
        watcher_interval: The maximum refresh rate of the watcher server.
        recursive: Whether to monitor the watch path recursively.
        verbose: Whether or not to enable verbose debug logging.
    """
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format='%(asctime)s\t%(name)s\t%(levelname)s\t%(message)s' if verbose else "%(message)s",
    )

    server = httpwatcher.HttpWatcherServer(
        static_root,
        watch_paths=watch_paths,
        host=host,
        port=port,
        server_base_path=server_base_path,
        watcher_interval=watcher_interval,
        recursive=recursive
    )
    server.listen()

    try:
        tornado.ioloop.IOLoop.current().start()
    except KeyboardInterrupt:
        server.shutdown()


def main():
    parser = argparse.ArgumentParser(description="Web server library and command-line utility for serving static "
                                                 "files with live reload functionality")
    parser.add_argument(
        '-r', '--root',
        default=".",
        help="The root path containing the static files to be served (defaults to the current folder)"
    )
    parser.add_argument(
        '-w', '--watch',
        default=None,
        help="A comma-separated list of paths to watch for changes (defaults to the static root path)"
    )
    parser.add_argument(
        '-H', '--host',
        default='localhost',
        help="The host address to which to bind the web server (default: localhost)"
    )
    parser.add_argument(
        '-p', '--port',
        type=int,
        default=5555,
        help="The port to which to bind the web server (default: 5555)"
    )
    parser.add_argument(
        '-b', '--base-path',
        default='/',
        help="The base path from which the server is to serve content (default: /)"
    )
    parser.add_argument(
        '--version',
        action='store_true',
        help="Display the current version number and exit"
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        default=False,
        help="Enable verbose debug logging"
    )
    args = parser.parse_args()

    if args.version:
        print("httpwatcher %s" % httpwatcher.__version__)
    else:
        watch_paths = args.watch
        if watch_paths is not None:
            watch_paths = [p.strip() for p in watch_paths.split(",") if len(p.strip()) > 0]
        watch(
            args.root,
            watch_paths=watch_paths,
            host=args.host,
            port=args.port,
            server_base_path=args.base_path,
            verbose=args.verbose
        )
