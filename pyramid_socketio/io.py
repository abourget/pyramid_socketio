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
    def __init__(self, request, in_type="type", out_type="type", debug=False):
        """Called when you create a new context, either by hand or from a nested context.

        Arguments:
        * ``request`` - the pyramid request
        * ``in_type`` - the dict. key for message names of incoming messages
        * ``out_type`` - the dict. key for message names, in outgoing message
        * ``debug`` - whether to disable debug logging...
        """
        self.request = request
        self.io = request.environ['socketio']
        self._parent = None
        self._in_type = in_type
        self._out_type = out_type
        if not hasattr(request, 'jobs'):
            request.jobs = []

        # Override self.debug if in production mode
        if not debug:
             self.debug = lambda x: None

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
        """Switch context, stack up contexts and pass on request.

        Important note: the caller *must* return the value returned by switch()
        to the managing context.
        """
        self.debug("Switching context: %s" % new_context.__name__)
        newctx = new_context(self.request)
        newctx._parent = self
        newctx._in_type = self._in_type
        newctx._out_type = self._out_type
        return newctx

    def error(self, code, msg):
        """Used to quickly generate an error message"""
        self.debug("error: %s, %s" % (code, msg))
        self.io.send({self._out_type: "error", 'error': code, 'msg': msg})

    def msg(self, msg_type, **kwargs):
        """Used to quickly generate an error message"""
        self.debug("message: %s, %s" % (msg_type, kwargs))
        kwargs[self._out_type] = msg_type
        self.io.send(kwargs)

    def assert_keys(self, msg, elements):
        """Make sure the elements are inside the message, otherwise send an
        error message and skip the message.
        """
        in_type = self._in_type
        if isinstance(elements, (str, unicode)):
            elements = (elements,)
        for el in elements:
            if el not in msg:
                self.error("bad_request", "Msg type '%s' should include all those keys: %s" % (msg[in_type], elements))
                raise SocketIOKeyAssertError()

    def __call__(self, msg):
        """Parse the message upon reception and dispatch it to the good method.
        """
        in_type = self._in_type
        msg_type = "msg_" + msg[in_type]
        if not hasattr(self, msg_type) or \
                not callable(getattr(self, msg_type)):
            self.error("unknown_command", "Command unknown: %s" % msg[in_type])
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
    in_type = context._in_type
    while True:
        for msg in io.recv():
            # Skip invalid messages
            if not isinstance(msg, dict):
                context.error("bad_request",
                              "Your message needs to be JSON-formatted")
            elif in_type not in msg:
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
    """Main SocketIO management function, call from within your Pyramid view.

    Pass it an instance of a SocketIOContext or a derivative that will handle
    messages for a particular context.
    """
    request = start_context.request
    io = request.environ['socketio']

    if not io.connected():
        # probably asked for something else dude!
        return "there's no reason to get here, you won't get any further. have you mapped socket.io/lib to something ?"

    # Run startup if there's one

    start_context.spawn(socketio_recv, start_context)

    # Launch the watcher thread
    killall = gevent.spawn(watcher, request)

    gevent.joinall(request.jobs + [killall])
    
    start_context.debug("socketio_manage terminated")

    return "done"
