# Contributing

This package is MIT. Copyright (c) 2026 Talal Kashar. See `LICENSE`.

The caller decides a computer-use action. `systemone use` checks that choice, stays a dry run unless `--arm`, and never passes `--act`. jev is the hands layer. Do not make Jev the decision maker.

- Run tests from this directory:

  ```bash
  python3 -m unittest discover -s tests -v
  python3 -m compileall -q src tests
  ```

  Tests import `tests/srcpath.py`, which puts `src/` on `sys.path`. `PYTHONPATH=src` is optional.

- A test for `systemone use` must start `python -m systemone.cli`. An armed test may put a throwaway `jev-run` on `PATH` that only records its argv. Do not point that test at a real click.
- Keep the default install free of third-party dependencies. Do not add PyTorch, Transformers, or model weights to `pyproject.toml`.
- Do not commit secrets, `.env` files, private keys, tokens, student records, or mail.
- Do not vendor other projects. Aaron Levin's typesafe-computer-use stays in its own repo. Decision-model weights stay under their own license.
- New behavior needs a test. Bug fixes should fail before the fix and pass after it.
