# SDM Migration — PR 5 of 5: Contributor docs, follow-up proposals, plan removal

Status: active
Tracking: (PR link)
Overview: `docs/plans/sdm-migration/README.md`. Depends on PR 4 (`04-ci.md`).

## Context
After PRs 1 to 4, the repo works, but parts of `AGENTS.md` and the README are still placeholders. This PR:
- finishes the contributor docs
- writes proposal docs for three follow-ups that are **not** implemented in this effort: updating the Illuminate skills, repo governance, and AI tooling setup for Claude and Copilot
- completes the migration plan by moving it into `docs/plans/archive/20261109-sdm-migration/`

The proposals are markdown only. No settings, skills or GitHub configuration change.

## Steps
1. Branch `migration/05-docs`.
2. `README.md` (expand the current two lines):
   - purpose: the SDM source of truth; Illuminate keeps its own copy until a later cutover
   - repo layout table
   - quick start: `uv sync`, `uv run build-sdm build`, `uv run build-sdm validate`
   - links to `docs/contributing.md`, `docs/decisions/` and `AGENTS.md`
3. `docs/contributing.md`:
   - **editing data:**
     - infomodel and schema file shapes, with short examples
     - adding a category from `docs/templates/category.toml.template`
     - guidance on the required/recommended/optional tiers (point to `.github/instructions/sdm-data.instructions.md` rather than repeating it)
   - **commands:** `build`, `build --madcap-output-dir PATH`, the config `output_dir` key and its precedence, `validate [--base-ref]`, `check-generated`
   - **MadCap output:**
     - the default goes to `generated/MadcapHtmlOutput/` and is committed
     - the override replaces the default
     - always commit the regenerated default output
   - **lint rules:** a table of rule IDs from PR 3, and the new-versus-existing violation policy (link ADR 0004)
   - **formatting:** `uv run taplo fmt`
   - **CI:** the jobs and how to fix each kind of failure
   - **plans and decisions:** how to write an ADR, and the plan lifecycle (link ADR 0005)
4. Finalize `AGENTS.md`:
   - remove the "(in progress)" layout note
   - replace the command placeholders with real commands
   - link `docs/contributing.md`
   
   Finalize `.github/copilot-instructions.md`:
   - confirm the list of "CI enforces this, don't comment" checks matches PR 4's jobs
   - keep it within the size limit recorded in ADR 0005
5. `docs/proposals/illuminate-skills-update.md`:
   - **`sdm-terminology`**, in the `ai-community` marketplace repo at `illuminate/skills/sdm-terminology/SKILL.md`:
     - re-point `_meta/gim/infomodels/` and `_meta/gim/schema/` to graylog-sdm `src/sdm/...`
     - replace the repo-detection check
     - drop the reference to `scripts/llm/build_sdm_ref.py`, which doesn't exist; propose an alternative such as a `build-sdm` subcommand that emits a reference index
   - **`sdm-build`:**
     - point to `build-sdm validate` as the enforcement for its checklist, and map each checklist item to a rule ID
     - note that its rules are now also inline in `.github/instructions/sdm-data.instructions.md`, so this repo is the source and the skill should defer to it
   - `illuminate/skills/README.md:35-36`
   - open question to note: how skills find graylog-sdm when they run from Illuminate (sibling checkout, env var, or a published artifact)
6. `docs/proposals/repo-governance.md`:
   - branch protection on `main`: required checks `data-lint`, `generated-fresh` and `python-qa`, plus at least one human approval; AI reviews are advisory
   - CODEOWNERS for `src/sdm/`, `tools/`, `.github/`, `AGENTS.md` and the instruction files
   - PR template:
     - a change-type selector (additive, deprecation, breaking)
     - checklist: validate, regenerated, `sdm_version` bump if breaking
     - plan checklist: "If this completes a plan: decisions recorded in an ADR; plan `Status: done` and moved to `docs/plans/archive/<Created YYYYMMDD>-<name>/`"
   - an optional CI check (a small script) that fails if:
     - any `docs/plans/*/README.md` outside `archive/` has `Status: done` or `abandoned`
     - any archive directory name doesn't match `^\d{8}-[a-z0-9-]+$`
     - an archive directory's date prefix doesn't match the `Created:` date in its README
   - issue templates adapted from Illuminate's `.github/ISSUE_TEMPLATE/`
7. `docs/proposals/ai-tooling-setup.md`, covering both tools:
   - **shared:**
     - the file map (`AGENTS.md`, `CLAUDE.md` imports, Copilot instruction files) and which tool reads which file
     - rule: add a new standard to exactly one file, chosen by audience; dev standards go in `AGENTS.md`, review standards in the Copilot files
   - **Claude:**
     - proposed `.claude/settings.json`:
       - allow `uv run build-sdm *`, `uv run pytest*`, `uv run ruff*`, `uv run taplo*`
       - deny `Edit(generated/**)` and `Write(generated/**)`
     - optional `PostToolUse` hook running `build-sdm validate` after edits to `src/sdm/`
     - optional Claude GitHub Action for PR review, which reads `CLAUDE.md` and therefore the same review standards
   - **Copilot:**
     - enable automatic Copilot code review on PRs
     - re-check the instruction-file size limits and whether `AGENTS.md` is supported; if Copilot review gains `AGENTS.md` support, consider simplifying
   - **maintenance:** a CODEOWNERS entry for the instruction files (see the governance proposal)
8. **Archive the plan:**
   1. Confirm every decision in the plan is covered by ADRs 0001–0005. Add or amend ADRs for anything that changed during implementation.
   2. Set `05-docs.md` and `README.md` to `Status: done` and complete the status table.
   3. Run `git mv docs/plans/sdm-migration docs/plans/archive/20261109-sdm-migration`, as its own commit so the move stays readable in history.
   4. Fix any links that pointed into `docs/plans/sdm-migration/`, for example from ADRs or the README.

## Verification
- Follow `docs/contributing.md` step by step in a fresh clone: `uv sync`, build, validate, check-generated. Every command works as written.
- All file paths and rule IDs mentioned in the docs and instruction files exist (grep them).
- `docs/plans/` contains only `README.md` and `archive/`.
- `docs/plans/archive/20261109-sdm-migration/` holds all six files, all with `Status: done`.
- `git log --follow docs/plans/archive/20261109-sdm-migration/README.md` shows history from before the move.
- `grep -rn "docs/plans/sdm-migration/"` returns no stale links.
- A Claude session and a Copilot review on a sample data PR both apply the data rules (for example, both flag a non-ASCII description).
