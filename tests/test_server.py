"""HTTP server on an ephemeral port. Never binds a public interface in tests."""

import json
import socket
import sys
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest import mock

import srcpath  # side effect: put src/ on sys.path
from systemone.engine import MockEngine
from systemone.server import DecisionServer, decide_payload, ensure_local_bind


def _request(method, url, payload=None):
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=2) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            return exc.code, json.loads(exc.read().decode("utf-8"))
        finally:
            exc.close()


class DecisionServerTests(unittest.TestCase):
    def test_start_does_no_reverse_dns_lookup(self):
        # getfqdn() can stall startup for many seconds on some Macs (it did on GitHub's macOS runners).
        with mock.patch.object(socket, "getfqdn", side_effect=AssertionError("getfqdn called")), \
                DecisionServer(port=0) as server:
            with urllib.request.urlopen(server.url + "/health", timeout=5) as resp:
                self.assertEqual(resp.status, 200)

    def setUp(self):
        self.server = DecisionServer(MockEngine(), host="127.0.0.1", port=0)
        self.server.start()
        self.addCleanup(self.server.close)

    def test_health(self):
        status, body = _request("GET", self.server.url + "/health")
        self.assertEqual(status, 200)
        self.assertEqual(body, {"status": "ok", "model": "mock", "mock": True})

    def test_decide(self):
        status, body = _request(
            "POST",
            self.server.url + "/decide",
            {
                "state": None,
                "questions": {
                    "ok": {"type": "noul", "instructions": "Is it ready?", "criteria": None},
                    "route": {
                        "type": "choice",
                        "instructions": "Pick",
                        "criteria": {"zeta": "z", "alpha": "a"},
                    },
                },
            },
        )
        self.assertEqual(status, 200)
        self.assertEqual(set(body), {"answers", "latency_s", "model"})
        self.assertEqual(body["model"], "mock")
        self.assertGreaterEqual(body["latency_s"], 0)
        self.assertEqual(body["answers"]["ok"], {"p": 0.5})
        self.assertEqual(body["answers"]["route"], {"label": "zeta"})

    def test_bad_questions_are_400(self):
        status, body = _request(
            "POST",
            self.server.url + "/decide",
            {"state": "x", "questions": []},
        )
        self.assertEqual(status, 400)
        self.assertEqual(body["error"], "questions must be an object")

    def test_unknown_path_and_wrong_method(self):
        status, body = _request("GET", self.server.url + "/missing")
        self.assertEqual(status, 404)
        self.assertEqual(body["error"], "not found")
        status, body = _request("POST", self.server.url + "/health", {})
        self.assertEqual(status, 405)
        status, body = _request("GET", self.server.url + "/decide")
        self.assertEqual(status, 405)

    def test_import_and_source_do_not_load_torch(self):
        self.assertNotIn("torch", sys.modules)
        root = Path(__file__).resolve().parents[1] / "src"
        for path in root.rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("import torch", text)
            self.assertNotIn("transformers", text)


class BindGuardTests(unittest.TestCase):
    def test_wildcard_is_refused_before_bind(self):
        with self.assertRaises(ValueError) as caught:
            ensure_local_bind("0.0.0.0", allow_remote=False)
        self.assertIn("0.0.0.0", str(caught.exception))
        self.assertIn("--allow-remote", str(caught.exception))
        ensure_local_bind("0.0.0.0", allow_remote=True)
        ensure_local_bind("127.0.0.1", allow_remote=False)
        with self.assertRaises(ValueError):
            DecisionServer(MockEngine(), host="0.0.0.0", port=0, allow_remote=False)

    def test_public_host_is_refused_and_loopback_names_are_allowed(self):
        with self.assertRaises(ValueError) as caught:
            ensure_local_bind("8.8.8.8", allow_remote=False)
        self.assertIn("8.8.8.8", str(caught.exception))
        ensure_local_bind("8.8.8.8", allow_remote=True)
        ensure_local_bind("localhost", allow_remote=False)
        ensure_local_bind("::1", allow_remote=False)

    def test_decide_payload_rejects_a_non_object_and_missing_questions(self):
        engine = MockEngine()
        with self.assertRaises(ValueError) as caught:
            decide_payload(engine, ["nope"])
        self.assertIn("JSON object", str(caught.exception))
        with self.assertRaises(ValueError) as caught:
            decide_payload(engine, {"state": None})
        self.assertIn("questions is required", str(caught.exception))


class DecideBodyTests(unittest.TestCase):
    def test_non_utf8_body_is_400(self):
        server = DecisionServer(MockEngine(), host="127.0.0.1", port=0)
        server.start()
        self.addCleanup(server.close)
        request = urllib.request.Request(
            server.url + "/decide",
            data=b"\xff",
            method="POST",
        )
        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(request, timeout=2)
        self.assertEqual(caught.exception.code, 400)
        try:
            body = json.loads(caught.exception.read().decode("utf-8"))
        finally:
            caught.exception.close()
        self.assertEqual(body["error"], "request body is not valid UTF-8")


if __name__ == "__main__":
    unittest.main()
