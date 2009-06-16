from urlparse import urlparse
from Queue import Queue
from cgi import parse_qs
from urllib import unquote
import signal, thread, time, sys
import BaseHTTPServer, SocketServer, mimetypes

webport = 1840

class WebServer(SocketServer.ThreadingMixIn, BaseHTTPServer.HTTPServer):
    pass
    
toPhone = Queue(0)
fromPhone = Queue(0)
store = {"/command":toPhone, "/log":fromPhone}
send = {"/browser":(fromPhone, ""), "/phone":(toPhone, 'console.')}
class WebRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    def do_GET(self):
        host, path, params, query = parseURL(self.path)

        if path in store:
            store[path].put(query.get("message"))

        elif path in send:
            queue, prefix = send[path]
            self.respond("application/x-javascript")
            self << "%scommand('%s')" % (prefix, escapeJavaScript(queue.get()))

        else:
            path = path[1:]
            if path == 'favicon.ico':
                self.respond(code="404 Not Found")
                self << "Not found!"
                return

            self.respond(mimetypes.guess_type(path)[0])

            if path in ["ibug.js", "firebug.js"]:
                self << "var ibugHost = '%s';"  % geturl()

            self << file(path).read()
    
    def respond(self, mimeType="text/plain", code="200 OK"):
        self << "HTTP/1.1 %s\r\n" % code
        self << "Content-Type: %s\r\n" % mimeType
        self << "\r\n"

    def __lshift__(self, text):
        self.wfile.write(text)
        
# **************************************************************************************************

def serve():    
    done = []
    def terminate(sig_num, frame):
        done.append(True)
    signal.signal(signal.SIGINT, terminate)

    
    print "Paste this code into the <head> of all HTML that will run on your iPhone:"
    print '<script type="application/x-javascript" src="%s/ibug.js"></script>' % geturl()

    if "launch" in sys.argv:
        print "Launching the console at:\n"

        import webbrowser
        webbrowser.open('%s/firebug.html' % geturl())
    else:
        print "Load this page in your browser:\n"

    print "    %s/firebug.html" % geturl()

    print "\nFirebug server is running..."

    server = WebServer(("", webport), WebRequestHandler)
    server.allow_reuse_address = True
    thread.start_new_thread(server.serve_forever, ())

    while not done:
        try:
            time.sleep(1)
        except IOError:
            pass

    server.server_close()

# **************************************************************************************************

def parseURL(url):
    """ Parses a URL into a tuple (host, path, args) where args is a dictionary."""
    
    scheme, host, path, params, query, hash = urlparse(url)
    if not path: path = "/"

    args = parse_qs(query)

    escapedArgs = {}
    for name in args:
        if len(args[name]) == 1:
            escapedArgs[unquote(name)] = unquote(args[name][0])
        else:
            escapedArgs[unquote(name)] = escapedSet = []
            for item in args[name]:
                escapedSet.append(unquote(item))

    return host, path, params, escapedArgs

def escapeJavaScript(text):
    return text.replace("'", "\\'").replace("\n", "\\n").replace("\r", "")
    
def geturl():
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("getfirebug.com", 80))
    hostname = s.getsockname()[0]
    s.close()
    return 'http://%s:%s' % (hostname, webport)

# **************************************************************************************************

if __name__ == "__main__":
    serve()
