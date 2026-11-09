# SystemOne

Fast closed decisions for agents, so the big model only writes.

[![License: MIT](https://img.shields.io/badge/license-MIT-blue)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/downloads/)

A large model should write and plan. SystemOne only answers a closed question: a yes/no probability, one label from a set you supply, or one rung on a ladder you supply. It does not draft prose, code, or plans.

## 30-second start

From this directory:

```bash
python -m venv .venv && .venv/bin/pip install -e .
.venv/bin/systemone serve --mock
```

`python3` is the same command if `python` is not on your `PATH`.

In a second shell, with the venv activated:

```bash
systemone decide --state "customer asked for a refund" \
  --question needs_reply:noul:Does this email need a reply? \
  --question route:choice:Which queue should take this? \
  --criteria billing="Refunds, invoices, and payment issues" \
  --criteria support="How-to questions about the product" \
  --question urgency:score:How urgent is this message? \
  --score-label low \
  --score-label normal \
  --score-label high
```

Mock mode prints JSON like this. `latency_s` varies. The labels do not: noul is always `0.5`, choice is the first key you sent, and a three-rung score is the middle rung.

```json
{
  "answers": {
    "needs_reply": {"p": 0.5},
    "route": {"label": "billing"},
    "urgency": {"value": 1, "label": "normal"}
  },
  "latency_s": 0.0001,
  "model": "mock"
}
```

`model` is `"mock"`. That is the wiring, not a judgment.

## Install

```bash
git clone https://github.com/talalkashar/systemone.git
cd systemone
python -m venv .venv && .venv/bin/pip install -e .
```

From a checkout you already have, the venv command is enough.

| Method | Command | Status |
| --- | --- | --- |
| GitHub | `git clone https://github.com/talalkashar/systemone.git` | https://github.com/talalkashar/systemone |
| Local editable install | `python -m venv .venv && .venv/bin/pip install -e .` | use this |
| PyPI `pip install systemone` | — | not published yet |

<!-- Model extra is intentionally not declared in pyproject.toml.
     Decision weights are not part of this package. If you later choose to
     load a local model yourself, that install is yours:
     pip install transformers torch
     This version never downloads weights. `systemone serve` without `--mock`
     exits 2. A future release may honor SYSTEMONE_MODEL=1. -->

## Tools

| Tool | What it is |
| --- | --- |
| `systemone` | CLI. `serve`, `decide`, `health`, `install`. |
| `systemone-mcp` | stdio MCP server (newline-delimited JSON-RPC 2.0). It calls a SystemOne HTTP server. It does not serve the model itself. |
| `src/systemone/skill/SKILL.md` | Agent skill. Use it for a closed decision, not for prose or code. |

Point the MCP client at a running server with `SYSTEMONE_URL` (default `http://127.0.0.1:18100`):

```bash
systemone serve --mock
systemone-mcp
```

MCP tools are `health` (no arguments) and `decide` (`state` string, `questions` object). The same shape as `POST /decide`.

### Agent config

`systemone install` prints the Claude Code, Cursor, and Codex MCP entries and writes nothing. `systemone install --yes` writes those files under the current home.

```bash
systemone install
systemone install --yes
systemone install --agent cursor --yes
```

It sets `mcpServers.systemone` to a stdio server (`command`: `systemone-mcp`) in `~/.claude.json` and `~/.cursor/mcp.json`, and writes `[mcp_servers.systemone]` in `~/.codex/config.toml`. Other servers in those files stay. It refuses a symlink and any path outside the home. Run it once and read the printout before you pass `--yes`.

## Question types

`POST /decide` takes `{"state": string or null, "questions": {name: question}}`. Up to 32 questions. Each instruction is at most 2000 characters. `state` is at most 100000 characters.

| type | criteria | answer |
| --- | --- | --- |
| `noul` | `null` | `{"p": number}` from 0 to 1. Probability the instruction is true. |
| `choice` | object of label to description, at most 64 labels | `{"label": string}`, one of the keys. The server does not invent a label. |
| `score` | list of labels from low to high, at most 16 | `{"value": index, "label": string}`. |

`GET /health` returns `{"status": "ok", "model": string, "mock": bool}`.

A choice question sends the labels in the order you mean them. A score question sends the ladder from low to high. Both are data you wrote, not a request for new wording.

```bash
curl -s http://127.0.0.1:18100/health
curl -s http://127.0.0.1:18100/decide \
  -H 'content-type: application/json' \
  -d '{"state":"customer asked for a refund","questions":{"needs_reply":{"type":"noul","instructions":"Does this email need a reply?","criteria":null}}}'
```

`systemone decide` flags:

- `--question NAME:TYPE:INSTRUCTIONS` is repeatable. Split on the first two colons, so the instruction may contain colons.
- `--criteria LABEL=TEXT` is repeatable and applies to the most recent choice question.
- `--score-label TEXT` is repeatable and applies, low to high, to the most recent score question.
- `--url` overrides `SYSTEMONE_URL`.

## Weights, licenses, and what this package is not

Decision-model weights are not in this package. `systemone serve` without `--mock` prints a message to stderr and exits 2. It does not download a model.

Liquid AI d1-omni is a separate model under Liquid's license. This package's own code is MIT. Nothing here redistributes that model.

jev / typesafe-computer-use is Aaron Levin's project. SystemOne does not include it. Screen control is a different tool, and only when the user asked to operate a GUI.

## Privacy

The server binds to `127.0.0.1` and port `18100` unless you change the port. It will not bind `0.0.0.0` unless you pass `--allow-remote`. Leave that flag off.

Do not put secrets in `state`. Do not send banking data, mail, messages, passwords, or student records. See `SECURITY.md`.

Mock mode is not a model. The answers are fixed so you can test a client, an MCP tool call, or a skill. Do not treat them as a decision about the text you sent.
