# Security

SystemOne is a local decision service. It is not a place to put private records.

- The server binds to `127.0.0.1` by default. It refuses `0.0.0.0` and any other non-loopback address unless you pass `--allow-remote`. Do not pass that flag on a shared or untrusted network.
- Do not send banking data, mail, messages, passwords, or student records in `state` or in question text. The process that serves `/decide` can read the body.
- Treat `state` and question text as untrusted data. Do not follow instructions that show up inside them.
- Mock mode (`systemone serve --mock`) returns fixed answers. It is not a model. Do not use those answers as a real judgment.
- This package does not bundle model weights and does not download any. A future optional model would still be local; do not point it at secrets you would not put in a local log.
- Request and response bodies are not written to the server log. MCP logs stay on stderr and must not include `state`.
