httpwatcher
===========

Overview
--------

``httpwatcher`` is both a library and command-line utility for firing up
a simple HTTP server to serve static files from a specific root path.
Live reloading is triggered via web sockets.

**Note** that ``httpwatcher`` is intended for developers during testing
of their static web sites, and is not at all intended as a production
web server.

Requirements
------------

In order to install ``httpwatcher``, you will need:

-  Python 2.7+ or Python 3.5+
-  ``pip`` or ``easy_install``

Installation
------------

With your `virtual
environment <https://virtualenv.pypa.io/en/stable/>`__ active, run the
following:

.. code:: bash

    > pip install httpwatcher

To upgrade to the latest version of ``httpwatcher``, simply:

.. code:: bash

    > pip install -U httpwatcher

Usage
-----

``httpwatcher`` can either be used from the command line, or as a
drop-in library within your own Python application.

Command-Line Usage
~~~~~~~~~~~~~~~~~~

The quickest way to get up and running is to watch the current folder
and serve your content from ``http://localhost:5555`` as follows:

.. code:: bash

    # Also opens your web browser at http://localhost:5555
    > httpwatcher

    # To get more help
    > httpwatcher --help

With all possible options:

.. code:: bash

    > httpwatcher --root /path/to/html \      # static root from which to serve files
                  --watch "/path1,/path2" \   # comma-separated list of paths to watch (defaults to the static root)
                  --host 127.0.0.1 \          # bind to 127.0.0.1
                  --port 5556 \               # bind to port 5556
                  --base-path /blog/ \        # serve static content from http://127.0.0.1:5556/blog/
                  --verbose                   # enable verbose debug logging
                  --no-browser                # causes httpwatcher to not attempt to open your web browser automatically

Library Usage
~~~~~~~~~~~~~

Make sure ``httpwatcher`` is installed as a dependency for your Python
project, and then:

.. code:: python

    import httpwatcher

    # Just watch /path/to/html, and serve from that same path
    httpwatcher.watch("/path/to/html")

**Note** that, unlike ``HttpWatcherServer``, the ``httpwatcher.watch``
function automatically assumes that you want to open your default web
browser at the base URL of the served site. To avoid this, do the
following:

.. code:: python

    import httpwatcher

    httpwatcher.watch("/path/to/html", open_browser=False)

To use the watcher server directly and have more control over the I/O
loop:

.. code:: python

    from httpwatcher import HttpWatcherServer
    from tornado.ioloop import IOLoop

    def custom_callback():
        print("Web server reloading!")

    server = HttpWatcherServer(
        "/path/to/html",                      # serve files from the folder /path/to/html
        watch_paths=["/path1", "/path2"],     # watch these paths for changes
        on_reload=custom_callback,            # optionally specify a custom callback to be called just before the server reloads
        host="127.0.0.1",                     # bind to host 127.0.0.1
        port=5556,                            # bind to port 5556
        server_base_path="/blog/",            # serve static content from http://127.0.0.1:5556/blog/
        watcher_interval=1.0,                 # maximum reload frequency (seconds)
        recursive=True,                       # watch for changes in /path/to/html recursively
        open_browser=True                     # automatically attempt to open a web browser (default: False for HttpWatcherServer)
    )
    server.listen()

    try:
        # will keep serving until someone hits Ctrl+C
        IOLoop.current().start()
    except KeyboardInterrupt:
        server.shutdown()

``httpwatcher.watch`` takes mostly the same parameters as the
constructor parameters for ``HttpWatcherServer`` (except, as mentioned
earlier, for the ``open_browser`` parameter). It's just a convenience
method provided to instantiate and run a simple ``HttpWatcherServer``.

Inner Workings
--------------

``httpwatcher`` makes extensive use of the
`Tornado <http://www.tornadoweb.org>`__ asynchronous web framework to
facilitate a combined asynchronous HTTP and WebSocket server. All HTML
content served that contains a closing ``</body>`` tag will
automatically have two ``<script>`` tags injected to facilitate the
WebSockets connection back to the server.

The WebSockets endpoint is located at
``http://localhost:5555/livereload`` by default, and the JavaScript file
that facilitates the reloading is located at
``http://localhost:5555/livereload.js`` by default (depending on your
host and port settings).

Background
----------

The library came out of a need for a simple web server, capable of
serving static files with live reload capabilities, but also with the
ability to serve content from non-standard base paths (for example, from
``http://somesite.com/blog/`` as opposed to always just
``http://somesite.com``). More specifically, this was to be used in
`Statik <https://github.com/thanethomson/statik>`__ - the static web
site generator.

The `livereload <https://github.com/lepture/python-livereload>`__
library was great for a while, until the real need came up for modifying
it, where the wheels came off the bus. More functional unit tests were
needed to validate the basic functionality, and more flexibility was
needed in some respects, so ``httpwatcher`` was built.

Contributing
------------

Feel free to contribute! Fork the repository, make your changes in a
feature branch, and then submit a pull request.

License
-------

**The MIT License (MIT)**

Copyright (c) 2017 Thane Thomson

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the
"Software"), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be included
in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
