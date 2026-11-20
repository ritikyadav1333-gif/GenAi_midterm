"""Local web server for the exam RAG demo. No external services are called."""
from __future__ import annotations

import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

from rag import answer


class RAGHandler(SimpleHTTPRequestHandler):
    def do_POST(self) -> None:
        if self.path != "/api/answer":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", 0))
        try:
            payload = json.loads(self.rfile.read(length))
            response = answer(str(payload.get("question", "")))
        except (json.JSONDecodeError, ValueError) as error:
            self.send_error(400, str(error))
            return
        body = json.dumps(response).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    print("Iron Tracks Archive running at http://localhost:5173")
    ThreadingHTTPServer(("", 5173), RAGHandler).serve_forever()
