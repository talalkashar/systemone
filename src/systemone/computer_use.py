"""Hand a computer-use action to jev. The caller has already decided.

This module checks the handoff and, only when armed, starts `jev-run` without
`--act`. It does not choose the action and it does not call the mock engine.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass

class UseRefused(Exception):
    """The handoff must not run."""


@dataclass(frozen=True)
class UsePlan:
    mode: str
    target: str
    request: str


_SURFACES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("banking", re.compile(r"\b(bank|banking|credit\s+card|debit\s+card)\b", re.I)),
    ("mail", re.compile(r"\b(mail|e-mail|email|gmail|outlook)\b", re.I)),
    ("messages", re.compile(r"\b(messages|imessage|sms)\b", re.I)),
    (
        "password managers",
        re.compile(r"\b(password\s+managers?|1password|bitwarden|lastpass|keychain|dashlane)\b", re.I),
    ),
    (
        "Mason or student records",
        re.compile(r"\b(mason|patriot\s*web|student\s+records?)\b", re.I),
    ),
    ("admin consoles", re.compile(r"\b(admin(?:istrator)?\s+consoles?)\b", re.I)),
    (
        "login or MFA",
        re.compile(r"\b(mfa|2fa|multi-factor|one-time\s+code|log\s*in|login|sign[\s-]?in)\b", re.I),
    ),
)


def sensitive_surface(*parts: str) -> str | None:
    """Return the refused surface name, or None when the text is allowed."""
    text = "\n".join(parts)
    for name, pattern in _SURFACES:
        if pattern.search(text):
            return name
    return None


def plan_use(target: str | None, request: str | None, armed: bool) -> UsePlan:
    """Decide whether a handoff is a dry run. Do not start a process here."""
    target_text = target if isinstance(target, str) else ""
    request_text = request if isinstance(request, str) else ""
    surface = sensitive_surface(target_text, request_text)
    if surface is not None:
        raise UseRefused(f"refusing a sensitive surface: {surface}")
    if "--act" in f"{target_text} {request_text}".split():
        raise UseRefused("refusing to pass --act")
    named = target_text.strip()
    request_named = request_text.strip()
    if named == "":
        raise UseRefused("a named target is required")
    if request_named == "":
        raise UseRefused("a request is required")
    if named.startswith("-") or request_named.startswith("-"):
        raise UseRefused("refusing a target or request that starts with -")
    return UsePlan(mode="armed" if armed else "dry-run", target=named, request=request_named)


def hands_argv(executable: str, plan: UsePlan) -> list[str]:
    """Build the jev-run argv. `--act` is never included."""
    argv = [
        executable,
        "--expect",
        plan.target,
        "--target",
        plan.target,
        "--text",
        plan.request,
    ]
    if any(part == "--act" for part in argv):
        raise UseRefused("refusing to pass --act")
    return argv


def payload(plan: UsePlan, *, started: bool) -> dict:
    return {
        "mode": plan.mode,
        "decision_maker": "caller",
        "hands": "jev",
        "target": plan.target,
        "request": plan.request,
        "started": started,
    }


def perform(target: str | None, request: str | None, armed: bool) -> tuple[int, dict]:
    """Run the shipped handoff. A dry run starts no process."""
    plan = plan_use(target, request, armed)
    if plan.mode != "armed":
        return 0, payload(plan, started=False)
    executable = shutil.which("jev-run")
    if executable is None:
        raise UseRefused("jev-run is not on PATH. Nothing was run.")
    argv = hands_argv(executable, plan)
    try:
        completed = subprocess.run(argv, check=False, capture_output=True)
    except OSError as exc:
        raise UseRefused("jev-run could not be started. Nothing was run.") from exc
    return completed.returncode, payload(plan, started=True)
