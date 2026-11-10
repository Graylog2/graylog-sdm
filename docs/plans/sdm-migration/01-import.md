# SDM Migration — PR 1 of 5: Scaffold, AI standards, ADRs, verbatim import

Status: active
Tracking: (PR link)
Overview: `docs/plans/sdm-migration/README.md`. Depends on: nothing. Next: `02-package.md`.

## Context
graylog-sdm (`~/Work/graylog-sdm`) becomes the source of truth for the Graylog Security Data Model (SDM). Today the SDM and its generator `build_gim` live in graylog-project-illuminate (`~/Work/graylog-project-illuminate`) at `_meta/gim/` and `scripts/build_gim/`. This PR does three things:
- sets up the repo's tool-neutral AI standards
- records the migration decisions as ADRs
- copies the data and tools in **verbatim**, so the import can be traced to its source

All restructuring of the data and tools happens in later PRs.

Constraints:
- Illuminate is not modified.
- Fresh import with no history carried over. The commit message records the Illuminate SHA.
- Source ref is Illuminate `origin/develop`. The local checkout is on `mw/ecs-comparison`, so do **not** copy from the working tree. Export from the ref.
- Standards must serve both Claude (dev + review) and GitHub Copilot (review). Copilot code review reads `.github/copilot-instructions.md` and path-scoped `.github/instructions/*.instructions.md`, and does not reliably follow links to other files, so review rules must be written out inline in those files. `CLAUDE.md` imports files with `@path`.

## Starting state
**Prerequisite:** setup PR #2 is merged. This section describes `main` at the moment PR 1 starts.

Already on `main`:
- From setup PR #1:
  - `.gitignore` additions: `.claude/settings.local.json`, `.claude/.cc-writes/`, `CLAUDE.local.md`
  - `CLAUDE.md`: a starter with TODOs. Its content moves to `AGENTS.md` in commit 1.
- From setup PR #2:
  - this plan (`docs/plans/sdm-migration/`)
  - `docs/plans/archive/.gitkeep`
  - the GitHub CLI permissions in `.claude/settings.json`:
    - read-only `gh` commands are allowed
    - `gh pr comment` and `gh api` ask first
    - `gh pr merge`, `gh pr review` and `gh pr ready` are denied
    - reading `.env` is denied

  Keep `.claude/settings.json` as is in PR 1. Further changes go to the PR 5 proposal.

## Steps
1. Branch `migration/01-import` off `main`.
2. **Commit 1: repo scaffolding and AI standards.**
   - `.gitignore`: keep the Claude entries above, and add `build/` and `.venv/` if missing.
   - `AGENTS.md`, the canonical development standards for all agents and humans. Move the content of the current `CLAUDE.md` here and resolve whatever TODOs can be resolved with what is known now. Sections:
     - **purpose:** the SDM source of truth; downstream repos consume it and never edit it
     - **layout:** the target layout from the overview, marked "(in progress, see docs/plans/)" until PR 5
     - **source of truth rules:**
       - edit SDM only under `src/sdm/`
       - never hand-edit `generated/`; regenerate it with `build-sdm build`
     - **change policy:**
       - classify every change as additive, deprecation or breaking
       - never reuse a removed field name or GIM code
       - a breaking change requires an `sdm_version` bump
     - **commands:** placeholders marked "available after PR 2/3"
     - **plans and decisions:**
       - durable decisions live in `docs/decisions/` (ADRs) and are authoritative
       - each active plan has its own directory, `docs/plans/<name>/`; it is work intent, not fact, and when a plan and the code disagree, the code wins
       - `docs/plans/archive/` is history only; don't use it as current guidance unless asked about history
       - for conventions, see `docs/plans/README.md`
   - `CLAUDE.md`, replaced with exactly:
     ```
     @AGENTS.md
     @.github/copilot-instructions.md
     ```
   - `.github/copilot-instructions.md`: repo-wide **review** standards, short and with everything written inline:
     - the source-of-truth rule
     - generated output must not be hand-edited, and must be regenerated whenever the source changes
     - change classification and breaking-change scrutiny
     - US-ASCII-only descriptions written for a technical audience
     - don't comment on what CI enforces (formatting, naming, freshness; this list is finalized in PR 3); focus on judgment: whether a required/recommended/optional classification is justified, description quality, and whether a change is really additive
     - plans in `docs/plans/` are intent; review the code against the PR, not against the plan
   - `.github/instructions/sdm-data.instructions.md`:
     - frontmatter `applyTo: "src/sdm/**"`
     - the `sdm-build` skill rules written inline: naming, uniqueness, default subcategory 99, the meaning of each classification tier, required kept conservative, no broad wildcards, default required fields form the baseline
     - source: `~/.claude/plugins/marketplaces/graylog-dev/illuminate/skills/sdm-build/SKILL.md`
   - `.github/instructions/python.instructions.md`:
     - frontmatter `applyTo: "tools/**,tests/**"`
     - Python 3.13, pydantic v1 (do not suggest v2 migrations), ruff/mypy clean, a test for every behavior change
