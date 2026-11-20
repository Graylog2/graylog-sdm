# 0002. build-sdm package

Status: accepted
Date: 2026-11-17

## Context
`build_gim` was a script directory in Illuminate, run from its own folder with its own virtualenv. It had no single entry point, and plugin errors could be logged without failing the build.

## Decision
- The tool becomes a proper Python package, `build_sdm`, with one CLI, `build-sdm`, and subcommands (`build`, `check-generated`, `validate`).
- The rename from `build_gim` to `build_sdm` covers tool names only. GIM remains the domain term for the information model (classes, categories, subcategories, event types).
- pydantic v1 is kept. Migrating to v2 is out of scope.
- Python 3.13 only.
- Plugin failures are fatal: the build exits non-zero if any plugin fails. This covers errors a plugin catches itself (write failures, template errors, invalid per-entity config) and an enabled plugin whose config is invalid.
- A fatal error is logged once, by the CLI, with its cause chain. Lower layers don't log before re-raising; they add context with `add_note()` or `raise ... from`. (Added in PR 3, follow-up F18.)
- A broken script config (`tools/build_sdm/configs/`) fails the command instead of falling back to defaults, and two source files with the same name in different directories are rejected instead of one silently replacing the other. (Added in PR 3.)
- Build output is deterministic: source files load in sorted path order, and recorded paths are repo-relative, so the same commit builds byte-identical output on any machine. (Added in PR 2, which found `message_summaries.json` ordered by filesystem listing order.)

## Consequences
- One command builds everything, locally and in CI.
- Code and docs keep using "GIM" for the model; only package, CLI, and module names change.
- A pydantic v2 migration needs its own decision later.
- Output changes are reviewable: `tests/golden/` holds snapshots of the non-MadCap plugin output built from the live data, and a change that alters output must update them (`pytest --update-golden`) in the same commit.
