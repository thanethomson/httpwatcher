#!/usr/bin/env python
# -*- coding:utf-8 -*-

import re
from io import open
import os.path
from setuptools import setup


def read_file(filename):
    full_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), filename)
    with open(full_path, "rt", encoding="utf-8") as f:
        lines = f.readlines()
    return lines


def get_version():
    pattern = re.compile(r"__version__ = \"(?P<version>[0-9.a-zA-Z-]+)\"")
    for line in read_file(os.path.join("httpwatcher", "__init__.py")):
        m = pattern.match(line)
        if m is not None:
            return m.group('version')
    raise ValueError("Cannot extract version number for httpwatcher")


setup(
    name="httpwatcher",
    version=get_version(),
    description="Web server library and command-line utility for serving static files with live reload functionality",
    long_description=''.join(read_file('README.rst')),
    keywords='livereload hotreload web server live reload hot reload',
    author="Thane Thomson",
    author_email="connect@thanethomson.com",
    url="https://github.com/thanethomson/httpwatcher",
    install_requires=[r.strip() for r in read_file('requirements.txt') if len(r.strip()) > 0],
    entry_points={
        'console_scripts': [
            'httpwatcher = httpwatcher.cmdline:main',
        ]
    },
    license='MIT',
    packages=["httpwatcher"],
    include_package_data=True,
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Operating System :: POSIX",
        "Operating System :: MacOS",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Utilities"
    ]
)
