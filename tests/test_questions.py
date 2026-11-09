"""Caps and shape checks for state and questions."""

import unittest

import srcpath  # side effect: put src/ on sys.path
from systemone.questions import (
    MAX_CHOICE_LABELS,
    MAX_INSTRUCTION_CHARS,
    MAX_QUESTIONS,
    MAX_SCORE_LABELS,
    MAX_STATE_CHARS,
    validate_questions,
    validate_state,
)


def _noul(text="Is this true?"):
    return {"type": "noul", "instructions": text, "criteria": None}


def _choice(labels):
    return {
        "type": "choice",
        "instructions": "Pick one",
        "criteria": {label: f"about {label}" for label in labels},
    }


def _score(labels):
    return {"type": "score", "instructions": "Rank it", "criteria": list(labels)}


class ValidateStateTests(unittest.TestCase):
    def test_null_and_empty_and_cap(self):
        self.assertIsNone(validate_state(None))
        self.assertEqual(validate_state(""), "")
        self.assertEqual(validate_state("a" * MAX_STATE_CHARS), "a" * MAX_STATE_CHARS)

    def test_rejects_non_string_and_oversize(self):
        with self.assertRaises(ValueError) as caught:
            validate_state(3)
        self.assertIn("string or null", str(caught.exception))
        with self.assertRaises(ValueError) as caught:
            validate_state("a" * (MAX_STATE_CHARS + 1))
        self.assertIn(str(MAX_STATE_CHARS), str(caught.exception))


class ValidateQuestionsTests(unittest.TestCase):
    def test_normalizes_three_types_and_keeps_order(self):
        questions = validate_questions(
            {
                "ok": _noul(),
                "route": {
                    "type": "choice",
                    "instructions": "Which queue?",
                    "criteria": {"zeta": "last letter", "alpha": "first letter"},
                },
                "rank": _score(["low", "high"]),
            }
        )
        self.assertEqual(list(questions), ["ok", "route", "rank"])
        self.assertIsNone(questions["ok"]["criteria"])
        self.assertEqual(list(questions["route"]["criteria"]), ["zeta", "alpha"])
        self.assertEqual(questions["rank"]["criteria"], ["low", "high"])

    def test_omitted_noul_criteria_is_null(self):
        questions = validate_questions({"ok": {"type": "noul", "instructions": "Yes?"}})
        self.assertIsNone(questions["ok"]["criteria"])

    def test_rejects_a_non_object(self):
        with self.assertRaises(ValueError) as caught:
            validate_questions(["ok"])
        self.assertEqual(str(caught.exception), "questions must be an object")

    def test_question_cap(self):
        allowed = {f"q{i}": _noul() for i in range(MAX_QUESTIONS)}
        self.assertEqual(len(validate_questions(allowed)), MAX_QUESTIONS)
        allowed[f"q{MAX_QUESTIONS}"] = _noul()
        with self.assertRaises(ValueError) as caught:
            validate_questions(allowed)
        self.assertIn("32", str(caught.exception))

    def test_instruction_cap(self):
        validate_questions({"ok": _noul("a" * MAX_INSTRUCTION_CHARS)})
        with self.assertRaises(ValueError) as caught:
            validate_questions({"ok": _noul("a" * (MAX_INSTRUCTION_CHARS + 1))})
        self.assertIn("2000", str(caught.exception))

    def test_choice_label_cap_and_order(self):
        labels = [f"l{i:02d}" for i in range(MAX_CHOICE_LABELS)]
        parsed = validate_questions({"route": _choice(labels)})
        self.assertEqual(list(parsed["route"]["criteria"]), labels)
        with self.assertRaises(ValueError) as caught:
            validate_questions({"route": _choice(labels + ["extra"])})
        self.assertIn("64", str(caught.exception))

    def test_score_label_cap(self):
        labels = [f"s{i}" for i in range(MAX_SCORE_LABELS)]
        self.assertEqual(len(validate_questions({"rank": _score(labels)})["rank"]["criteria"]), 16)
        with self.assertRaises(ValueError) as caught:
            validate_questions({"rank": _score(labels + ["extra"])})
        self.assertIn("16", str(caught.exception))

    def test_bad_shapes(self):
        cases = [
            {"ok": "yes"},
            {"ok": {"instructions": "Yes?"}},
            {"ok": {"type": "maybe", "instructions": "Yes?"}},
            {"ok": {"type": "noul", "instructions": 1}},
            {"ok": {"type": "noul", "instructions": "Yes?", "criteria": {"a": "b"}}},
            {"route": {"type": "choice", "instructions": "Pick", "criteria": ["a"]}},
            {"route": {"type": "choice", "instructions": "Pick", "criteria": {}}},
            {"route": {"type": "choice", "instructions": "Pick", "criteria": {"": "x"}}},
            {"route": {"type": "choice", "instructions": "Pick", "criteria": {"a": 1}}},
            {"rank": {"type": "score", "instructions": "Rank", "criteria": "low"}},
            {"rank": {"type": "score", "instructions": "Rank", "criteria": []}},
            {"rank": {"type": "score", "instructions": "Rank", "criteria": ["ok", ""]}},
            {"": _noul()},
        ]
        for raw in cases:
            with self.subTest(raw=raw):
                with self.assertRaises(ValueError):
                    validate_questions(raw)

    def test_does_not_mutate_the_caller(self):
        criteria = {"billing": "money"}
        raw = {"route": {"type": "choice", "instructions": "Pick", "criteria": criteria}}
        parsed = validate_questions(raw)
        parsed["route"]["criteria"]["extra"] = "nope"
        self.assertEqual(criteria, {"billing": "money"})


if __name__ == "__main__":
    unittest.main()
