# SystemOne

Guarded computer-use handoff and closed-question wiring. The caller decides.

License: MIT. Python 3.11 or newer. Copyright (c) 2026 Talal Kashar.

The agent you choose (Claude, Grok, ChatGPT, or any OpenAI-compatible model) is the brain. It picks the target and the action. SystemOne checks that choice. jev is only the computer-use layer. Mock answers from `systemone serve --mock` are fixed wiring, not a model and not a judgment.

## Install

```bash
git clone https://github.com/talalkashar/systemone.git
cd systemone
python -m venv .venv && .venv/bin/pip install -e .
```

`python3` is the same command if `python` is not on your `PATH`. From a checkout you already have, the venv command is enough.

| Method | Command | Status |
| --- | --- | --- |
| GitHub | `git clone https://github.com/talalkashar/systemone.git` | https://github.com/talalkashar/systemone |
| Local editable install | `python -m venv .venv && .venv/bin/pip install -e .` | use this |
| PyPI | — | not published yet |

`pip install systemone` is not a working install for this release.

## Computer use

`systemone use` prints the handoff and starts no process. `--arm` is the explicit arm. It looks up `jev-run` on `PATH` and starts it as:

```text
jev-run --expect TARGET --target TARGET --text REQUEST
```

That argument list never includes `--act`. A named target and a request are required. The command refuses the handoff before any process starts when the target or the request names any of these surfaces: banking, mail, messages, password managers, Mason or student records, admin consoles, or login or MFA.

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

`decision_maker` is `caller`. It is not `jev`, and this command does not call the mock engine. If `jev-run` is missing, `--arm` exits 2 and starts nothing.

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

It sets `mcpServers.systemone` to a stdio server (`command`: `systemone-mcp`) in `~/.claude.json` and `~/.cursor/mcp.json`, and writes `[mcp_servers.systemone]` in `~/.codex/config.toml`. Other servers in those files stay. It refuses a symlink, including a pre-existing `*.systemone-tmp` symlink, and any path outside the home. Read the printout before you pass `--yes`.

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
