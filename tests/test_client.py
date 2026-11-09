"""Client maps /decide JSON onto .answers and .model, and surfaces server errors."""

import socket
import unittest

import srcpath  # side effect: put src/ on sys.path
from systemone.client import SystemOneClient, SystemOneError
from systemone.engine import MockEngine
from systemone.server import DecisionServer


class SystemOneClientTests(unittest.TestCase):
    def setUp(self):
        self.server = DecisionServer(MockEngine(), host="127.0.0.1", port=0)
        self.server.start()
        self.addCleanup(self.server.close)
        self.client = SystemOneClient(self.server.url, timeout=2)

    def test_system_one_returns_answers_and_model(self):
        decision = self.client.system_one(
            "hello",
            {"ok": {"type": "noul", "instructions": "Is this a test?", "criteria": None}},
        )
        self.assertEqual(decision.answers, {"ok": {"p": 0.5}})
        self.assertEqual(decision.model, "mock")
        self.assertIsInstance(decision.latency_s, (int, float))
        health = self.client.health()
        self.assertEqual(health["status"], "ok")
        self.assertTrue(health["mock"])

    def test_http_error_includes_the_server_string(self):
        with self.assertRaises(SystemOneError) as caught:
            self.client.system_one("x", ["not", "an", "object"])
        self.assertEqual(str(caught.exception), "questions must be an object")

    def test_connection_failure_raises(self):
        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
        sock.close()
        client = SystemOneClient(f"http://127.0.0.1:{port}", timeout=1)
        with self.assertRaises(SystemOneError) as caught:
            client.health()
        self.assertIn(str(port), str(caught.exception))


if __name__ == "__main__":
    unittest.main()
