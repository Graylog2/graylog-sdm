---
applyTo: "tools/**,tests/**"
---

# Python review rules

- Target Python 3.13 only.
- The code uses pydantic v1. Do not suggest migrating to pydantic v2 or v2-only APIs.
- Code must be clean under ruff (lint and format) and mypy.
- Every behavior change needs a test that covers it. Flag behavior changes without tests.
