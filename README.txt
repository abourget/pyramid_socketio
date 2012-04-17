THIS PACKAGE IS DEPRECATED.  SEE THE REVAMPED gevent-socketio AT:

  https://github.com/abourget/gevent-socketio

And the documentation at:

  http://gevent-socketio.readthedocs.org/en/latest/index.html




The following is a bit rude and rough, check the blog post instead

Gevent-based Socket.IO integration for Pyramid (and WSGI frameworks)
====================================================================

To use the server, either run:

<pre>
socketio-serve development.ini
socketio-serve-reload development.ini
</pre>

or tweak your <code>[server:main]</code> section in your development.ini to:

<pre>
[server:main]
use = egg:pyramid_socketio#sioserver_patched
resource = socket.io
host = 0.0.0.0
port = 6555
</pre>

otherwise, follow instructions given for <code>pastegevent</code>.


Simple in-Pyramid usage:

<pre>
### somewhere in a Pyramid view:
from pyramid_socketio import SocketIOContext, socketio_manage

class ConnectIOContext(SocketIOContext):
    """Starting context, which will go one side or the other"""
    def msg_connect(self, msg):
        if msg.get('context') not in contexts:
            self.io.send(dict(type="error", error="unknown_connect_context",
                              msg="You asked for a context that doesn't exist"))
            return
        # Waiting for a msg such as: {'type': connect', 'context': 'section'}
        newctx = self.switch(contexts[msg['context']])
        if hasattr(newctx, 'startup'):
            newctx.startup(msg)
        # Returning a new IOContext switches the WebSocket context, and will
        # call this context's methods for next incoming messages.
        return newctx

    def msg_login(self, msg):
        # Do the login, then wait for the next connect
        self.request.session.user_id = 123
        print "Logged in, session created and"


class SectionIOContext(SocketIOContext):
    def startup(self, connect_msg):
        print "Started the section context"
        self.my_id = connect_msg['section_id']
        # TODO: make sure we don't leak Sessions from MongoDB!
        from intr.models import mdb # can't import globally, because of Pyramid
        self.db = mdb
        self.conn = BrokerConnection("localhost", "guest", "guest", "/")
        self.chan = self.conn.channel()
        self.queue = Queue("session-%s" % self.io.session.session_id,
                           exchange=my_exchange,
                           durable=False, exclusive=True,
                           auto_delete=True,
                           routing_key="section.%s" % self.my_id)

        self.producer = Producer(self.chan, exchange=my_exchange,
                                 serializer="json",
                                 routing_key="section.%s" % self.my_id)
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
        # "memorized" is the 'type' attribute, any other kwarg added will be
        # added to the JSON object.
        self.msg("memorized", some="thing")

    def msg_forget(self, msg):
        self.error("error_code", "Error message")

    def msg_change_privacy(self, msg):
        pass

    def msg_get_members(self, msg):
        pass

    def msg_enter_game(self, msg):
        return self.switch(SomeOtherIOContext)

contexts = {'section': SectionIOContext,
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

In the routes and view configurations, 'socket.io' is the "resource" specified either in the server (under [server:main], key=resource), and is by default "socket.io".  This is pretty much a standard..



#
#  On the JavaScript side:
#

Somewhere:

  <script src="http://cdn.socket.io/stable/socket.io.js"></script>

And then:

var socket = new io.Socket(null, {rememberTransport: false,
                                  transports: ['websocket', 'xhr-multipart', 'xhr-polling', 'jsonp-polling']});
socket.on('message', function(obj){
  console.log("message:", JSON.stringify(obj));
  if ((obj.type == "memorized") || (obj.type == "forgot")) {
    // do some tihngs...
  }
  else if (obj.type == "new_content") {
    $("div.intr-timeline").append($(obj.insert_html));
  }
  else if (obj.type == "privacy_changed") {
    $("#privacy").val(obj.new_value);
  }
  else if (obj.type == "photos_sent") {
    $('#intrentry-post-photos div.upload').empty();
    new_upload_box();
  }
});
socket.on('error', function(obj) {
  console.log("error", obj);
});
socket.on('disconnect', function(obj) {
  console.log("disconnected", obj);
  socketio_notification("Disconnected", "There was a disconnection, either because of network or server failure");
  socketio_schedule_reconnect();
});
var connection_notification = null;
socket.on('connect', function() {
  console.log("connected");
  // Comment out if you don't use the auto-reconnect machinery:
  socketio_notification();
  socket.send({type: "connect", context: "interest", interest_id: "${intr['_id']}"});
});



// Use this:

socket.connect(); 



// Or this is optional auto-reconnect machinery:

function socketio_schedule_reconnect() {
  setTimeout(function() { if (!socket.connected && !socket.connecting) { socketio_reconnect("reconnect");}}, 1000);
}
function socketio_reconnect(func) {
  console.log("connecting... ", socket);
  if (func == "connect") {
    socketio_notification("Connecting", "Connecting...");
  }
  if (func == "reconnect") {
    socketio_notification("Re-connecting", "Attempting to reconnect...");
    socketio_schedule_reconnect();
  }
  socket.connect();
}
function socketio_notification(title, msg) {
  if (connection_notification) {
    connection_notification.close();
    connection_notification = null;
  }
  if (title) {
    connection_notification = notify_default(title, msg);
  }
}
$(document).ready(function() {
  socketio_reconnect('connect');
});
