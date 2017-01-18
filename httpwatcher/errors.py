# -*- coding: utf-8 -*-

from __future__ import unicode_literals

__all__ = [
    "MissingFolderError"
]


class MissingFolderError(Exception):
    def __init__(self, folder_name):
        super(MissingFolderError, self).__init__("Cannot find folder: %s" % folder_name)
        self.folder_name = folder_name
