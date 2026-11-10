# SDM Migration — PR 2 of 5: Package, rename, path decoupling, optional MadCap output path

Status: active
Tracking: (PR link)

Overview: `docs/plans/sdm-migration/README.md`. Depends on PR 1 (`01-import.md`). Next: `03-lint.md`.

## Context
PR 1 imported `build_gim` verbatim into `tools/build_sdm/`. It is still a standalone uv project:
- flat imports (`from base_output import …`, `import output_plugins`)
- pydantic v1
- Python 3.13
- about 50 test files and 174 tests
- it imports nothing from outside its own folder

It is tied to the Illuminate layout in these places:
- `main.py:49`: repo root is `Path(__file__).resolve().parents[2]`
- `configs/build_gim.toml`: `gim_source_dir = "_meta/gim"` and `output_dir = "build/gim_artifacts"` (code default at `runner.py:49,86`)
- `tests/test_sdm_version_registry_loading.py:45` and `tests/test_runner_load_and_transform_gim_config.py:114`: both use `parents[3]/_meta/gim`
- data-side plugin config keyed by module path: `plugin_name = "output_plugins.madcap_html_output.plugin.MadcapHtmlOutput"` (`config_loader.py:108-114`)
- `runner.py:124`: each plugin writes to `<output_dir>/<PluginClassName>/`
- `plugin_loader.safe_execute` (`:14-31`): logs plugin exceptions and skips the plugin, so failures are swallowed
- `field_schema_model.py:7-12`: hard-coded allowed field types. The config list `field_schema.config.toml allowed_field_types` is ignored and is missing `long`, `boolean` and `byte`, all of which the data uses.

## Decisions (from interview)
- Proper Python package at `tools/build_sdm/`, import name `build_sdm`, root `pyproject.toml`, Python 3.13 only.
- Rename build_gim → build_sdm in **tool names only**. GIM stays as the domain term (`type = "gim"`, `gim.config.toml`, `GIMCategory`).
- Pydantic stays on v1.
- Output content and format do not change, apart from the optional MadCap path.
- Only the MadCap output is committed, under `generated/MadcapHtmlOutput/`. The other plugins write to the gitignored `build/sdm_artifacts/<Plugin>/`.
- Optional MadCap output path:
  - It **replaces** the default location; it does not write a second copy.
  - It can be supplied by a CLI flag and by a config key; the CLI flag wins.
- Plugin failures exit non-zero.
- Tests live in `tests/` at the repo root.
- One CLI with subcommands.

## Commit order (review commit by commit)
This PR combines a pure refactor with behavior changes. To keep the parity check meaningful, structure the commits like this:

1. **Refactor, no behavior change:** steps 2–7, 11a and 12 (packaging, imports, rename, repo-root discovery, config loading, a CLI with only the `build` subcommand, moving tests). Step 11a has to be in this commit because the `build-sdm` console script from step 2 points at `build_sdm.cli:main`. Without it, `uv run build-sdm build` can't run the parity check.
   - The parity check runs **at this commit**. Every plugin's output must be byte-identical to Illuminate's at the PR 1 SHA (see Verification).
   - Record the result in the PR description, because a squash merge loses this intermediate state on `main`.
2. **Fatal plugin failures:** step 9. If parity at commit 1 revealed a plugin that was failing silently, this commit surfaces it.
3. **Optional MadCap output path:** step 8, including the `--madcap-output-dir` flag on `build`. It's additive, and the default output is unchanged.
4. **CLI additions:** step 11b.
5. **`allowed_field_types` fix:** step 10. This is the only commit expected to change output. List any output differences in the PR description.
6. **Generated output and determinism:** steps 13–14. Commit `generated/MadcapHtmlOutput/` from the final state.
7. **Standards and plan status:** steps 15–16.

## Steps
1. Branch `migration/02-package`.
2. Root `pyproject.toml`:
   - `name = "build-sdm"`, `requires-python = ">=3.13"`
   - dependencies copied from `tools/build_sdm/pyproject.toml`: `pydantic>=1.10,<2.0`, `jinja2>=3.1`, `markdown>=3.4`, `tomlkit>=0.12`
   - dev dependency group: pytest, pytest-mock, ruff, mypy
   - build backend (hatchling) with package dir `tools/build_sdm` mapped to `build_sdm`, and package data for `html_templates/**` and `configs/*.toml`
   - `[project.scripts] build-sdm = "build_sdm.cli:main"`
   - move `[tool.ruff]`, `[tool.mypy]` (pydantic plugin) and the legacy per-module exemptions over from the tool's pyproject, updating module paths to `build_sdm.*`
   - `[tool.pytest.ini_options] testpaths = ["tests"]`
   - delete `tools/build_sdm/{pyproject.toml,uv.lock,.python-version}`; add root `.python-version` (3.13); generate the root `uv.lock`
3. Turn `tools/build_sdm/` into a package:
   - add `__init__.py` where missing
   - rewrite all flat imports to `build_sdm.…`
   - update `runner._scan_and_import_plugins` (`runner.py:33-35`) to walk `build_sdm.output_plugins`
   - registry keys become `build_sdm.output_plugins.…` automatically (`base_output.py:75-80`)
4. Update the module-path references in data and config:
   - `tools/build_sdm/configs/plugin.config.madcap.toml` → `plugin_name = "build_sdm.output_plugins.madcap_html_output.plugin.MadcapHtmlOutput"`
   - the commented example in `docs/templates/category.toml.template`, which also fixes its old inconsistent key
