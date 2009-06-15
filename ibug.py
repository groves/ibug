
from urlparse import urlparse
from Queue import Queue
from cgi import parse_qs
from urllib import unquote
import signal, thread, time, sys
import BaseHTTPServer, SocketServer, mimetypes

# **************************************************************************************************
# Globals

global done, server
done = False
server = None

webPort = 1840

# **************************************************************************************************

class WebServer(SocketServer.ThreadingMixIn, BaseHTTPServer.HTTPServer):
    pass
    
toPhone = Queue(0)
fromPhone = Queue(0)
toHandle = {"/command":toPhone, "/log":fromPhone}
toSend = {"/browser":(fromPhone, ""), "/phone":(toPhone, 'console.')}
class WebRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    def do_GET(self):
        host, path, params, query = parseURL(self.path)

        if path in toHandle:
            toHandle[path].put(query.get("message"))

        elif path in toSend:
            queue, prefix = toSend[path]
            self.respond(mimeType="application/x-javascript")
            cmd = "%scommand('%s')" % (prefix, escapeJavaScript(queue.get()))
            self << cmd

        elif path in ["/ibug.js", "/firebug.js"]:
            header = "var ibugHost = '%(hostName)s:%(port)s';" % getHostInfo()
            self.sendFile(path[1:], header=header)

        else:
            self.sendFile(path[1:])
    
    def respond(self, code=200, mimeType="text/plain"):
        self << "HTTP/1.1 %s %s\n" % (code, "OK")
        self << "Content-Type: %s\n" % mimeType
        self << "\n"
    
    def sendFile(self, path, mimeType=None, header=None):
        if path == 'favicon.ico':
            self.respond(404)
            self << "Not found!"
            return

        if not mimeType:
            mimeType = mimetypes.guess_type(path)[0]
            
        self.respond(200, mimeType)
        if header:
            self << header
        self << file(path).read()
        
    def __lshift__(self, text):
            self.wfile.write(text)
        
# **************************************************************************************************

def serve():    
    signal.signal(signal.SIGINT, terminate)
    thread.start_new_thread(runServer, ())
    
    global done
    while not done:
        try:
            time.sleep(0.3)
        except IOError:
            pass
   
    global server
    server.server_close()
    
def runServer():
    print "Paste this code into the <head> of all HTML that will run on your iPhone:"
    print getFormattedFile("embed.html", getHostInfo())

    url = "http://%(hostName)s:%(port)s/firebug.html" % getHostInfo()
    if "launch" in sys.argv:
        print "Launching the console at:\n"

        import webbrowser
        webbrowser.open(url)
    else:
        print "Load this page in your browser:\n"

    print "    %s" % url
    
    print "\nFirebug server is running..."

    global server
    server = WebServer(("", webPort), WebRequestHandler)
    server.allow_reuse_address = True
    server.serve_forever()

def terminate(sig_num, frame):
    global done
    done = True    

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
    
def getFormattedFile(path, args={}):
    return file(path).read() % args

def getHostInfo():
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("getfirebug.com", 80))
    hostName = "localhost"
    s.close()
    
    return {"hostName": hostName, "port": webPort}

# **************************************************************************************************

if __name__ == "__main__":
    serve()
