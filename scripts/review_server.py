"""Loopback-only static review surface. Never serves raw media or filesystem listings."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import argparse

ROOT = Path(__file__).resolve().parents[1]
ASSETS = {'/': ('web/index.html', 'text/html; charset=utf-8'),
          '/review.css': ('web/review.css', 'text/css; charset=utf-8'),
          '/review.js': ('web/review.js', 'text/javascript; charset=utf-8'),
          '/example.json': ('examples/review-demo.json', 'application/json; charset=utf-8')}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.headers.get('Host') not in (f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'):
            self.send_error(403)
            return
        if self.path not in ASSETS:
            self.send_error(404)
            return
        name, mime = ASSETS[self.path]
        body = (ROOT / name).read_bytes()
        self.send_response(200)
        for key, value in {'Content-Type': mime, 'Content-Length': str(len(body)), 'Cache-Control': 'no-store',
                           'X-Content-Type-Options': 'nosniff', 'Content-Security-Policy': "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; media-src blob:; base-uri 'none'; frame-ancestors 'none'; form-action 'none'"}.items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_):
        pass


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8890)
    args = parser.parse_args()
    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    print(f'RoughCut Review http://127.0.0.1:{args.port}', flush=True)
    server.serve_forever()
