"""Serves web/ for QA with Vercel-style clean URLs and points the admin /
shop pages at the QA backend (localhost:8002) instead of the default 8001.
Usage: python backend/qa/serve_web.py 5555"""
import http.server
import sys
from pathlib import Path

WEB = Path(__file__).resolve().parents[2] / "web"
API = "http://localhost:8002"


class Handler(http.server.SimpleHTTPRequestHandler):
    def _resolve(self):
        p = self.path.split("?")[0].split("#")[0]
        f = WEB / p.lstrip("/")
        if f.is_dir():
            f = f / "index.html"
        if not f.exists() and (WEB / (p.lstrip("/") + ".html")).exists():
            f = WEB / (p.lstrip("/") + ".html")
        return f

    def do_GET(self):
        f = self._resolve()
        if not f.exists():
            self.send_error(404)
            return
        data = f.read_bytes()
        ctype = self.guess_type(str(f))
        if f.suffix == ".html":
            data = data.replace(b"<head>", f'<head><script>window.SUDA_API_BASE_URL="{API}";</script>'.encode(), 1)
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5555
    http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
