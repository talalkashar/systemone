"""Drive the shipped `systemone use` command. The stand-in jev-run only records argv."""

import json
import stat
import sys
import tempfile
import unittest
from pathlib import Path

import srcpath  # side effect: put src/ on sys.path
from test_cli import _env, _run

_SURFACES = (
    ("banking", "banking"),
    ("mail", "mail"),
    ("messages", "messages"),
    ("password managers", "password managers"),
    ("Mason or student records", "Mason or student records"),
    ("admin consoles", "admin consoles"),
    ("login or MFA", "login or MFA"),
    ("mail", "Mail"),
    ("password managers", "1Password"),
    ("Mason or student records", "Patriot Web"),
    ("Mason or student records", "student records"),
    ("admin consoles", "admin console"),
    ("login or MFA", "MFA"),
    ("banking", "credit card"),
)


class UseCommandTests(unittest.TestCase):
    def setUp(self):
        self._temp = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp.cleanup)
        root = Path(self._temp.name)
        self.bin_dir = root / "bin"
        self.bin_dir.mkdir()
        self.log = root / "argv.log"
        script = self.bin_dir / "jev-run"
        script.write_text(
            f"#!{sys.executable}\n"
            "import os\n"
            "import sys\n"
            "from pathlib import Path\n"
            "Path(os.environ['SYSTEMONE_USE_ARGV']).write_text(\n"
            "    '\\n'.join(sys.argv) + '\\n', encoding='utf-8'\n"
            ")\n",
            encoding="utf-8",
        )
        script.chmod(script.stat().st_mode | stat.S_IEXEC)

    def _child_env(self, path: Path | None = None):
        return _env(PATH=str(path or self.bin_dir), SYSTEMONE_USE_ARGV=str(self.log))

    def test_dry_run_starts_nothing_and_names_the_caller(self):
        result = _run(
            ["use", "--target", "Notes", "--request", "count the windows"],
            env=self._child_env(),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        body = json.loads(result.stdout)
        self.assertEqual(body["mode"], "dry-run")
        self.assertEqual(body["decision_maker"], "caller")
        self.assertNotEqual(body["decision_maker"], "jev")
        self.assertEqual(body["hands"], "jev")
        self.assertEqual(body["target"], "Notes")
        self.assertEqual(body["request"], "count the windows")
        self.assertFalse(body["started"])
        self.assertNotIn("model", body)
        self.assertNotIn("mock", result.stdout)
        self.assertNotIn("--act", result.stdout)
        self.assertFalse(self.log.exists())
        print("dry-run: no child argv contains --act; decision_maker is caller")

    def test_missing_target_is_refused(self):
        result = _run(["use", "--request", "count the windows"], env=self._child_env())
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("a named target is required", result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertFalse(self.log.exists())
        print("missing target refused")

    def test_blank_target_is_refused(self):
        result = _run(
            ["use", "--target", "   ", "--request", "count the windows"],
            env=self._child_env(),
        )
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("a named target is required", result.stderr)
        self.assertFalse(self.log.exists())

    def test_missing_request_is_refused(self):
        result = _run(["use", "--target", "Notes"], env=self._child_env())
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("a request is required", result.stderr)
        self.assertFalse(self.log.exists())

    def test_each_sensitive_surface_is_refused_before_spawn(self):
        seen = set()
        for name, phrase in _SURFACES:
            for armed in (False, True):
                args = ["use", "--target", "Notes", "--request", phrase]
                if armed:
                    args.append("--arm")
                result = _run(args, env=self._child_env())
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                self.assertIn(f"refusing a sensitive surface: {name}", result.stderr)
                self.assertEqual(result.stdout, "")
                self.assertFalse(self.log.exists(), phrase)
            seen.add(name)
            print(f"refused surface: {name}")
        self.assertEqual(
            seen,
            {
                "banking",
                "mail",
                "messages",
                "password managers",
                "Mason or student records",
                "admin consoles",
                "login or MFA",
            },
        )

    def test_sensitive_target_is_refused_when_armed(self):
        result = _run(
            ["use", "--arm", "--target", "Mail", "--request", "count the windows"],
            env=self._child_env(),
        )
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("refusing a sensitive surface: mail", result.stderr)
        self.assertFalse(self.log.exists())

    def test_act_token_is_refused_and_not_spawned(self):
        for args in (
            ["use", "--arm", "--target", "Notes", "--request=--act"],
            ["use", "--arm", "--target=--act", "--request", "count the windows"],
            ["use", "--arm", "--target", "Notes", "--request", "count the windows --act"],
        ):
            result = _run(args, env=self._child_env())
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertIn("refusing to pass --act", result.stderr)
            self.assertFalse(self.log.exists(), args)

    def test_arm_starts_recorder_without_act(self):
        result = _run(
            ["use", "--arm", "--target", "Notes", "--request", "count the windows"],
            env=self._child_env(),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        body = json.loads(result.stdout)
        self.assertEqual(body["mode"], "armed")
        self.assertEqual(body["decision_maker"], "caller")
        self.assertNotEqual(body["decision_maker"], "jev")
        self.assertFalse(body["decision_maker"] == "mock")
        self.assertEqual(body["hands"], "jev")
        self.assertTrue(body["started"])
        self.assertNotIn("model", body)
        self.assertNotIn("mock", result.stdout)
        argv = self.log.read_text(encoding="utf-8").splitlines()
        self.assertTrue(argv[0].endswith("jev-run"))
        self.assertEqual(
            argv[1:],
            ["--expect", "Notes", "--target", "Notes", "--text", "count the windows"],
        )
        self.assertNotIn("--act", argv)
        print("armed recorder argv has no --act; decision_maker is caller")

    def test_arm_without_jev_run_starts_nothing(self):
        empty = Path(self._temp.name) / "empty"
        empty.mkdir()
        result = _run(
            ["use", "--arm", "--target", "Notes", "--request", "count the windows"],
            env=self._child_env(empty),
        )
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("jev-run is not on PATH. Nothing was run.", result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertFalse(self.log.exists())

    def test_help_offers_arm_and_has_no_act_flag(self):
        result = _run(["use", "--help"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--arm", result.stdout)
        self.assertIn("--target", result.stdout)
        self.assertNotRegex(result.stdout, r"(?m)^\s*--act\b")


class SurfaceListTests(unittest.TestCase):
    """Names ported from the jev fork's sensitive-surface gate, and ordinary targets that stay allowed."""

    def test_named_apps_sites_and_codes_are_refused(self):
        from systemone.computer_use import sensitive_surface

        cases = {
            "banking": ("PayPal", "open Venmo", "Coinbase", "Wallet", "Wells Fargo"),
            "messages": ("Signal", "WhatsApp", "Telegram"),
            "password managers": ("Passwords",),
            "Mason or student records": ("ssbstudent.gmu.edu", "financial aid", "tuition", "degree evaluation"),
            "admin consoles": ("https://admin.google.com", "console.cloud.google.com", "platform.openai.com"),
            "login or MFA": ("type the verification code", "Duo Security", "two-factor", "accounts.google.com"),
        }
        for name, phrases in cases.items():
            for phrase in phrases:
                with self.subTest(phrase=phrase):
                    self.assertEqual(sensitive_surface("Safari", phrase), name)

    def test_ordinary_targets_are_allowed(self):
        from systemone.computer_use import sensitive_surface

        for target, request in (("Notes", "count the windows"), ("Finder", "open the Downloads folder"),
                                ("Calendar", "show next week"), ("System Settings", "turn on dark mode")):
            with self.subTest(target=target):
                self.assertIsNone(sensitive_surface(target, request))
