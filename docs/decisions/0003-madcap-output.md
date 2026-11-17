# 0003. MadCap HTML output

Status: accepted
Date: 2026-11-17

## Context
The MadCap HTML generated from the SDM feeds a MadCap Flare project in a separate repo. Previously it was built locally and was not tracked, so there was no way to see or review what changed in the output.

## Decision
- MadCap HTML is committed to `generated/MadcapHtmlOutput/`.
- The MadCap output plugin accepts an optional output path. When set, it replaces the default location (it does not add a second copy). Precedence: CLI flag > config key > default.
- CI checks on every PR that the committed output is up to date. CI does not auto-commit; the contributor runs `build-sdm build` and commits the result.
- How output is delivered to Flare is out of scope.

## Consequences
- Output changes show up in PR diffs and can be reviewed.
- Every source change that affects output must include the regenerated files.
