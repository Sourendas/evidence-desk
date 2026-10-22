"""Evidence Desk web server (stdlib only). Run: python server.py [--port 8787]"""
from __future__ import annotations

import argparse
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from evidence_desk.agent import EvidenceDesk
from evidence_desk.config import get_settings
from evidence_desk.report import to_markdown

STATIC = Path(__file__).resolve().parent / "static"


def make_handler(settings, getter=None):
    class H(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):  # quiet; never logs headers/bodies
            sys.stderr.write("%s %s\n" % (self.command, self.path))

        def _send(self, code, body: bytes, ctype: str):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _json(self, code, obj):
            self._send(code, json.dumps(obj).encode(), "application/json")

        def do_GET(self):
            if self.path in ("/", "/index.html"):
                self._send(200, (STATIC / "index.html").read_bytes(), "text/html; charset=utf-8")
            elif self.path == "/api/health":
                self._json(200, {"ok": True, **settings.public()})
            else:
                self._json(404, {"error": "not found"})

        def do_POST(self):
            try:
                n = min(int(self.headers.get("Content-Length", 0)), 400_000)
                payload = json.loads(self.rfile.read(n) or b"{}")
            except (ValueError, json.JSONDecodeError):
                return self._json(400, {"error": "invalid JSON"})
            if self.path == "/api/ask":
                q = str(payload.get("question", "")).strip()
                if not q:
                    return self._json(400, {"error": "question is required"})
                kw = {"getter": getter} if getter else {}
                desk = EvidenceDesk(settings, **kw)
                res = desk.run(q, [str(s) for s in payload.get("snippets", [])][:10],
                               [str(u) for u in payload.get("urls", [])][:6], bool(payload.get("use_web")))
                d = res.to_dict()
                d["markdown"] = to_markdown(d)
                return self._json(200, d)
            if self.path == "/api/report":
                try:
                    return self._send(200, to_markdown(payload).encode(), "text/markdown; charset=utf-8")
                except (KeyError, TypeError):
                    return self._json(400, {"error": "invalid result payload"})
            self._json(404, {"error": "not found"})

    return H


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8787)
    a = ap.parse_args()
    s = get_settings()
    print(f"Evidence Desk on http://{a.host}:{a.port}  mode={s.public()['mode']}")
    ThreadingHTTPServer((a.host, a.port), make_handler(s)).serve_forever()


if __name__ == "__main__":
    main()
