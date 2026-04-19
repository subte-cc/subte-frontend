#!/usr/bin/env python3
import http.server
import socketserver
import urllib.request
import urllib.error
import os
import mimetypes
import time
mimetypes.add_type('text/css', '.css')
mimetypes.add_type('application/javascript', '.js')
mimetypes.add_type('image/svg+xml', '.svg')

PORT = 3000
BACKEND_URL = "http://127.0.0.1:3001"
BUILD_DIR = "build"

class ProxyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.start_time = 0.0
        super().__init__(*args, directory=BUILD_DIR, **kwargs)

    def handle_one_request(self):
        self.start_time = time.time()
        super().handle_one_request()

    def log_request(self, code='-', size='-'):
        elapsed = (time.time() - self.start_time) * 1000
        self.log_message('"%s" %s %s [%.2fms]',
                         self.requestline, str(code), str(size), elapsed)

    def do_GET(self):
        if self.path.startswith('/api/') or self.path.startswith('/up/'):
            self.proxy_request('GET')
            return

        clean_path = self.path.split('?')[0]
        if clean_path == '/':
            clean_path = '/index.html'

        filepath = os.path.join(self.directory, clean_path.lstrip('/'))

        if os.path.exists(filepath) and not os.path.isdir(filepath):
            self.path = clean_path
        elif os.path.exists(filepath + '.html'):
            self.path = clean_path + '.html'
        elif os.path.isdir(filepath):
            if os.path.exists(os.path.join(filepath, 'index.html')):
                self.path = clean_path.rstrip('/') + '/index.html'
            else:
                self.path = '/index.html'
        else:
            self.path = '/index.html'

        super().do_GET()

    def do_POST(self):
        if self.path.startswith('/api/') or self.path.startswith('/up/'):
            self.proxy_request('POST')
        else:
            self.send_error(405, "Method Not Allowed")

    def do_PUT(self):
        if self.path.startswith('/api/') or self.path.startswith('/up/'):
            self.proxy_request('PUT')
        else:
            self.send_error(405, "Method Not Allowed")

    def do_DELETE(self):
        if self.path.startswith('/api/') or self.path.startswith('/up/'):
            self.proxy_request('DELETE')
        else:
            self.send_error(405, "Method Not Allowed")

    def do_PATCH(self):
        if self.path.startswith('/api/') or self.path.startswith('/up/'):
            self.proxy_request('PATCH')
        else:
            self.send_error(405, "Method Not Allowed")

    def proxy_request(self, method):
        url = BACKEND_URL + self.path
        
        headers = {}
        for key, value in self.headers.items():
            if key.lower() not in ['host', 'connection', 'accept-encoding']:
                headers[key] = value

        data = None
        if 'Content-Length' in self.headers:
            content_length = int(self.headers['Content-Length'])
            data = self.rfile.read(content_length)

        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        
        try:
            with urllib.request.urlopen(req) as response:
                self.send_response(response.status)
                for key, value in response.headers.items():
                    if key.lower() not in ['transfer-encoding', 'connection']:
                        self.send_header(key, value)
                self.end_headers()
                self.wfile.write(response.read())
        except urllib.error.HTTPError as e:
            self.send_response(e.code)
            for key, value in e.headers.items():
                if key.lower() not in ['transfer-encoding', 'connection']:
                    self.send_header(key, value)
            self.end_headers()
            self.wfile.write(e.read())
        except Exception as e:
            self.send_error(502, f"Bad Gateway: {str(e)}")

if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    if not os.path.exists(BUILD_DIR):
        print(f"Error: '{BUILD_DIR}' directory not found. Please run the build script first.")
        exit(1)

    class ReusableTCPServer(socketserver.TCPServer):
        allow_reuse_address = True

    with ReusableTCPServer(("", PORT), ProxyHTTPRequestHandler) as httpd:
        print(f"Serving local testing environment at http://localhost:{PORT}")
        print(f"Proxying /api/* and /up/* to {BACKEND_URL}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server.")
