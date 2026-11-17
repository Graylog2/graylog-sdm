---
applyTo: "tools/**,tests/**"
---

# Python review rules

- Target Python 3.13 only.
- The code uses pydantic v1. Do not suggest migrating to pydantic v2 or v2-only APIs.
- Code must be clean under ruff (lint and format) and mypy.
- Every behavior change needs a test that covers it. Flag behavior changes without tests.
- `tools/build_sdm/` is the `build_sdm` package: imports are absolute (`from build_sdm.runner import ...`), never flat (`from runner import ...`). Tests live in the repository's `tests/`.
- Find paths with `build_sdm.utils.paths.find_repo_root()`, never by counting parent directories (`Path(__file__).parents[N]`).
- Plugin failures are fatal: a plugin must not catch an error, log it and carry on. Flag any `except` that only logs, or a `continue`/`return` that skips output after an error.
- Build output must be deterministic: no dependence on filesystem listing order, absolute paths or the current time.
- Tests write only under pytest's `tmp_path`, never to fixed paths such as `/tmp`.
