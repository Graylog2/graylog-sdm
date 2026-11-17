# graylog-sdm

Development standards for all agents and humans working in this repo.

## Purpose

This repo is the authoritative source for the Graylog Security Data Model (SDM): field schema, GIM (Graylog Information Model) classes/categories/subcategories/event types, and reserved values. Downstream repos (e.g. graylog-project-illuminate) consume it; they never edit it.

## Layout

Target layout (in progress, see docs/plans/):

```
AGENTS.md                      # canonical dev standards (this file)
CLAUDE.md                      # imports AGENTS.md and .github/copilot-instructions.md
.github/
  copilot-instructions.md      # repo-wide review standards
  instructions/*.instructions.md  # path-scoped review standards
src/sdm/{infomodels,schema,config}/   # SDM source data
generated/MadcapHtmlOutput/    # committed build output; never hand-edit
tools/build_sdm/               # build-sdm package; configs/ incl. MadCap plugin config
tests/
docs/
  decisions/NNNN-*.md          # ADRs (authoritative)
  plans/                       # active plans and archive
  templates/category.toml.template
build/sdm_artifacts/<Plugin>/  # other plugin output, gitignored
```

## Source of truth rules

- Edit SDM definitions only under `src/sdm/`. Never "fix" SDM content in a downstream repo.
- Never hand-edit `generated/`. Regenerate it with `build-sdm build` whenever the source changes, and commit the result with the source change.

## Conventions

- Meta fields (`title`, `description`, etc.) use US-ASCII printable characters only and are written for a technical audience.
- Class, category, subcategory and event type names are lowercase `a-z` words separated by underscores.
- Subcategory and event type names are unique across the whole GIM, except `default`.
- The `default` subcategory is always number `99`.
- See `.github/instructions/sdm-data.instructions.md` for the full field classification rules.

## Change policy

- Classify every change as **additive**, **deprecation**, or **breaking**.
- Breaking changes (rename, removal, type change) require an `sdm_version` bump.
- Never reuse a removed field name or GIM code for a different meaning.

## Commands

- Set up: `uv sync`
- Build: `uv run build-sdm build`. Writes `generated/MadcapHtmlOutput/` (committed) and `build/sdm_artifacts/<Plugin>/` (gitignored).
- Check generated output is fresh: `uv run build-sdm check-generated`. If it reports stale files, run `rm -rf generated/MadcapHtmlOutput && uv run build-sdm build`.
- Tests: `uv run pytest`. If a change alters plugin output on purpose, refresh the snapshots with `uv run pytest tests/test_golden_outputs.py --update-golden` and commit `tests/golden/` with the change.
- Lint and types: `uv run ruff check`, `uv run ruff format --check`, `uv run mypy`
- Validate SDM data: `uv run build-sdm validate --base-ref origin/main` (available after PR 3)
- Format TOML: `uv run taplo fmt` (available after PR 3)

Before claiming work is done, run the commands above that are available and confirm they pass.

## Plans and decisions

- Durable decisions live in `docs/decisions/` (ADRs) and are authoritative.
- Each active plan has its own directory, `docs/plans/<name>/`. A plan is work intent, not fact; when a plan and the code disagree, the code wins.
- `docs/plans/archive/` is history only. Don't use it as current guidance unless asked about history.
- For plan conventions, see `docs/plans/README.md`.
