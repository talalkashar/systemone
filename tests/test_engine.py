"""MockEngine is deterministic and does not invent labels."""

import unittest

import srcpath  # side effect: put src/ on sys.path
from systemone import __version__
from systemone.engine import Engine, MockEngine


def _questions():
    return {
        "ok": {"type": "noul", "instructions": "Is this a test?", "criteria": None},
        "route": {
            "type": "choice",
            "instructions": "Which one?",
            "criteria": {"zeta": "later", "alpha": "earlier"},
        },
        "rank": {
            "type": "score",
            "instructions": "How high?",
            "criteria": ["low", "mid", "high"],
        },
    }


class MockEngineTests(unittest.TestCase):
    def setUp(self):
        self.engine = MockEngine()

    def test_version_and_protocol(self):
        self.assertEqual(__version__, "0.1.0")
        self.assertIsInstance(self.engine, Engine)
        self.assertEqual(self.engine.model, "mock")

    def test_fixed_answers(self):
        answers = self.engine.decide("anything", _questions())
        self.assertEqual(answers["ok"], {"p": 0.5})
        self.assertEqual(answers["route"], {"label": "zeta"})
        self.assertEqual(answers["rank"], {"value": 1, "label": "mid"})

    def test_same_input_same_output(self):
        first = self.engine.decide(None, _questions())
        second = self.engine.decide("different state", _questions())
        self.assertEqual(first, second)

    def test_score_middle_for_even_and_odd_and_singleton(self):
        one = self.engine.decide(None, {"r": {"type": "score", "instructions": "r", "criteria": ["only"]}})
        two = self.engine.decide(
            None,
            {"r": {"type": "score", "instructions": "r", "criteria": ["low", "high"]}},
        )
        four = self.engine.decide(
            None,
            {"r": {"type": "score", "instructions": "r", "criteria": ["a", "b", "c", "d"]}},
        )
        self.assertEqual(one["r"], {"value": 0, "label": "only"})
        self.assertEqual(two["r"], {"value": 0, "label": "low"})
        self.assertEqual(four["r"], {"value": 1, "label": "b"})

    def test_rejects_bad_questions(self):
        with self.assertRaises(ValueError):
            self.engine.decide(None, {"ok": {"type": "noul", "instructions": "x", "criteria": []}})


if __name__ == "__main__":
    unittest.main()
