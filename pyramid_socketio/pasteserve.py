"""Entry point for PasteDeploy."""

# hump'ly ripped from pastegevent 0.1

from gevent import reinit
from socketio import SocketIOServer
from gevent.monkey import patch_all

__all__ = ["server_factory",
           "server_factory_patched"]

def server_factory(global_conf, host, port, resource="socket.io"):
    port = int(port)
    def serve(app):
        reinit()
        print "Serving on %s:%d (http://127.0.0.1:%d) ..." % (host, port, port)
        SocketIOServer((host, port), app,
                       resource=resource).serve_forever()
    return serve


def server_factory_patched(global_conf, host, port, resource="socket.io"):
    port = int(port)
    def serve(app):
        reinit()
        patch_all(dns=False)
        print "Serving on %s:%d (http://127.0.0.1:%d) ..." % (host, port, port)
        SocketIOServer((host, port), app,
                       resource=resource).serve_forever()
    return serve
