import http.server
import socketserver
import os
import sys

PORT = 8088
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

print(f"Starting Smart Clock Screensaver Prototype on http://localhost:{PORT}")
print(f"Serving files from {DIRECTORY}")

try:
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"Server online at http://localhost:{PORT}")
        httpd.serve_forever()
except Exception as e:
    print(f"Error starting server: {e}")
