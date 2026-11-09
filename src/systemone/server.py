"""Local HTTP server for POST /decide and GET /health. Stdlib only."""

import json
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from systemone.engine import Engine, MockEngine
from systemone.questions import validate_questions, validate_state

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 18100
MAX_BODY_BYTES = 2_000_000
_LOOPBACK = frozenset({"127.0.0.1", "localhost", "::1"})


class _HTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True


def ensure_local_bind(host: str, allow_remote: bool) -> None:
    """Refuse 0.0.0.0 and every other non-loopback host unless allow_remote is set."""
    if allow_remote or host in _LOOPBACK:
        return
    raise ValueError(
        f"refusing to bind {host}; pass allow_remote=True or the CLI flag --allow-remote"
    )


def health_payload(engine: Engine) -> dict:
    model = engine.model
    return {"status": "ok", "model": model, "mock": model == "mock"}


def decide_payload(engine: Engine, body: object) -> dict:
    if not isinstance(body, dict):
        raise ValueError("request body must be a JSON object")
    if "questions" not in body:
        raise ValueError("questions is required")
    state = validate_state(body["state"] if "state" in body else None)
    questions = validate_questions(body["questions"])
    started = time.perf_counter()
    answers = engine.decide(state, questions)
    if not isinstance(answers, dict):
        raise RuntimeError("engine did not return an object")
    latency_s = round(time.perf_counter() - started, 6)
    return {"answers": answers, "latency_s": latency_s, "model": engine.model}


def build_handler(engine: Engine) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"
        timeout = 30

        def log_message(self, fmt: str, *args) -> None:
            # Request lines only would still be noise. Do not log bodies.
            return

        def do_GET(self) -> None:
            self._route("GET")

        def do_POST(self) -> None:
            self._route("POST")

        def _route(self, method: str) -> None:
            try:
                status, payload = self._handle(method)
            except ValueError as exc:
                status, payload = 400, {"error": str(exc)}
            except Exception:
                print("systemone: internal error", file=sys.stderr, flush=True)
                status, payload = 500, {"error": "internal error"}
            self._send(status, payload)

        def _handle(self, method: str) -> tuple[int, dict]:
            path = urllib.parse.urlsplit(self.path).path
            if path == "/health":
                if method != "GET":
                    return 405, {"error": "method not allowed"}
                return 200, health_payload(engine)
            if path == "/decide":
                if method != "POST":
                    return 405, {"error": "method not allowed"}
                return 200, decide_payload(engine, self._json_body())
            return 404, {"error": "not found"}

        def _json_body(self) -> object:
            raw_length = self.headers.get("Content-Length")
            if raw_length is None:
                raise ValueError("Content-Length is required")
            try:
                length = int(raw_length)
            except ValueError as exc:
                raise ValueError("Content-Length is not an integer") from exc
            if length < 0:
                raise ValueError("Content-Length must be non-negative")
            if length > MAX_BODY_BYTES:
                raise ValueError(f"request body exceeds {MAX_BODY_BYTES} bytes")
            data = self.rfile.read(length)
            if len(data) != length:
                raise ValueError("request body ended early")
            try:
                text = data.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise ValueError("request body is not valid UTF-8") from exc
            try:
                return json.loads(text)
            except json.JSONDecodeError as exc:
                raise ValueError("request body is not valid JSON") from exc

        def _send(self, status: int, payload: dict) -> None:
            raw = json.dumps(payload).encode("utf-8")
            self.close_connection = True
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(raw)

    return Handler


class DecisionServer:
    """Threading HTTP server. Bind is checked before the socket is opened."""

    def __init__(
        self,
        engine: Engine | None = None,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        allow_remote: bool = False,
    ) -> None:
        ensure_local_bind(host, allow_remote)
        self.engine = MockEngine() if engine is None else engine
        self.host = host
        self.allow_remote = allow_remote
        self.httpd = _HTTPServer((host, port), build_handler(self.engine))
        self.httpd.daemon_threads = True
        self.port = int(self.httpd.server_address[1])
        self._thread: threading.Thread | None = None

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def serve_forever(self) -> None:
        self.httpd.serve_forever(poll_interval=0.1)

    def start(self) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(
            target=self.serve_forever,
            name="systemone-http",
            daemon=True,
        )
        self._thread.start()
        self.wait_until_ready()

    def wait_until_ready(self, timeout: float = 5.0) -> None:
        deadline = time.monotonic() + timeout
        last_error = "not started"
        while time.monotonic() < deadline:
            if self._thread is not None and not self._thread.is_alive():
                raise RuntimeError("server thread exited before it was ready")
            try:
                with urllib.request.urlopen(self.url + "/health", timeout=0.2) as resp:
                    if resp.status == 200:
                        return
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                last_error = str(exc)
                time.sleep(0.02)
        raise TimeoutError(last_error)

    def close(self) -> None:
        thread = self._thread
        if thread is not None and thread.is_alive():
            self.httpd.shutdown()
            thread.join(timeout=5)
        self.httpd.server_close()
        self._thread = None

    def __enter__(self) -> "DecisionServer":
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        self.close()
        return False
