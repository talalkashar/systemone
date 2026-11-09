"""HTTP server on an ephemeral port. Never binds a public interface in tests."""

import json
import sys
import unittest
import urllib.error
import urllib.request
from pathlib import Path

import srcpath  # side effect: put src/ on sys.path
from systemone.engine import MockEngine
from systemone.server import DecisionServer, ensure_local_bind


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


if __name__ == "__main__":
    unittest.main()
