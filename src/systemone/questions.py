"""Validate `/decide` question maps. Raises ValueError with a stable message."""

MAX_QUESTIONS = 32
MAX_INSTRUCTION_CHARS = 2000
MAX_CHOICE_LABELS = 64
MAX_SCORE_LABELS = 16
MAX_STATE_CHARS = 100_000

QUESTION_TYPES = ("noul", "choice", "score")


def validate_state(state: object) -> str | None:
    """Return state when it is null or a string inside the size cap."""
    if state is None:
        return None
    if not isinstance(state, str):
        raise ValueError("state must be a string or null")
    if len(state) > MAX_STATE_CHARS:
        raise ValueError(f"state exceeds {MAX_STATE_CHARS} characters")
    return state


def validate_questions(questions: object) -> dict:
    """Return a normalized questions object, or raise ValueError."""
    if not isinstance(questions, dict):
        raise ValueError("questions must be an object")
    if len(questions) > MAX_QUESTIONS:
        raise ValueError(f"at most {MAX_QUESTIONS} questions are allowed")

    normalized: dict = {}
    for name, raw in questions.items():
        if not isinstance(name, str) or name == "":
            raise ValueError("question names must be non-empty strings")
        if not isinstance(raw, dict):
            raise ValueError(f"question {name!r} must be an object")
        normalized[name] = _one_question(name, raw)
    return normalized


def _one_question(name: str, raw: dict) -> dict:
    if "type" not in raw:
        raise ValueError(f"question {name!r} is missing type")
    qtype = raw["type"]
    if qtype not in QUESTION_TYPES:
        raise ValueError(f"question {name!r} type must be noul, choice, or score")
    if "instructions" not in raw:
        raise ValueError(f"question {name!r} is missing instructions")
    instructions = raw["instructions"]
    if not isinstance(instructions, str):
        raise ValueError(f"question {name!r} instructions must be a string")
    if len(instructions) > MAX_INSTRUCTION_CHARS:
        raise ValueError(
            f"question {name!r} instructions exceed {MAX_INSTRUCTION_CHARS} characters"
        )
    criteria = raw["criteria"] if "criteria" in raw else None
    return {
        "type": qtype,
        "instructions": instructions,
        "criteria": _criteria(name, qtype, criteria),
    }


def _criteria(name: str, qtype: str, criteria: object) -> dict | list | None:
    if qtype == "noul":
        if criteria is not None:
            raise ValueError(f"noul question {name!r} does not take criteria")
        return None
    if qtype == "choice":
        return _choice_criteria(name, criteria)
    return _score_criteria(name, criteria)


def _choice_criteria(name: str, criteria: object) -> dict:
    if not isinstance(criteria, dict):
        raise ValueError(
            f"choice question {name!r} requires criteria, an object of label to description"
        )
    if len(criteria) == 0:
        raise ValueError(f"choice question {name!r} criteria must not be empty")
    if len(criteria) > MAX_CHOICE_LABELS:
        raise ValueError(
            f"choice question {name!r} has more than {MAX_CHOICE_LABELS} labels"
        )
    copied: dict = {}
    for label, description in criteria.items():
        if not isinstance(label, str) or label == "":
            raise ValueError(f"choice question {name!r} labels must be non-empty strings")
        if not isinstance(description, str):
            raise ValueError(
                f"choice question {name!r} description for {label!r} must be a string"
            )
        copied[label] = description
    return copied


def _score_criteria(name: str, criteria: object) -> list:
    if isinstance(criteria, str) or not isinstance(criteria, list):
        raise ValueError(
            f"score question {name!r} requires criteria, a list of labels from low to high"
        )
    if len(criteria) == 0:
        raise ValueError(f"score question {name!r} criteria must not be empty")
    if len(criteria) > MAX_SCORE_LABELS:
        raise ValueError(
            f"score question {name!r} has more than {MAX_SCORE_LABELS} labels"
        )
    labels: list = []
    for label in criteria:
        if not isinstance(label, str) or label == "":
            raise ValueError(f"score question {name!r} labels must be non-empty strings")
        labels.append(label)
    return labels
