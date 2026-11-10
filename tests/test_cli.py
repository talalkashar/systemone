"""CLI via `python -m systemone.cli`. The mock server uses a free local port."""

import json
import os
import socket
import subprocess
import sys
import time
import unittest
import urllib.request
from pathlib import Path

import srcpath  # side effect: put src/ on sys.path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"


def _env(**extra):
    env = os.environ.copy()
    env.pop("SYSTEMONE_URL", None)
    previous = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(SRC) if not previous else str(SRC) + os.pathsep + previous
    env.update(extra)
    return env


def _run(args, env=None, timeout=10):
    return subprocess.run(
        [sys.executable, "-m", "systemone.cli", *args],
        cwd=ROOT,
        env=env or _env(),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def _free_port():
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


class VersionTests(unittest.TestCase):
    def test_version_matches_the_package(self):
        from systemone import __version__

        result = _run(["--version"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), f"systemone {__version__}")


class ServeTests(unittest.TestCase):
    def test_without_mock_exits_2_even_if_model_flag_is_set(self):
        result = _run(["serve"], env=_env(SYSTEMONE_MODEL="1"))
        self.assertEqual(result.returncode, 2)
        self.assertIn("real weights are not bundled", result.stderr)
        self.assertIn("--mock", result.stderr)
        self.assertIn("SYSTEMONE_MODEL=1", result.stderr)
        self.assertNotIn("import torch", result.stderr)

    def test_allow_remote_without_mock_still_refuses_weights(self):
        result = _run(["serve", "--allow-remote"])
        self.assertEqual(result.returncode, 2)
        self.assertIn("real weights are not bundled", result.stderr)

    def test_mock_serves_health_and_decide(self):
        port = _free_port()
        server = subprocess.Popen(
            [sys.executable, "-m", "systemone.cli", "serve", "--mock", "--port", str(port)],
            cwd=ROOT,
            env=_env(),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.addCleanup(self._stop, server)
        self._wait_until_up(server, port)
        health = _run(["health", "--url", f"http://127.0.0.1:{port}"])
        self.assertEqual(health.returncode, 0, health.stderr)
        self.assertEqual(json.loads(health.stdout)["mock"], True)

        decide = _run(
            [
                "decide",
                "--url",
                f"http://127.0.0.1:{port}",
                "--state",
                "customer asked for a refund",
                "--question",
                "needs_reply:noul:Does this email need a reply?",
                "--question",
                "route:choice:Which queue: billing or support?",
                "--criteria",
                "billing=Refunds, invoices, and payment issues",
                "--criteria",
                "support=How-to questions",
                "--question",
                "urgency:score:How urgent is this message?",
                "--score-label",
                "low",
                "--score-label",
                "normal",
                "--score-label",
                "high",
            ]
        )
        self.assertEqual(decide.returncode, 0, decide.stderr)
        body = json.loads(decide.stdout)
        self.assertEqual(body["model"], "mock")
        self.assertEqual(
            body["answers"],
            {
                "needs_reply": {"p": 0.5},
                "route": {"label": "billing"},
                "urgency": {"value": 1, "label": "normal"},
            },
        )

    def test_criteria_on_a_noul_question_is_a_usage_error(self):
        result = _run(
            [
                "decide",
                "--url",
                "http://127.0.0.1:9",
                "--question",
                "ok:noul:Is it?",
                "--criteria",
                "a=b",
            ]
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("most recent choice", result.stderr)
        self.assertEqual(result.stdout, "")

    def _wait_until_up(self, server, port):
        deadline = time.monotonic() + 20
        url = f"http://127.0.0.1:{port}/health"
        last = None
        while time.monotonic() < deadline:
            if server.poll() is not None:
                err = server.stderr.read() if server.stderr is not None else ""
                self.fail(f"server exited {server.returncode}: {err}")
            try:
                with urllib.request.urlopen(url, timeout=1) as response:
                    if response.status == 200:
                        return
            except OSError as exc:
                last = exc
                time.sleep(0.05)
        server.terminate()
        try:
            err = server.communicate(timeout=5)[1]
        except subprocess.TimeoutExpired:
            server.kill()
            err = server.communicate()[1]
        self.fail(f"mock server did not start: last error {last!r}; stderr: {err}")

    def _stop(self, server):
        if server.poll() is None:
            server.terminate()
            try:
                server.wait(timeout=3)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=3)
        if server.stderr is not None:
            server.stderr.close()


class QuestionsFromFlagsTests(unittest.TestCase):
    def test_order_criteria_score_labels_and_duplicate_name(self):
        from systemone.cli import questions_from_flags

        questions = questions_from_flags(
            [
                ("question", "ship:choice:Should it ship?"),
                ("criteria", "ci=builds"),
                ("criteria", "product=defects"),
                ("question", "risk:score:How risky?"),
                ("score_label", "low"),
                ("score_label", "high"),
            ]
        )
        self.assertEqual(list(questions), ["ship", "risk"])
        self.assertEqual(list(questions["ship"]["criteria"]), ["ci", "product"])
        self.assertEqual(
            questions["ship"]["criteria"],
            {"ci": "builds", "product": "defects"},
        )
        self.assertEqual(questions["risk"]["criteria"], ["low", "high"])
        with self.assertRaises(ValueError) as caught:
            questions_from_flags(
                [
                    ("question", "ok:noul:Is it?"),
                    ("question", "ok:noul:Again?"),
                ]
            )
        self.assertIn("duplicate", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
