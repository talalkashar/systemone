# Contributing

This package is MIT. Copyright (c) 2026 Talal Kashar. See `LICENSE`.

- Run tests from this directory with `PYTHONPATH=src`:

  ```bash
  python3 -m unittest discover -s tests -v
  python3 -m compileall -q src tests
  ```

- Keep the default install free of third-party dependencies. Do not add PyTorch, Transformers, or model weights to `pyproject.toml`.
- Do not commit secrets, `.env` files, student records, mail, or anything that belonged in a `state` field.
- Do not vendor other projects. Decision-model weights stay under their own license. Computer-use tools stay in their own repos.
- New behavior needs a test. Bug fixes should fail before the fix and pass after it.
