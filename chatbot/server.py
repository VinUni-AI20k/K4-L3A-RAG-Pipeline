"""Minimal HTTP server for the static chat UI.

Run with: python -m chatbot.server
No extra web framework required (Flask/FastAPI are not project
dependencies) - this uses only the standard library so `python -m
chatbot.server` is the entire "install" step.
"""

import json
import threading
import traceback
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import config, engine

STATIC_DIR = Path(__file__).resolve().parent / "static"


class Handler(BaseHTTPRequestHandler):
    server_version = "LegalChatbot/1.0"

    def log_message(self, format: str, *args) -> None:  # noqa: A002
        print(f"[chatbot] {self.address_string()} - {format % args}")

    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path in ("/", "/index.html"):
            self._serve_static("index.html")
            return
        if self.path == "/api/health":
            try:
                stats = engine.warm_up()
                self._send_json(200, {"status": "ok", **stats})
            except Exception as error:  # noqa: BLE001
                self._send_json(500, {"status": "error", "message": str(error)})
            return
        self.send_error(404, "Not found")

    def _serve_static(self, filename: str) -> None:
        path = STATIC_DIR / filename
        if not path.exists():
            self.send_error(404, "Not found")
            return
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/api/chat":
            self.send_error(404, "Not found")
            return

        length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(raw_body or b"{}")
        except json.JSONDecodeError:
            self._send_json(400, {"error": "Invalid JSON body"})
            return

        question = str(payload.get("question", "")).strip()
        if not question:
            self._send_json(400, {"error": "Thiếu câu hỏi"})
            return

        top_k = int(payload.get("top_k", config.TOP_K))
        use_hybrid = bool(payload.get("use_hybrid", True))

        try:
            result = engine.generate_with_citation(question, top_k=top_k, use_hybrid=use_hybrid)
        except Exception as error:  # noqa: BLE001
            traceback.print_exc()
            self._send_json(500, {"error": str(error)})
            return

        sources = [
            {
                "title": source["title"],
                "source": source["source"],
                "score": round(source["score"], 4),
                "retrieval_method": source["retrieval_method"],
                "snippet": source["content"][:400],
            }
            for source in result["sources"]
        ]
        self._send_json(
            200,
            {
                "answer": result["answer"],
                "retrieval_method": result["retrieval_method"],
                "sources": sources,
            },
        )


def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", config.PORT), Handler)
    url = f"http://127.0.0.1:{config.PORT}"
    print(f"Đang chuẩn bị chỉ mục truy hồi (embedding model: {config.EMBEDDING_MODEL})...")
    engine.warm_up()
    print(f"Chatbot đang chạy tại {url}")
    threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
