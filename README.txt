Gevent-based Socket.IO integration for Pyramid (and WSGI frameworks)
====================================================================

Simple usage:

<pre>
### somewhere in a Pyramid view:
from intr.socketio import SocketIOContext, socketio_manage


class ConnectIOContext(SocketIOContext):
    """Starting context, which will go one side or the other"""
    def msg_connect(self, msg):
        if msg.get('context') not in contexts:
            self.io.send(dict(type="error", error="unknown_connect_context",
                              msg="You asked for a context that doesn't exist"))
            return
        # Waiting for a msg such as: {'type': connect', 'context': 'interest'}
        newctx = self.switch(contexts[msg['context']])
        if hasattr(newctx, 'startup'):
            newctx.startup(msg)
        # Returning a new IOContext switches the WebSocket context, and will
        # call this context's methods for next incoming messages.
        return newctx

    def msg_login(self, msg):
        # Do the login, then wait for the next connect
        from intr.bound_models import User, ObjectId
        u = User.find_one({'_id': ObjectId("4d4892a12a16e62df4000000")})
        intrs = u['interests']
        from intr.views.auth import create_session
        create_session(request, u, intrs)
        print "Logged, created session"


class InterestIOContext(SocketIOContext):
    def startup(self, connect_msg):
        print "Started the interest context"
        self.intr_id = connect_msg['interest_id']
        # TODO: make sure we don't leak Sessions from MongoDB!
        from intr.models import mdb # can't import globally, because of Pyramid
        self.db = mdb
        self.conn = BrokerConnection("localhost", "guest", "guest", "/")
        self.chan = self.conn.channel()
        self.queue = Queue("session-%s" % self.io.session.session_id,
                           exchange=intr_exchange,
                           durable=False, exclusive=True,
                           auto_delete=True,
                           routing_key="interest.%s" % self.intr_id)

        self.producer = Producer(self.chan, exchange=intr_exchange,
                                 serializer="json",
                                 routing_key="interest.%s" % self.intr_id)
        self.producer.declare()
        self.consumer = Consumer(self.chan, [self.queue])
        self.consumer.declare()
        self.consumer.register_callback(self.consume_queue_message)
        self.spawn(self.queue_recv)

        # Do we need this ?  Please fix the session instead, have a new one
        # init'd for each incoming msg, or when calling save(), re-create a new
        # SessionObject.
        request = self.request
        self.user = request.session['user']
        self.temporary = request.session['temporary']
        self.user_id = request.session['user_id']

    def consume_queue_message(self, body, message):
        """Callback when receiving  anew message from Message Queue"""
        # Do something when received :)
        print "Received message from queue:", self.io.session.session_id, body
        self.io.send(body)

    def queue_recv(self):
        """Wait for messages from Queue"""
        self.consumer.consume(no_ack=True)
        # consume queue...
        while True:
            gevent.sleep(0)
            self.conn.drain_events()
            if not self.io.connected():
                return

    #
    # Socket messages
    #
    def msg_memorize(self, msg):
        # do something

    def msg_forget(self, msg):
        pass

    def msg_interest(self, msg):
        pass

    def msg_change_privacy(self, msg):
        pass

    def msg_get_members(self, msg):
        pass




contexts = {'interest': InterestIOContext,
            'somewhereelse': SocketIOContext,
            }



#
# SOCKET.IO implementation
#
@view_config(route_name="socket_io")
def socket_io(request):
    """Deal with the SocketIO protocol, using SocketIOContext objects"""
    # Offload management to the pyramid_socketio module

    retval = socketio_manage(ConnectIOContext(request))
    #print "socketio_manage ended"
    return Response(retval)



#### Inside __init__.py for your Pyramid application:
def main(..):
    ...
    config.add_static_view('socket.io/lib', 'intr:static')
    config.add_route('socket_io', 'socket.io/*remaining')
    ....
</pre>
