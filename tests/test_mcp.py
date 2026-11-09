"""Spawn the stdio MCP server and talk newline-delimited JSON-RPC to it."""

import json
import os
import select
import subprocess
import sys
import threading
import time
import unittest
from pathlib import Path

import srcpath  # side effect: put src/ on sys.path
from systemone.engine import MockEngine
from systemone.server import DecisionServer

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"


class McpProcess:
    def __init__(self, url: str | None):
        env = os.environ.copy()
        env.pop("SYSTEMONE_URL", None)
        previous = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = str(SRC) if not previous else str(SRC) + os.pathsep + previous
        if url is not None:
            env["SYSTEMONE_URL"] = url
        self.stderr_lines: list[str] = []
        self.proc = subprocess.Popen(
            [sys.executable, "-m", "systemone.mcp_server"],
            cwd=ROOT,
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0,
        )
        self._buffer = bytearray()
        self._drain = threading.Thread(target=self._read_stderr, daemon=True)
        self._drain.start()

    def _read_stderr(self):
        assert self.proc.stderr is not None
        for line in self.proc.stderr:
            self.stderr_lines.append(line.decode("utf-8", errors="replace"))

    def send(self, payload: dict) -> None:
        assert self.proc.stdin is not None
        raw = json.dumps(payload, separators=(",", ":")).encode("utf-8") + b"\n"
        self.proc.stdin.write(raw)
        self.proc.stdin.flush()

    def recv(self, timeout: float = 5):
        deadline = time.monotonic() + timeout
        assert self.proc.stdout is not None
        fd = self.proc.stdout.fileno()
        while time.monotonic() < deadline:
            while b"\n" in self._buffer:
                line, _, rest = self._buffer.partition(b"\n")
                self._buffer = bytearray(rest)
                if line.strip() == b"":
                    continue
                return json.loads(line.decode("utf-8"))
            remaining = max(0.05, deadline - time.monotonic())
            ready, _, _ = select.select([fd], [], [], min(0.2, remaining))
            if not ready:
                if self.proc.poll() is not None:
                    break
                continue
            chunk = os.read(fd, 65536)
            if chunk == b"":
                break
            self._buffer.extend(chunk)
        raise AssertionError(
            "no JSON-RPC response\nstderr:\n" + "".join(self.stderr_lines)
        )

    def close(self):
        if self.proc.poll() is None and self.proc.stdin is not None:
            try:
                self.proc.stdin.close()
            except OSError:
                pass
            try:
                self.proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.proc.terminate()
                try:
                    self.proc.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self.proc.kill()
                    self.proc.wait(timeout=2)
        self._drain.join(timeout=2)
        for stream in (self.proc.stdin, self.proc.stdout, self.proc.stderr):
            if stream is not None and not stream.closed:
                stream.close()


class McpServerTests(unittest.TestCase):
    def setUp(self):
        self.http = DecisionServer(MockEngine(), host="127.0.0.1", port=0)
        self.http.start()
        self.addCleanup(self.http.close)
        self.mcp = McpProcess(self.http.url)
        self.addCleanup(self.mcp.close)

    def _initialize(self, protocol="2025-06-18", request_id=1):
        self.mcp.send(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": "initialize",
                "params": {
                    "protocolVersion": protocol,
                    "capabilities": {},
                    "clientInfo": {"name": "test", "version": "0"},
                },
            }
        )
        return self.mcp.recv()

    def test_initialize_tools_and_decide(self):
        initialized = self._initialize("2024-11-05")
        self.assertEqual(initialized["id"], 1)
        result = initialized["result"]
        self.assertEqual(result["protocolVersion"], "2024-11-05")
        self.assertIn("tools", result["capabilities"])
        self.assertEqual(result["serverInfo"], {"name": "systemone", "version": "0.1.0"})
        self.assertIn("untrusted", result["instructions"])

        self.mcp.send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        self.mcp.send({"jsonrpc": "2.0", "id": 2, "method": "ping"})
        ping = self.mcp.recv()
        self.assertEqual(ping["id"], 2)
        self.assertEqual(ping["result"], {})

        self.mcp.send({"jsonrpc": "2.0", "id": 3, "method": "tools/list"})
        listed = self.mcp.recv()
        names = [tool["name"] for tool in listed["result"]["tools"]]
        self.assertEqual(names, ["health", "decide"])

        token = "SECRET-STATE-TOKEN"
        self.mcp.send(
            {
                "jsonrpc": "2.0",
                "id": 4,
                "method": "tools/call",
                "params": {
                    "name": "decide",
                    "arguments": {
                        "state": token,
                        "questions": {
                            "route": {
                                "type": "choice",
                                "instructions": "Which queue?",
                                "criteria": {"billing": "money", "support": "help"},
                            }
                        },
                    },
                },
            }
        )
        called = self.mcp.recv()
        self.assertEqual(called["id"], 4)
        self.assertIs(called["result"]["isError"], False)
        text = called["result"]["content"][0]["text"]
        self.assertNotIn("\n", text)
        body = json.loads(text)
        self.assertEqual(body["model"], "mock")
        self.assertEqual(body["answers"]["route"], {"label": "billing"})
        self.assertNotIn(token, text)
        self.assertNotIn(token, "".join(self.mcp.stderr_lines))

        self.mcp.send(
            {"jsonrpc": "2.0", "id": 5, "method": "tools/call", "params": {"name": "health"}}
        )
        health = self.mcp.recv()
        health_body = json.loads(health["result"]["content"][0]["text"])
        self.assertEqual(health_body["status"], "ok")
        self.assertTrue(health_body["mock"])

    def test_unknown_protocol_falls_back(self):
        response = self._initialize("1999-01-01")
        self.assertEqual(response["result"]["protocolVersion"], "2025-06-18")

    def test_unknown_method_parse_error_and_bad_params(self):
        self.mcp.send({"jsonrpc": "2.0", "id": 7, "method": "nope"})
        unknown = self.mcp.recv()
        self.assertEqual(unknown["error"]["code"], -32601)

        assert self.mcp.proc.stdin is not None
        self.mcp.proc.stdin.write(b"not json\n")
        self.mcp.proc.stdin.flush()
        parsed = self.mcp.recv()
        self.assertIsNone(parsed["id"])
        self.assertEqual(parsed["error"]["code"], -32700)

        self.mcp.send(
            {
                "jsonrpc": "2.0",
                "id": 8,
                "method": "tools/call",
                "params": {"name": "decide", "arguments": {"state": ""}},
            }
        )
        bad = self.mcp.recv()
        self.assertEqual(bad["error"]["code"], -32602)

        self.mcp.send(
            {
                "jsonrpc": "2.0",
                "id": 9,
                "method": "tools/call",
                "params": {"name": "health", "arguments": {"extra": True}},
            }
        )
        self.assertEqual(self.mcp.recv()["error"]["code"], -32602)


class McpDownTests(unittest.TestCase):
    def test_health_is_an_error_when_the_server_is_down(self):
        mcp = McpProcess("http://127.0.0.1:9")
        self.addCleanup(mcp.close)
        mcp.send({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        self.assertEqual(mcp.recv()["result"]["serverInfo"]["name"], "systemone")
        mcp.send(
            {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "health"}}
        )
        response = mcp.recv()
        self.assertNotIn("error", response)
        self.assertIs(response["result"]["isError"], True)
        text = response["result"]["content"][0]["text"]
        self.assertIn("systemone serve --mock", text)


if __name__ == "__main__":
    unittest.main()
