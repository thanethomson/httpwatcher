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


def watch(static_root, watch_paths=None, on_reload=None, host='localhost', port=5555, server_base_path="/",
          watcher_interval=1.0, recursive=True, open_browser=True, open_browser_delay=1.0):
    """Initialises an HttpWatcherServer to watch the given path for changes. Watches until the IO loop
    is terminated, or a keyboard interrupt is intercepted.

    Args:
        static_root: The path whose contents are to be served and watched.
        watch_paths: The paths to be watched for changes. If not supplied, this defaults to the static root.
        on_reload: An optional callback to pass to the watcher server that will be executed just before the
            server triggers a reload in connected clients.
        host: The host to which to bind our server.
        port: The port to which to bind our server.
        server_base_path: If the content is to be served from a non-standard base path, specify it here.
        watcher_interval: The maximum refresh rate of the watcher server.
        recursive: Whether to monitor the watch path recursively.
        open_browser: Whether or not to automatically attempt to open the user's browser at the root URL of
            the project (default: True).
        open_browser_delay: The number of seconds to wait before attempting to open the user's browser.
    """
    server = httpwatcher.HttpWatcherServer(
        static_root,
        watch_paths=watch_paths,
        on_reload=on_reload,
        host=host,
        port=port,
        server_base_path=server_base_path,
        watcher_interval=watcher_interval,
        recursive=recursive,
        open_browser=open_browser,
        open_browser_delay=open_browser_delay
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
        '--version',
        action='store_true',
        help="Display the current version number and exit"
    )

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
        '-n', '--no-browser',
        action='store_true',
        default=False,
        help="Do not attempt to open a web browser at the server's base URL"
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        default=False,
        help="Enable verbose debug logging"
    )
    args = parser.parse_args()

    if args.version:
        print("httpwatcher v%s" % httpwatcher.__version__)
    else:
        watch_paths = args.watch
        if watch_paths is not None:
            watch_paths = [p.strip() for p in watch_paths.split(",") if len(p.strip()) > 0]

        logging.basicConfig(
            level=logging.DEBUG if args.verbose else logging.INFO,
            format='%(asctime)s\t%(name)s\t%(levelname)s\t%(message)s' if args.verbose else "%(message)s",
        )

        watch(
            args.root,
            watch_paths=watch_paths,
            host=args.host,
            port=args.port,
            server_base_path=args.base_path,
            open_browser=(not args.no_browser)
        )
