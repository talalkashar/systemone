"""Decision backends. This release ships the deterministic mock only."""

from typing import Protocol, runtime_checkable

from systemone.questions import validate_questions, validate_state


@runtime_checkable
class Engine(Protocol):
    """Something that can answer a closed question map."""

    model: str

    def decide(self, state: str | None, questions: dict) -> dict:
        """Return answers keyed by question name. Do not return prose."""


class MockEngine:
    """Fixed answers for wiring tests. Not a model and not a judgment."""

    model = "mock"

    def decide(self, state: str | None, questions: dict) -> dict:
        state = validate_state(state)
        questions = validate_questions(questions)
        del state  # the mock must not look like it read the context
        answers: dict = {}
        for name, question in questions.items():
            answers[name] = _mock_answer(question)
        return answers


def _mock_answer(question: dict) -> dict:
    qtype = question["type"]
    if qtype == "noul":
        return {"p": 0.5}
    if qtype == "choice":
        # Insertion order, not alphabetical. Callers supply the labels.
        label = next(iter(question["criteria"]))
        return {"label": label}
    labels = question["criteria"]
    # Even ladders use the lower of the two middle rungs.
    index = (len(labels) - 1) // 2
    return {"value": index, "label": labels[index]}
