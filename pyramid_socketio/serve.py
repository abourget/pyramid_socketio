#!/usr/bin/env python
import gevent
from gevent import monkey; monkey.patch_all()

from ConfigParser import ConfigParser
import logging
import logging.config
import socket
import sys
import os

from socketio import SocketIOServer
from paste.deploy import loadapp


host = '127.0.0.1'
port = 6543

def socketio_serve():
    # See http://bitbucket.org/Jeffrey/socketio/src/9bf2cd777808/examples/chat.py

    if len(sys.argv) < 2:
        print "ERROR: Please specify .ini file on command line"
        sys.exit(1)

    do_reload = sys.argv[1] == '--reload'

    # Setup logging...
    cfgfile = sys.argv[2] if do_reload else sys.argv[1]
    logging.config.fileConfig(cfgfile)
    log = logging.getLogger(__name__)

    cfg = ConfigParser()
    cfg.readfp(open(cfgfile))
    sec = 'server:main'
    if sec in cfg.sections():
        opts = cfg.options(sec)
        if 'host' in opts:
            host = cfg.get(sec, 'host')
        if 'port' in opts:
            port = cfg.getint(sec, 'port')

    def main():
        # Load application and config.
        app = loadapp('config:%s' % cfgfile, relative_to='.')
        server = SocketIOServer((host, port), app,
                                resource="socket.io")

        try:
            print "Serving on %s:%d (http://127.0.0.1:%d) ..." % (host, port, port)
            server.serve_forever()
        except socket.error, e:
            print "ERROR SERVING WSGI APP: %s" % e
            sys.exit(1)

    def reloader():
        from paste import reloader
        reloader.install()
        reloader.watch_file(cfgfile)
        import glob # Restart on "compile_catalog"
        # TODO: make more generic, and more robust
        for lang in glob.glob('*/locale/*/LC_MESSAGES/*.mo'):
            reloader.watch_file(lang)
        for lang in glob.glob('*/i18n/*/LC_MESSAGES/*.mo'):
            reloader.watch_file(lang)

    jobs = [gevent.spawn(main)]
    if do_reload:
        jobs.append(gevent.spawn(reloader))
    gevent.joinall(jobs)
