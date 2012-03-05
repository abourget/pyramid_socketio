#!/usr/bin/env python

import os
import sys

from os.path import dirname, join,realpath


def socketio_serve_reload():
    """Spawn a new process and reload when it dies"""
    bin_dir = dirname(realpath(sys.argv[0]))
    executable = join(bin_dir, 'socketio-serve')
    command = "%s --watch %s" % (executable, sys.argv[1])
    while True:
        ret = os.system(command)
        if ret != 768:
            break
