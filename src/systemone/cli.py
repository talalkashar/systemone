"""Command line: serve, decide, health, install, and use.

`use` stays a dry run unless `--arm`. It never passes `--act`.
"""

import argparse
import json
import os
import sys
from pathlib import Path

from systemone import __version__
from systemone.client import SystemOneClient, SystemOneError
from systemone.computer_use import UseRefused, perform
from systemone.engine import MockEngine
from systemone.install import AGENTS, InstallError, apply_install, plan_install
from systemone.questions import QUESTION_TYPES, validate_questions, validate_state
from systemone.server import DEFAULT_HOST, DEFAULT_PORT, DecisionServer

DEFAULT_URL = "http://127.0.0.1:18100"
_NO_WEIGHTS = (
    "real weights are not bundled, use --mock, or set SYSTEMONE_MODEL=1 in a future release"
)


class _OrderedFlag(argparse.Action):
    """Record flags in argv order so criteria attach to the latest question."""

    def __call__(self, parser, namespace, values, option_string=None):
        sequence = getattr(namespace, "sequence", None)
        if sequence is None:
            sequence = []
            setattr(namespace, "sequence", sequence)
        sequence.append((self.dest, values))


def main(argv: list[str] | None = None) -> None:
    _configure_stdio()
    raise SystemExit(run(argv))


