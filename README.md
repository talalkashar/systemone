# SystemOne

Your agent decides. SystemOne checks that decision before a computer-use program can run.

License: MIT. Python 3.11 or newer. Copyright (c) 2026 Talal Kashar. See [SECURITY.md](SECURITY.md), [CONTRIBUTING.md](CONTRIBUTING.md), and [LICENSE](LICENSE).

Claude, Grok, ChatGPT, or any OpenAI-compatible model is the brain. It picks the window and the action. SystemOne checks that choice, refuses sensitive surfaces, and can hand the already chosen target and request to an installed `jev-run`. jev does not choose the action. This release never passes `--act`, so it does not click, type, or move the pointer.

Mock answers from `systemone serve --mock` are fixed wiring. They are not a model and not a judgment. This package does not download weights.

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
| PyPI | — | not published yet |

## Computer use

`systemone use` prints the handoff and starts no process. `--arm` is the explicit arm. It looks up `jev-run` on `PATH` and starts it as:

```text
jev-run --expect TARGET --target TARGET --text REQUEST
```

That argument list never includes `--act`. Starting `jev-run` this way does not click, type, or move the pointer. A named target and a request are required. The command refuses the handoff before any process starts when the target or the request names any of these surfaces: banking, mail, messages, password managers, Mason or student records, admin consoles, or login or MFA.

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