3. **Commit 2: ADRs and plans.**
   - Create `docs/decisions/` with a lightweight ADR template (`Status`, `Context`, `Decision`, `Consequences`) and these ADRs, all `Status: accepted`:
     - `0001-repo-layout.md`:
       - data in `src/sdm/`, tools in `tools/build_sdm/`, tests in `tests/`, committed output in `generated/`, other plugin output in gitignored `build/sdm_artifacts/`
       - presentation config (MadCap plugin config) is kept separate from SDM data
     - `0002-build-sdm-package.md`:
       - a proper package with one CLI and subcommands
       - the rename covers tool names only; GIM stays as the domain term
       - pydantic v1 kept; Python 3.13 only
       - plugin failures are fatal
     - `0003-madcap-output.md`:
       - MadCap HTML is committed to `generated/MadcapHtmlOutput/`
       - the optional output path replaces the default, with precedence CLI > config
       - CI checks freshness and doesn't auto-commit
       - delivery to Flare is out of scope
     - `0004-sdm-lint-policy.md`:
       - structural validation, the codified rule set, taplo formatting
       - a violation fails only when it is new relative to the base ref (`rule_id` + `entry_key`); existing violations warn
     - `0005-ai-standards-and-plan-lifecycle.md`:
       - `AGENTS.md` is canonical for development
       - Copilot instruction files hold review standards inline
       - `CLAUDE.md` only imports
       - each plan gets its own directory under `docs/plans/`, with a `README.md` header (`Status`, `Created`, `Tracking`)
       - when a plan is done or abandoned, `git mv` it to `docs/plans/archive/YYYYMMDD-<name>/`, using the plan's creation date
       - lasting decisions go into ADRs before the plan is archived
       - the archive is history only and has no authority
   - Add `docs/plans/README.md`: the plan conventions from the overview (header fields, step files, how and when to archive, date = Created, the authority rules), plus a template header block.
   - Add `docs/plans/archive/.gitkeep`.
   - `docs/plans/sdm-migration/` and `docs/plans/archive/.gitkeep` were already added in the setup PR (#2) before this PR. Commit 2 only adds `docs/plans/README.md`.
4. In Illuminate, run `git fetch origin develop`, then `SHA=$(git rev-parse origin/develop)`.
5. Export from that ref: `git archive "$SHA" _meta/gim scripts/build_gim | tar -x -C "$TMPDIR/sdm-import"`.
6. **Commit 3: verbatim import**, from the export:
   - `_meta/gim/infomodels/*.toml` → `src/sdm/infomodels/`
   - `_meta/gim/schema/*.toml` → `src/sdm/schema/`
   - `_meta/gim/{gim,field_schema,sdm_version}.config.toml` → `src/sdm/config/`
   - `_meta/gim/plugin.config.madcap.toml` → `src/sdm/config/`, temporarily, so this commit stays verbatim
   - `_meta/gim/infomodels/category.toml.template` → `docs/templates/category.toml.template`
   - `scripts/build_gim/` → `tools/build_sdm/`, excluding `.venv/`, `build/`, `__pycache__/` and `.pytest_cache/`
   - **Not imported:** `_meta/gim/html_templates/` (stale) and `scripts/legacy/build_gim.py` (unreferenced)
   - Commit message: `Import SDM data and build_gim from graylog-project-illuminate@<SHA>`
7. **Commit 4:** `git mv src/sdm/config/plugin.config.madcap.toml tools/build_sdm/configs/`. Per-entity `meta.plugin_config.MadcapHtmlOutput` blocks stay in the data TOMLs.
8. **Commit 5: plan status.** Set `docs/plans/sdm-migration/01-import.md` to `Status: done` and mark PR 1 done in the status table in `README.md`.

The tool won't run yet; PR 2 fixes its paths. Note this in the PR description.

## Verification
- Counts: 21 files in `src/sdm/infomodels/`, 30 in `src/sdm/schema/`, 3 in `src/sdm/config/`.
- `diff -r` against the `$TMPDIR` export shows no differences beyond the intentional exclusions and moves.
- `CLAUDE.md` contains only the two import lines. A new Claude session in the repo shows that both imported files are loaded (`/memory`).
- Every instruction file has valid frontmatter (`applyTo` set). Open a draft PR touching a file in `src/sdm/` and request a Copilot review, to confirm the path-specific instructions are picked up.
- Check the current GitHub docs for:
  - Copilot code review's instruction-file size limits; keep files under them
  - whether Copilot review now reads `AGENTS.md`
  
  Record what you find in ADR 0005.
