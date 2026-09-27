#!/usr/bin/env python3
"""
All-in-one local server for dual-api-writer.html.

Does two jobs on a single port:
  1. Serves the static files in this folder (dual-api-writer.html, etc.)
     — same job as `python -m http.server`.
  2. Proxies POST http://localhost:8787/proxy to whatever API the browser
     asks for (via the X-Target-Url header), sidestepping the browser's
     CORS restriction — same job as the old proxy.py.

The proxy streams: bytes are forwarded as they arrive (needed for the
tool's "streaming" option), and when the browser disconnects ("Parar") the
upstream request is closed too, so the provider stops generating.

Only this tool may use it: requests must come from this server's own
pages (or the HTML opened as a local file), and the Host must be
localhost — other websites you visit cannot use it as a relay.

Run:  python server.py [port]
Default port: 8787. It also opens your browser at the tool automatically.

Only one window to keep open now.
"""
import os
import sys
import json
import socket
import functools
import threading
import webbrowser
import urllib.parse
import urllib.request
import urllib.error
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8787
ENTRY_FILE = 'dual-api-writer.html'
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Seconds without receiving any byte from the provider before giving up.
# The tool has its own (configurable) timeout; this is only a safety net,
# so it is long enough for a non-streamed 8K-token chapter.
UPSTREAM_TIMEOUT = 1800

ALLOWED_HOSTS = {f'localhost:{PORT}', f'127.0.0.1:{PORT}', 'localhost', '127.0.0.1'}
# 'null' is the Origin browsers send from a page opened as a local file.
ALLOWED_ORIGINS = {f'http://localhost:{PORT}', f'http://127.0.0.1:{PORT}', 'null'}

# Some providers sit behind Cloudflare rules that reject the default
# "Python-urllib" user agent.
USER_AGENT = 'Mozilla/5.0 (dual-api-writer local proxy)'


class CombinedHandler(SimpleHTTPRequestHandler):
    def _host_ok(self):
        # Blocks DNS-rebinding: a hostile page resolved to 127.0.0.1 still
        # sends its own name in the Host header.
        return (self.headers.get('Host') or '').lower() in ALLOWED_HOSTS

    def _origin_ok(self):
        origin = self.headers.get('Origin')
        # No Origin = not a browser page (e.g. curl), not a cross-site risk.
        return origin is None or origin in ALLOWED_ORIGINS

    def end_headers(self):
        origin = self.headers.get('Origin') if self.headers else None
        if origin in ALLOWED_ORIGINS:
            self.send_header('Access-Control-Allow-Origin', origin)
            self.send_header('Vary', 'Origin')
            self.send_header('Access-Control-Expose-Headers', 'Retry-After')
        super().end_headers()

    def _forbidden(self, why):
        self._send_json(403, {'error': why})

    def do_GET(self):
        if not self._host_ok():
            return self._forbidden('Host not allowed')
        super().do_GET()

    def do_HEAD(self):
        if not self._host_ok():
            return self._forbidden('Host not allowed')
        super().do_HEAD()

    def do_OPTIONS(self):
        if not self._host_ok() or not self._origin_ok():
            return self._forbidden('Origin not allowed')
        self.send_response(204)
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        # Listed explicitly: a "*" wildcard does not cover Authorization.
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Target-Url')
        self.send_header('Access-Control-Max-Age', '600')
        self.send_header('Content-Length', '0')
        self.end_headers()

    def do_POST(self):
        if self.path != '/proxy':
            self._send_json(404, {'error': 'Not found'})
            return
        if not self._host_ok() or not self._origin_ok():
            return self._forbidden('Origin not allowed')

        target_url = self.headers.get('X-Target-Url')
        auth = self.headers.get('Authorization', '')
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length)

        if not target_url:
            self._send_json(400, {'error': 'Missing X-Target-Url header'})
            return
        parts = urllib.parse.urlsplit(target_url)
        if parts.scheme not in ('https', 'http') or not parts.netloc:
            # urllib would also happily open file:// and ftp:// URLs.
            self._send_json(400, {'error': 'X-Target-Url must be an http(s) URL'})
            return

        req = urllib.request.Request(
            target_url,
            data=body,
            method='POST',
            headers={
                'Content-Type': 'application/json',
                'Authorization': auth,
                'Accept': self.headers.get('Accept') or '*/*',
                'User-Agent': USER_AGENT,
            },
        )

        try:
            resp = urllib.request.urlopen(req, timeout=UPSTREAM_TIMEOUT)
        except urllib.error.HTTPError as e:
            resp = e  # error bodies are relayed as-is, with their status
        except Exception as e:
            self._send_json(502, {'error': f'Proxy could not reach target: {e}'})
            return

        with resp:
            status = getattr(resp, 'status', None) or resp.code
            self.send_response(status)
            self.send_header('Content-Type', resp.headers.get('Content-Type') or 'application/json')
            self.send_header('Cache-Control', 'no-cache')
            retry_after = resp.headers.get('Retry-After')
            if retry_after:
                self.send_header('Retry-After', retry_after)
            # No Content-Length: HTTP/1.0 response, the body ends when the
            # connection closes, so chunks can be forwarded as they arrive.
            self.end_headers()
            read = getattr(resp, 'read1', None) or resp.read
            try:
                while True:
                    chunk = read(65536)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                # Browser went away ("Parar"): leaving the with-block closes
                # the upstream connection, so the provider stops generating.
                print('[server] browser disconnected — upstream request closed')
            except (socket.timeout, TimeoutError):
                print('[server] provider stopped sending data — closing')

    def _send_json(self, status, obj):
        data = json.dumps(obj).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):
        # Quieter than the default — only show real requests, skip devtools noise.
        if 'devtools' in (self.path or '') or 'favicon' in (self.path or ''):
            return
        print('[server] ' + (fmt % args))


def open_browser_later():
    threading.Timer(0.6, lambda: webbrowser.open(f'http://localhost:{PORT}/{ENTRY_FILE}')).start()


if __name__ == '__main__':
    # Serve this script's folder, wherever it is started from.
    handler = functools.partial(CombinedHandler, directory=BASE_DIR)
    try:
        server = ThreadingHTTPServer(('127.0.0.1', PORT), handler)
    except OSError as e:
        print(f'Não consegui abrir a porta {PORT}: {e}')
        print(f'Já está outra janela do servidor aberta? Fecha-a ou usa outra porta: python server.py {PORT + 1}')
        sys.exit(1)
    print(f'A correr em http://localhost:{PORT}/ — deixa esta janela aberta.')
    print(f'Ferramenta: http://localhost:{PORT}/{ENTRY_FILE}')
    print('Proxy local: http://localhost:%d/proxy  (já vem pré-preenchido no campo "Proxy local")' % PORT)
    open_browser_later()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nA terminar.')
