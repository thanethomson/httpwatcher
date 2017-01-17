# -*- coding: utf-8 -*-

from __future__ import unicode_literals
import re
from io import open
import os
import os.path
import tempfile
import shutil
import pkg_resources

__all__ = [
    "write_file",
    "init_temp_path",
    "get_html_namespace",
    "html_findall",
    "read_resource"
]


def write_file(base_path, filename, contents):
    if not os.path.isdir(base_path):
        os.makedirs(base_path)

    with open(os.path.join(base_path, filename), "wt", encoding="utf-8") as f:
        f.write(contents)


def read_resource(path):
    full_path = pkg_resources.resource_filename("httpwatcher", path)
    with open(full_path, "rb") as f:
        contents = f.read()
    return contents


def init_temp_path():
    temp_path = os.path.abspath(os.path.join(tempfile.gettempdir(), "httpwatcher"))
    if os.path.isdir(temp_path):
        shutil.rmtree(temp_path)
    os.makedirs(temp_path)
    return temp_path


def get_html_namespace(tree):
    p = re.compile(r"\{(?P<namespace>[^\}]+)\}.+")
    m = p.match(tree[0].tag)
    return m.group('namespace') if m is not None else None


def html_findall(tree, namespace, xpath):
    return tree.findall(xpath.format(ns="{%s}" % namespace))
