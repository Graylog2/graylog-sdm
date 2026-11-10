# SDM Migration to graylog-sdm — Overview

Status: active
Created: 2026-11-09
Tracking: (issue link)

This plan lives in `docs/plans/sdm-migration/`:

- `README.md`: this overview, with the status table
- `01-import.md`: PR 1
- `02-package.md`: PR 2
- `03-lint.md`: PR 3
- `04-ci.md`: PR 4
- `05-docs.md`: PR 5

## Context
The Security Data Model (field schema, GIM infomodels, reserved values) and its generator `build_gim` live in `graylog-project-illuminate` today (`_meta/gim/`, `scripts/build_gim/`). Nothing validates the data automatically. Several authoring rules exist only as prose in the `sdm-build` skill. graylog-sdm becomes the source of truth. Its output feeds a MadCap Flare project that lives in a separate repo. The repo is worked on with Claude (development and review) and GitHub Copilot (review), so its standards must work for both.

## Objectives
1. Move SDM source data to `src/sdm/`. Repackage the generator as a proper Python package `build_sdm` (renamed from build_gim) at `tools/build_sdm/`.
2. Add an optional output path to the MadCap output plugin. When set, it **replaces** the default location. It can come from a CLI flag or a config key; the flag wins.
3. Commit the MadCap HTML to `generated/`. CI checks on every PR that it is up to date.
4. Lint SDM source data on PRs: structural validation, codified rules, and TOML formatting. Also run Python QA on the tools.
5. Standards that work for any AI tool:
   - `AGENTS.md` holds development standards.
   - `.github/copilot-instructions.md` and `.github/instructions/*.instructions.md` hold review standards.
   - `CLAUDE.md` only imports both.
6. Durable decisions go into ADRs in `docs/decisions/`. Each plan lives in its own directory under `docs/plans/`. When a plan is complete, its directory moves to `docs/plans/archive/YYYYMMDD-<name>/`, where the date is the plan's **creation** date.
7. Contributor docs, plus proposal docs for follow-ups: skills update, repo governance, AI tooling setup.

## Out of scope
- Any changes to Illuminate. Cutover is a later effort.
- How output gets delivered to Flare.
- Pydantic v2.
- Changes to output content or format beyond the optional path.
- Carrying over git history.
- Actually changing skills, governance settings, or Claude/Copilot settings. These get proposal docs only. The one exception is the GitHub CLI permissions in `.claude/settings.json`, which setup PR #2 adds before this plan starts.

## Target layout
```
graylog-sdm/
  AGENTS.md                      # canonical dev standards (all agents)
  CLAUDE.md                      # @AGENTS.md + @.github/copilot-instructions.md
  .github/
    copilot-instructions.md      # repo-wide review standards (inline, concise)
    instructions/
      sdm-data.instructions.md   # applyTo: src/sdm/**
      python.instructions.md     # applyTo: tools/**,tests/**
    workflows/ci.yml
  src/sdm/{infomodels,schema,config}/
  generated/MadcapHtmlOutput/    # committed
  tools/build_sdm/               # package; configs/ incl. MadCap plugin config
  tests/
  docs/
    decisions/NNNN-*.md          # ADRs (authoritative, current)
    plans/
      README.md                  # plan conventions
      <plan-name>/               # active plans, one directory each
        README.md                # overview + Status/Created/Tracking + status table
        NN-<step>.md             # optional per-step plans
      archive/
        YYYYMMDD-<plan-name>/    # completed plans; date = Created
    templates/category.toml.template
    contributing.md
    proposals/{illuminate-skills-update,repo-governance,ai-tooling-setup}.md
  pyproject.toml, uv.lock, .python-version (3.13), taplo.toml
build/sdm_artifacts/<Plugin>/    # gitignored
```

## Plan conventions (applied to this migration)
- **Header.** A plan's `README.md` starts with `Status: active | done | abandoned`, `Created: YYYY-MM-DD`, and `Tracking: <issue/PR>`. Step files carry only `Status`.
- **While active.** Each PR that completes a step marks that step file `Status: done` and updates the status table below. Nothing is deleted.
- **Completion.** The final PR:
  1. Records any lasting decisions in ADRs.
  2. Sets `README.md` to `Status: done`.
  3. Runs `git mv docs/plans/<name> docs/plans/archive/<Created as YYYYMMDD>-<name>`.
- **Abandoned plans** are archived the same way, with `Status: abandoned` and a one-line reason.
- **Authority.**
  - ADRs are current decisions.
  - Active plans are intent; the code wins when they disagree.
  - `docs/plans/archive/` is history only. Agents must not treat it as current guidance unless asked about history.
- **This plan** archives to `docs/plans/archive/20261109-sdm-migration/` in PR 5.

| PR | Step file | Status |
|---|---|---|
| 1 | `01-import.md`: scaffold, AI standards, ADRs, plan conventions, verbatim import | active |
| 2 | `02-package.md`: package, rename, paths, optional MadCap path | active |
| 3 | `03-lint.md`: `build-sdm validate` + TOML formatting | active |
| 4 | `04-ci.md`: CI workflow | active |
| 5 | `05-docs.md`: docs + proposals; archive this plan | active |

## Verification (end to end)
After PR 5:
- In a fresh clone, `uv sync && uv run build-sdm build && uv run build-sdm validate --base-ref HEAD && uv run build-sdm check-generated && uv run pytest` passes.
- `uv run build-sdm validate` without `--base-ref` lists the known existing violations and exits 1. That's expected: without a base ref, every violation is reported as an error (see `03-lint.md`).
- CI is green on `main`.
- `docs/plans/sdm-migration/` no longer exists.
- `docs/plans/archive/20261109-sdm-migration/` contains the six files, all `Status: done`.
- ADRs 0001–0005 exist.
- `CLAUDE.md` contains only the imports.
