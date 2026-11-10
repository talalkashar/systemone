# SystemOne

Your agent decides. SystemOne checks that decision before a computer-use program can run.

License: MIT. Python 3.11 or newer. Copyright (c) 2026 Talal Kashar. See [SECURITY.md](SECURITY.md), [CONTRIBUTING.md](CONTRIBUTING.md), and [LICENSE](LICENSE).

Any agent can be the brain. Claude, Grok, ChatGPT, Gemini, DeepSeek, Qwen, GLM, Kimi, Llama, Mistral, a model you run yourself, or any other program that can run a command. There is no model SDK in this package and no OpenAI requirement. The agent picks the window and the action. SystemOne checks that choice, refuses sensitive surfaces, and can hand the already chosen target and request to an installed `jev-run`. jev does not choose the action. This release never passes `--act`, so it does not click, type, or move the pointer.

Mock answers from `systemone serve --mock` are fixed wiring. They are not a model and not a judgment. This package does not download weights and it does not call TypeSafe.

## What jev is

People use the name for two different things.

Jev, the model, is [TypeSafe](https://docs.typesafe.ai/models)'s System One model (`jev-1.14.0` and `jev-1.13.0` on their models page). It is not a chatbot. You send a state and closed questions. It returns a typed answer and probabilities for each question. It does not write a plan, an email, or code. The question types on that page are Choice, Score, and Noul. Jev 1.14 adds Box.

jev, the program, is Aaron Levin's [typesafe-computer-use](https://github.com/awlevin/typesafe-computer-use). It reads a Mac screen, asks that model which action, item, and site come next, and can click. The classifier is the decision maker there. The writing model only supplies free text.

SystemOne is neither of those. It does not include Aaron Levin's source, and it does not sell access to the Jev model.

## What it costs

This package is MIT and has no runtime dependencies. Installing it creates no TypeSafe bill.

TypeSafe's [models page](https://docs.typesafe.ai/models) lists Jev 1.14 and Jev 1.13 at **$0.042 per million input tokens**. Output tokens are free. That is their list price. A gateway or a prepaid pack can differ. Check the page for the current number.

Aaron Levin's README publishes the computer-use figure: about **$0.0002 a step**. On one screenshot he measured, a jev decision was $0.0002 and 0.13 to 0.38 seconds, against $0.032 and 5.2 seconds for the frontier model on that same screenshot. A 12-step task in that table is about $0.003 on the jev side. Those are his measurements, from [awlevin/typesafe-computer-use](https://github.com/awlevin/typesafe-computer-use). This repository does not re-run them.

## Why that is effective

A step on a screen is usually one choice from a short list of controls. Jev answers that kind of question in one pass and returns probabilities your code can gate on. It does not spend an output-token budget writing a paragraph about the click.

That is the wrong place to decide the goal. Aaron's own write-up says the frontier model read event dates off the pixels, and the classifier needed those facts computed and handed over as state. The large model is the right tool for the goal, the permission, and anything that has to be read and reasoned about. Jev is the right tool for the next control after that decision already exists.

## Why this instead of jev alone

jev alone lets the classifier pick the next action and, when you pass its own `--act`, drive the mouse. Use that when you want the small model to run the desktop.

Use SystemOne when the agent you already trust should keep the decision:

- The caller can be any agent. If it can run `systemone use --target WINDOW --request ACTION`, it can use this. DeepSeek, Qwen, GLM, Kimi, and a model on your own machine are the same shape of caller as Claude or ChatGPT.
- The check is in code. Banking, mail, messages, password managers, Mason or student records, admin consoles, and login or MFA are refused before a process starts.
- `--arm` starts `jev-run` with the target and request the agent already chose. The argument list never includes `--act`. The classifier does not get to swap in a different action.
- MCP is stdio JSON-RPC. Any MCP client can run `systemone-mcp`. The installer prints Claude Code, Cursor, and Codex config because those are the three files it knows. Every other agent adds that same command itself.

This release checks and records the handoff. jev alone is the program that clicks. SystemOne does not click.

## This release

| Piece | What is true |
| --- | --- |
| Source | Public and MIT at [github.com/talalkashar/systemone](https://github.com/talalkashar/systemone) |
| Install | Clone the repo. `pip install systemone` is not a working install yet. |
| Computer use | Dry run unless you pass `--arm`. `--arm` starts `jev-run` and still omits `--act`. |
| Closed questions | `systemone serve --mock` returns fixed answers for questions you already shaped. |
| Writes | `systemone install` prints Claude Code, Cursor, and Codex config and writes nothing unless `--yes`. |

## Install

```bash
git clone https://github.com/talalkashar/systemone.git
cd systemone
python3 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/systemone use --target Notes --request "count the windows"
```

On Windows the command is `.venv\Scripts\systemone`. From a checkout you already have, the venv commands are enough.

| Method | Command | Status |
| --- | --- | --- |
| GitHub | `git clone https://github.com/talalkashar/systemone.git` | use this |
| Editable install | `python3 -m venv .venv && .venv/bin/pip install -e .` | use this |
| PyPI | no | not published yet |

## Computer use

`systemone use` prints the handoff and starts no process. `--arm` is the explicit arm. It looks up `jev-run` on `PATH` and starts it as:

```text
jev-run --expect TARGET --target TARGET --text REQUEST
```

That argument list never includes `--act`. Starting `jev-run` this way does not click, type, or move the pointer. A named target and a request are required. The command refuses the handoff before any process starts when the target or the request names any of these surfaces: banking, mail, messages, password managers, Mason or student records, admin consoles, or login or MFA. Each name covers the common apps and sites for it, for example PayPal, Venmo and Coinbase, Signal and WhatsApp, the macOS Passwords app, GMU's student systems, Google and cloud admin consoles, and verification or Duo codes.

```bash
systemone use --target Notes --request "count the windows"
```

```json
{
  "mode": "dry-run",
  "decision_maker": "caller",
  "hands": "jev",
  "target": "Notes",
  "request": "count the windows",
  "started": false
}
```

`decision_maker` is `caller`. This command does not call the mock engine, and it does not ask jev what to do. If `jev-run` is missing, `--arm` exits 2 and starts nothing.

## How this differs from other Jev projects

These public projects use Jev as the decision maker:

| Repository | What their own docs say |
| --- | --- |
| [awlevin/typesafe-computer-use](https://github.com/awlevin/typesafe-computer-use) | The TypeSafe classifier picks the next action, item, and site. The writer only supplies free text. |
| [jkudish/jev-mcp](https://github.com/jkudish/jev-mcp) | MCP tools return typed judgments from TypeSafe's Jev model. |
| [kofanlabs/typesafe-computer-use-windows](https://github.com/kofanlabs/typesafe-computer-use-windows) | Jev chooses the next operation and target on Windows. |
| [paulsmith/computer-use-jev](https://github.com/paulsmith/computer-use-jev) | Jev is the decision maker for each next macOS action. |

SystemOne does not. Your agent makes the decision. This package checks it and can hand the already chosen target and request to an installed `jev-run`. It does not vendor Aaron Levin's typesafe-computer-use source.

## Tools

| Tool | What it is |
| --- | --- |
| `systemone` | CLI. `use`, `serve`, `decide`, `health`, `install`. |
| `systemone-mcp` | stdio MCP server (newline-delimited JSON-RPC 2.0) for `health` and `decide`. It calls a SystemOne HTTP server. It does not choose a computer-use action. |
| `src/systemone/skill/SKILL.md` | Agent skill. The agent decides. `systemone use` is the handoff. |

`systemone-mcp` reads `SYSTEMONE_URL` (default `http://127.0.0.1:18100`).

### Agent config

`systemone install` prints the Claude Code, Cursor, and Codex config and writes nothing. `systemone install --yes` writes those files under the current home.

```bash
systemone install
systemone install --yes
systemone install --agent cursor --yes
```

It sets `mcpServers.systemone` to a stdio server (`command`: `systemone-mcp`) in `~/.claude.json` and `~/.cursor/mcp.json`, and writes `[mcp_servers.systemone]` in `~/.codex/config.toml`. Other servers in those files stay. It refuses a symlink, including a pre-existing `*.systemone-tmp` symlink, and any path outside the home. Read the printout before you pass `--yes`. An agent this installer does not know about uses the same `systemone-mcp` command. The protocol is not tied to one vendor.

## Closed questions

`POST /decide` takes `{"state": string or null, "questions": {name: question}}`. Up to 32 questions. Each instruction is at most 2000 characters. `state` is at most 100000 characters. The running server in this release is the mock.

| type | criteria | answer |
| --- | --- | --- |
| `noul` | `null` | `{"p": number}` from 0 to 1 |
| `choice` | object of label to description, at most 64 labels | `{"label": string}`, one of the keys you sent |
| `score` | list of labels from low to high, at most 16 | `{"value": index, "label": string}` |

`GET /health` returns `{"status": "ok", "model": string, "mock": bool}`.

```bash
systemone serve --mock
```

```bash
systemone decide --state "the build failed on main" \
  --question rerun:noul:Should this build be rerun? \
  --question route:choice:Which queue should take this? \
  --criteria ci="Build, test, and deploy failures" \
  --criteria product="User-facing defects" \
  --question urgency:score:How urgent is this failure? \
  --score-label low \
  --score-label normal \
  --score-label high
```

Mock mode returns fixed answers: noul `p` is `0.5`, choice is the first label in insertion order, and score is the middle rung (the lower middle when the ladder length is even). `model` is `"mock"`. `latency_s` is the local function duration. Those values are wiring, not a judgment about the text you sent.

```json
{
  "answers": {
    "rerun": {"p": 0.5},
    "route": {"label": "ci"},
    "urgency": {"value": 1, "label": "normal"}
  },
  "latency_s": 0.0,
  "model": "mock"
}
```

`systemone decide` flags:

- `--question NAME:TYPE:INSTRUCTIONS` is repeatable. Split on the first two colons, so the instruction may contain colons.
- `--criteria LABEL=TEXT` is repeatable and applies to the most recent choice question.
- `--score-label TEXT` is repeatable and applies, low to high, to the most recent score question.
- `--url` overrides `SYSTEMONE_URL`.

## Weights and license

This package's code is MIT. Decision-model weights are not in it. `systemone serve` without `--mock` prints a message to stderr and exits 2. It does not download a model, including when `SYSTEMONE_MODEL=1` is set. Liquid AI d1-omni stays under Liquid's license. Nothing here redistributes that model.

## Privacy

The server binds to `127.0.0.1` and port `18100` unless you change the port. It will not bind `0.0.0.0` unless you pass `--allow-remote`. Leave that flag off.

Do not put secrets in `state`. Do not send banking data, mail, messages, passwords, or student records to `/decide` or to `systemone use`. See `SECURITY.md`.
