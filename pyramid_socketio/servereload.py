#!/usr/bin/env python

import os
import sys

def socketio_serve_reload():
    """Spawn a new process and reload when it dies"""
    while True:
        ret = os.system("socketio-serve --watch %s" % (sys.argv[1]))
        if ret != 3:
            break
