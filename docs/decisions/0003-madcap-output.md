# 0003. MadCap HTML output

Status: accepted
Date: 2026-11-17

## Context
The MadCap HTML generated from the SDM feeds a MadCap Flare project in a separate repo. Previously it was built locally and was not tracked, so there was no way to see or review what changed in the output.

## Decision
- MadCap HTML is committed to `generated/MadcapHtmlOutput/`.
- The MadCap output plugin accepts an optional output path. When set, it replaces the default location (it does not add a second copy). Precedence: CLI flag (`build --madcap-output-dir`, relative to the current directory) > config key (`output_dir` in `configs/madcap_html_output.toml`, relative to the repo root) > default (`build/sdm_artifacts/MadcapHtmlOutput/`).
- `--madcap-output-dir` writes only into a directory that is new, empty, or holds a `.build-sdm-output` marker. The build writes the marker into a new or empty directory; a non-empty directory without it is refused unless `--force` is given, and a forced build adds no marker. The build never deletes files. This protects hand-written content when the flag points into a Flare project (follow-up F4, 2026-11-24). The configured location isn't checked: it is in the repo, under version control.
- CI checks on every PR that the committed output is up to date (`build-sdm check-generated`). The check compares both ways: changed, stale (no longer built) and missing files all fail, because the build never deletes files. CI does not auto-commit; the contributor runs `build-sdm build` and commits the result.
- How output is delivered to Flare is out of scope.

## Consequences
- Output changes show up in PR diffs and can be reviewed.
- Every source change that affects output must include the regenerated files.