def run(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if args.command == "serve":
        return _serve(args)
    if args.command == "decide":
        return _decide(args)
    if args.command == "health":
        return _health(args)
    if args.command == "install":
        return _install(args)
    if args.command == "use":
        return _use(args)
    parser.error(f"unknown command {args.command}")
    return 2


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="systemone",
        description=(
            "The caller decides. systemone use is a dry run unless --arm, "
            "and it never passes --act. Mock answers are fixed wiring, not a model."
        ),
    )
    parser.add_argument("--version", action="version", version=f"systemone {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    serve =sub.add_parser("serve", help="listen for POST /decide")
    serve.add_argument("--port", type=int, default=DEFAULT_PORT)
    serve.add_argument(
        "--mock",
        action="store_true",
        help="serve fixed answers. This build has no model weights.",
    )
    serve.add_argument(
        "--allow-remote",
        action="store_true",
        help="bind 0.0.0.0. Off by default; the server otherwise stays on 127.0.0.1.",
    )

    decide = sub.add_parser("decide", help="ask a running server and print JSON")
    decide.add_argument("--url", default=None, help=f"default: SYSTEMONE_URL or {DEFAULT_URL}")
    decide.add_argument("--state", default=None, help="context string. Omit for null. Do not put secrets here.")
    decide.add_argument(
        "--question",
        action=_OrderedFlag,
        required=True,
        help="NAME:TYPE:INSTRUCTIONS. TYPE is noul, choice, or score. Repeatable.",
    )
    decide.add_argument(
        "--criteria",
        action=_OrderedFlag,
        help="LABEL=TEXT for the most recent choice question. Repeatable.",
    )
    decide.add_argument(
        "--score-label",
        action=_OrderedFlag,
        dest="score_label",
        help="one rung, low to high, for the most recent score question. Repeatable.",
    )
    decide.set_defaults(sequence=None)

    health = sub.add_parser("health", help="print GET /health JSON")
    health.add_argument("--url", default=None, help=f"default: SYSTEMONE_URL or {DEFAULT_URL}")

    install = sub.add_parser(
        "install",
        help="print the agent-config change. Write it only when --yes is passed.",
    )
    install.add_argument(
        "--agent",
        action="append",
        choices=AGENTS,
        help="which agent config to update. Repeatable. Default: claude-code, cursor, and codex.",
    )
    install.add_argument(
        "--yes",
        action="store_true",
        help="write the printed files under the current home. Without this, nothing is written.",
    )

    use = sub.add_parser(
        "use",
        help="check a computer-use handoff. Dry run unless --arm. Never passes --act.",
    )
    use.add_argument("--target", default="", help="window or control the caller already chose")
    use.add_argument("--request", default="", help="action the caller already chose")
    use.add_argument(
        "--arm",
        action="store_true",
        help="start jev-run without --act. Omit this and no process is started.",
    )
    return parser


def _serve(args: argparse.Namespace) -> int:
    if not args.mock:
        print(_NO_WEIGHTS, file=sys.stderr)
        return 2
    if args.port < 0 or args.port > 65535:
        print("port must be between 0 and 65535", file=sys.stderr)
        return 2
    host = "0.0.0.0" if args.allow_remote else DEFAULT_HOST
    try:
        server = DecisionServer(
            MockEngine(),
            host=host,
            port=args.port,
            allow_remote=args.allow_remote,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"could not bind {host}:{args.port}: {exc}", file=sys.stderr)
        return 2
    shown = DEFAULT_HOST if host == "0.0.0.0" else host
    print(
        f"listening on http://{shown}:{server.port} (bind {host}) model=mock",
        file=sys.stderr,
        flush=True,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    finally:
        server.httpd.server_close()
    return 0


def _decide(args: argparse.Namespace) -> int:
    try:
        state = validate_state(args.state)
        questions = questions_from_flags(args.sequence or [])
        validate_questions(questions)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    client = SystemOneClient(_resolve_url(args.url))
    try:
        decision = client.system_one(state, questions)
    except SystemOneError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    json.dump(
        {"answers": decision.answers, "latency_s": decision.latency_s, "model": decision.model},
        sys.stdout,
        indent=2,
        ensure_ascii=False,
    )
    sys.stdout.write("\n")
    return 0


def _use(args: argparse.Namespace) -> int:
    """Print the handoff. Start jev-run only when --arm is set, and never with --act."""
    try:
        code, body = perform(args.target, args.request, bool(args.arm))
    except UseRefused as exc:
        print(str(exc), file=sys.stderr)
        return 2
    json.dump(body, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
    return code


def _install(args: argparse.Namespace) -> int:
    """Print the config change. Write only under Path.home(), and only with --yes."""
    home = Path.home()
    agents = tuple(args.agent) if args.agent else AGENTS
    try:
        planned = plan_install(home, agents)
        report = apply_install(home, planned, yes=bool(args.yes))
    except InstallError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    sys.stdout.write(report)
    return 0


def _health(args: argparse.Namespace) -> int:
    client = SystemOneClient(_resolve_url(args.url))
    try:
        payload = client.health()
    except SystemOneError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    json.dump(payload, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


def questions_from_flags(sequence: list[tuple[str, str]]) -> dict:
    """Build a questions object. Criteria stick to the most recent matching question."""
    questions: dict = {}
    last: str | None = None
    for kind, value in sequence:
        if not isinstance(value, str):
            raise ValueError(f"{kind} must be a string")
        if kind == "question":
            name, qtype, instructions = _split_question(value)
            if name in questions:
                raise ValueError(f"duplicate question {name!r}")
            if qtype == "choice":
                criteria: dict | list | None = {}
            elif qtype == "score":
                criteria = []
            else:
                criteria = None
            questions[name] = {
                "type": qtype,
                "instructions": instructions,
                "criteria": criteria,
            }
            last = name
            continue
        if kind == "criteria":
            _require_recent(questions, last, "choice", "--criteria")
            if "=" not in value:
                raise ValueError("--criteria must be LABEL=TEXT")
            label, text = value.split("=", 1)
            if label == "":
                raise ValueError("--criteria label must not be empty")
            questions[last]["criteria"][label] = text
            continue
        if kind == "score_label":
            _require_recent(questions, last, "score", "--score-label")
            if value == "":
                raise ValueError("--score-label must not be empty")
            questions[last]["criteria"].append(value)
            continue
        raise ValueError(f"unknown decide flag {kind}")
    if not questions:
        raise ValueError("at least one --question is required")
    return questions


def _split_question(value: str) -> tuple[str, str, str]:
    parts = value.split(":", 2)
    if len(parts) != 3 or parts[0] == "":
        raise ValueError("--question must be NAME:TYPE:INSTRUCTIONS")
    name, qtype, instructions = parts
    if qtype not in QUESTION_TYPES:
        raise ValueError("--question TYPE must be noul, choice, or score")
    return name, qtype, instructions


def _require_recent(questions: dict, last: str | None, expected: str, flag: str) -> None:
    if last is None or questions[last]["type"] != expected:
        kind = "choice" if expected == "choice" else "score"
        raise ValueError(f"{flag} applies to the most recent {kind} question")


def _resolve_url(explicit: str | None) -> str:
    if explicit:
        return explicit
    return os.environ.get("SYSTEMONE_URL") or DEFAULT_URL


def _configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8")
            except (OSError, ValueError):
                return


if __name__ == "__main__":
    main()