5. Rename (tool names only):
   - `configs/build_gim.toml` → `configs/build_sdm.toml`
   - key `gim_source_dir` → `sdm_source_dir` = `"src/sdm"`
   - `output_dir = "build/sdm_artifacts"`, with the code defaults at `runner.py:49,86` updated to match
   - README, docstrings, log strings and the argparse prog name
   - `grep -rn "build_gim\|gim_artifacts\|_meta/gim" tools/ tests/ src/ pyproject.toml` until it returns nothing. Docs (`docs/`, ADRs, plans) are left out of this search on purpose, because they mention the old names as history.
6. Find the repo root without counting parent directories:
   - add `build_sdm.utils.paths.find_repo_root()`, which walks up from the current working directory and then from `__file__` until it finds a `pyproject.toml` with `name = "build-sdm"`
   - use it in place of `main.py:49` and in both tests (or add a `repo_root` fixture in `tests/conftest.py`)
   - the config dir defaults to the package's `configs/`, loaded via `importlib.resources` or the package path
7. Config loading: `plugin.config.madcap.toml` now lives in `configs/`, not in the data dir. Make sure the loader still accepts `type = "config_output_plugin"` from the configs directory, for example by also scanning `configs/` for that type. Keep one single code path.
8. Per-plugin output directory and the optional MadCap path:
   - in `madcap_html_output/models.py` `MadcapHtmlOutputConfig`, add `output_dir: Optional[str] = None`
   - in `configs/build_sdm.toml` under the MadCap plugin section, set `output_dir = "generated/MadcapHtmlOutput"`
   - add an optional override hook so a plugin can supply its own output dir; otherwise the runner keeps `<output_dir>/<Plugin>/`
   - precedence: CLI `--madcap-output-dir` > config `output_dir` > runner default
   - path resolution: a relative CLI path resolves against the current working directory; a relative config path resolves against the repo root
   - when a path is set, write only there (replace); create the directory if missing
9. Make failures fatal: `safe_execute` logs, then re-raises. `cli.main` catches the error and exits 1. Update the tests that asserted skip behavior.
10. Fix `allowed_field_types`:
    - `field_schema_model.py` validates against the list in `src/sdm/config/field_schema.config.toml`
    - load that config before the schema files are validated, or pass it in via a validator context
    - add `long`, `boolean` and `byte` to the config list
    - delete the hard-coded set
11. CLI, in two parts:
    - **11a (commit 1).** Replace `main.py` with `cli.py` (argparse subcommands). Add only `build [--dry-run] [-ll LEVEL] [-c CONFIG_DIR]`, with exactly the old `main.py` flags and behavior.
    - **11b (commit 4).** Add:
      - `check-generated`: build MadCap into a temporary dir, then run a recursive byte-for-byte diff against `generated/MadcapHtmlOutput/`. Print the differing files and exit 1 on any difference.
      - a placeholder for `validate` (implemented in PR 3)
    - Commit 3 adds `--madcap-output-dir PATH` to `build`, as part of step 8.
12. Move `tools/build_sdm/tests/` → `tests/`. Update the imports and the two tests that read real data so they use `src/sdm`; one of them still asserts `7.1.0`.
13. Add a determinism check: run `build` twice and diff the results. If anything nondeterministic shows up (timestamps, dict or set ordering), fix it.
14. Run `uv run build-sdm build` and commit `generated/MadcapHtmlOutput/`. Add `build/` to `.gitignore` if it isn't there.
15. Update the standards files:
    - `AGENTS.md`: replace the "available after PR 2" placeholders with the real `build-sdm build` and `check-generated` commands
    - `.github/instructions/python.instructions.md`: note the package layout (`build_sdm.*` imports)
    - if implementation departed from ADR 0002 or 0003, amend the ADR in this PR
16. Plan status: set `docs/plans/sdm-migration/02-package.md` to `Status: done` and mark PR 2 done in the `README.md` status table.

## Verification
- `uv sync && uv run pytest`: everything passes, about 174 tests plus new ones for path precedence and failure exit codes.
- `uv run ruff check`, `uv run mypy`: no new errors.
- Parity check, **covering all plugins**, run at commit 1 of the commit order:
  1. In Illuminate at the PR 1 SHA, run the original tool from an exported tree, not the working tree: `cd scripts/build_gim && uv run python3 main.py`.
  2. Run `uv run build-sdm build` here. Temporarily point the MadCap output at the same build directory, or diff the two locations separately.
  3. Diff each plugin directory, old against new: `CategoryDataCSVOutput/`, `FieldMappingCSVOutput/`, `JsonFileOutput/`, `MessageSummariesOutput/`, `MadcapHtmlOutput/`.
  4. Expected result at commit 1: **byte-identical for every plugin**. Any difference is a refactor regression; fix it before continuing.
  5. Re-run the parity check after commit 5 (`allowed_field_types`). Differences are allowed only where that change explains them, and each one is listed in the PR description.
  6. Separately, note in the PR how the freshly built `category_data.csv` and `message_summaries.json` differ from the copies checked in to Illuminate (`illuminate/core/data/`, `illuminate/core/spotlight/`). That difference already exists and isn't caused by this PR. Record it in the Illuminate SDM-removal issue.
- `uv run build-sdm build --madcap-output-dir "$TMPDIR/x"` writes only to `$TMPDIR/x`, and `generated/` is unchanged.
- With the config `output_dir` set to another path and no flag, output goes to that path. With both set, the flag wins.
- A test plugin that raises makes the CLI exit 1.
- `uv run build-sdm check-generated` exits 0 on a clean tree, and exits 1 after one generated file has been hand-edited.
- `grep -rn "build_gim\|gim_artifacts\|_meta/gim" tools/ tests/ src/ pyproject.toml` returns no hits. This is the same scope as step 5; docs are excluded.
