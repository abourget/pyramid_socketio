# -=- encoding: utf-8 -=-

import logging
import gevent

__all__ = ['SocketIOError', 'SocketIOContext',
           'socketio_manage']

log = logging.getLogger(__name__)

class SocketIOError(Exception):
    pass

class SocketIOKeyAssertError(SocketIOError):
    pass

class SocketIOContext(object):
    def __init__(self, request):
        """Created by the call to connect() before doing any generic recv()"""
        self.request = request
        self.io = request.environ['socketio']
        self._parent = None
        if not hasattr(request, 'jobs'):
            request.jobs = []
        # Override self.debug if in production mode
        #self.debug = lambda x: None

    def debug(self, msg):
        log.debug("%s: %s" % (self.io.session.session_id, msg))

    def spawn(self, callable, *args):
        """Spawn a new process in the context of this request.

        It will be monitored by the "watcher" method
        """
        self.debug("Spawning greenlet: %s" % callable.__name__)
        new = gevent.spawn(callable, *args)
        self.request.jobs.append(new)
        return new

    def kill(self):
        """Kill the current context, pass control to the parent context if
        "return" is True.  If this is the last context, close the connection."""
        # Detach objects to dismantle cyclic references
        # (was that going to happen anyway ?)
        request = self.request
        io = self.io
        self.request = None
        self.io = None
        if self._parent:
            parent = self._parent
            self._parent = None
            return parent
        else:
            io.close()
            return
            
    def switch(self, new_context):
        """Switch context, stack up contexts and pass on request, the caller
        must return the value returned by switch().
        """
        self.debug("Switching context: %s" % new_context.__name__)
        newctx = new_context(self.request)
        newctx._parent = self
        return newctx

    def error(self, code, msg):
        """Used to quickly generate an error message"""
        self.debug("error: %s, %s" % (code, msg))
        self.io.send(dict(type='error', error=code, msg=msg))

    def msg(self, msg_type, **kwargs):
        """Used to quickly generate an error message"""
        self.debug("message: %s, %s" % (msg_type, kwargs))
        self.io.send(dict(type=msg_type, **kwargs))

    def assert_keys(self, msg, elements):
        """Make sure the elements are inside the message, otherwise send an
        error message and skip the message.
        """
        if isinstance(elements, (str, unicode)):
            elements = (elements,)
        for el in elements:
            if el not in msg:
                self.error("bad_request", "Msg type '%s' should include all those keys: %s" % (msg['type'], elements))
                raise SocketIOKeyAssertError()

    def __call__(self, msg):
        """Parse the message upon reception and dispatch it to the good method.
        """
        msg_type = "msg_" + msg['type']
        if not hasattr(self, msg_type) or \
                not callable(getattr(self, msg_type)):
            self.error("unknown_command", "Command unknown: %s" % msg['type'])
            return
        try:
            self.debug("Calling msg type: %s with obj: %s" % (msg_type, msg))
            return getattr(self, msg_type)(msg)
        except SocketIOKeyAssertError, e:
            return None


def watcher(request):
    """Watch if any of the greenlets for a request have died. If so, kill the request and the socket.
    """
    # TODO: add that if any of the request.jobs die, kill them all and exit
    io = request.environ['socketio']
    gevent.sleep(5.0)
    while True:
        gevent.sleep(1.0)
        if not io.connected():
            gevent.killall(request.jobs)
            return

def socketio_recv(context):
    """Manage messages arriving from Socket.IO, dispatch to context handler"""
    io = context.io
    while True:
        for msg in io.recv():
            # Skip invalid messages
            if not isinstance(msg, dict):
                context.error("bad_request",
                              "Your message needs to be JSON-formatted")
            elif 'type' not in msg:
                context.error("bad_request",
                              "You need a 'type' attribute in your message")
            else:
                # Call msg in context.
                newctx = context(msg)

                # Switch context ?
                if newctx:
                    context = newctx

        if not io.connected():
            return

def socketio_manage(start_context):
    """Main SocketIO management function, call from within your Pyramid view"""
    request = start_context.request
    io = request.environ['socketio']

    if not io.connected():
        # probably asked for something else dude!
        return "there's no reason to get here, you won't get any further. have you mapped socket.io/lib to something ?"

    start_context.spawn(socketio_recv, start_context)

    # Launch the watcher thread
    killall = gevent.spawn(watcher, request)

    gevent.joinall(request.jobs + [killall])
    
    start_context.debug("socketio_manage terminated")

    return "done"
