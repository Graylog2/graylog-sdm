# Contributing

How to change the SDM, run the tool, and get a PR through CI. For the development standards that people and AI agents both follow, see [`AGENTS.md`](../AGENTS.md).

## Set up

You need [uv](https://docs.astral.sh/uv/). From the repository root:

```sh
uv sync
```

This installs Python 3.13 (from `.python-version`), the tool and its development dependencies.

## Editing the SDM

Edit SDM data only under `src/sdm/`. After every change:

1. Run `uv run build-sdm build`, and commit the regenerated `generated/MadcapHtmlOutput/` with the source change.
2. If the change alters other plugin output (it usually does), refresh the snapshots with `uv run pytest tests/test_golden_outputs.py --update-golden` and commit `tests/golden/` too.
3. Run `uv run build-sdm validate --base-ref origin/main` and fix anything new it reports.
4. Classify the change as additive, deprecation or breaking. A rename, removal or type change is breaking and needs an `sdm_version` bump in `src/sdm/config/sdm_version.config.toml`. Never reuse a removed field name or GIM code for a different meaning.

### Infomodel files (GIM)

Each file in `src/sdm/infomodels/` defines one category. The file name is the category code, then the name: `26.system_time.toml`. A trimmed example, based on that file, with names that follow the current rules:

```toml
type = "gim"

[system_time]
name = "system_time"
code = 26
description = "The System Time category captures events where the system clock is modified."
required_fields = ["source", "user_name"]
recommended_fields = []
optional_fields = []

[system_time.subcategories.00]
name = "time_change"
description = "Changes to the system clock, manual or automatic."
class = "endpoint"
required_fields = []
recommended_fields = []
optional_fields = []

[system_time.subcategories.00.event_type_codes]
00.name = "system_time_changed"
00.description = "The system clock was changed."

[system_time.subcategories.99]
name = "default"
description = "System time messages"
# ... the same keys as above
```

- Category, subcategory and event type codes are two digits each. Together they form the six-digit event type code (`260000` above) that Illuminate uses.
- Every category has a `default` subcategory numbered `99`. Its required fields are the baseline for every other subcategory in the category.
- `class` is `endpoint` or `protocol` in the current data.
- Subcategories can also carry a `summary` table, and categories can carry `summaries` and `indicators`. See the existing files and the template for the shapes.

Some existing names contain spaces (`"system time changed"`). They're known violations; new names must follow the naming rule.

### Adding a category

1. Copy `docs/templates/category.toml.template` to `src/sdm/infomodels/<code>.<name>.toml`, using an unused two-digit code.
2. Replace every `category_name` with the category name and set `code`.
3. Fill in the subcategories and event types. Keep `99` as `default`.
4. Follow the steps in [Editing the SDM](#editing-the-sdm). The build finds the new file on its own; nothing needs registering.

### Schema files

Each file in `src/sdm/schema/` defines one entity and its fields:

```toml
type = "field_schema"

[user]
description = "The user fields describe the account associated with the activity."
entity_type = "top"

[[user.fields]]
field_suffix = "name"
example_values = "jsmith"
field_type = "keyword"
description = "Name of the user account."
```

`entity_type` decides each field's full name:

| `entity_type` | Full field name | Example |
|---|---|---|
| `top` | entity name, `_`, suffix | `user` + `name` = `user_name` |
| `sub` | appended to each entity in `applies_to` | `hash` with `applies_to = ["file", "process"]`: `file_hash_sha256`, `process_hash_sha256` |
| `reserved` | the suffix itself, with no prefix | `timestamp` |

`field_type` must be one of the `allowed_field_types` in `src/sdm/config/field_schema.config.toml`.

### Classifying fields

Every field attached to a subcategory is required, recommended or optional. Keep required conservative: only fields needed for event analysis, such as those used by event definitions or alerts. The full rules are in [`.github/instructions/sdm-data.instructions.md`](../.github/instructions/sdm-data.instructions.md); that file is also what Copilot reviews against.

### Descriptions

Meta fields such as `title` and `description` use printable US-ASCII only: no smart quotes, em dashes or other Unicode. Write for a technical audience: precise and unambiguous.

## Commands

Run all commands from the repository root.

| Command | What it does |
|---|---|
| `uv run build-sdm build` | Builds every enabled output plugin |
| `uv run build-sdm build --madcap-output-dir PATH` | Writes the MadCap HTML to `PATH` instead of its configured location. `PATH` must be new, empty or marked as build-sdm output; `--force` overrides this. |
| `uv run build-sdm build --dry-run` | Runs the build without writing files |
| `uv run build-sdm check-generated` | Builds into a temporary directory and compares the MadCap HTML with the committed copy |
| `uv run build-sdm validate` | Loads the source and runs the lint rules; every violation is an error |
| `uv run build-sdm validate --base-ref REF` | The same, but only violations that are new relative to `REF` fail |
| `uv run taplo fmt` | Formats the TOML files; `--check` only reports |
| `uv run pytest` | Runs the tests |
| `uv run ruff check`, `uv run ruff format --check`, `uv run mypy` | Lint, format check and type check for the Python code |

Every `build-sdm` command also takes `--loglevel` and `--config_dir`.

### MadCap output

- The MadCap HTML goes to `generated/MadcapHtmlOutput/` and is committed. This location comes from `output_dir` in `tools/build_sdm/configs/madcap_html_output.toml`, relative to the repository root.
- `--madcap-output-dir PATH` overrides it, relative to the current directory. The override **replaces** the configured location: the build writes the MadCap HTML only to `PATH`.
- Because `PATH` may be inside a Flare project, the build refuses to overwrite files it didn't write there:
  - If `PATH` is new or empty, the build writes a `.build-sdm-output` marker into it, and later builds to the same `PATH` just work.
  - If `PATH` is not empty and has no marker, the build exits 1 and changes nothing. Pick an empty directory, or pass `--force` to write there anyway; files with the same names as generated pages are overwritten, and other files are left alone. A forced build doesn't add the marker, so each forced build needs `--force` again.
  - This check covers only `--madcap-output-dir`. The configured location is in the repository, where git shows every change.
- Without either, the MadCap HTML would go to `build/sdm_artifacts/MadcapHtmlOutput/`, like the other plugins' output.
- Always commit the regenerated default output with your source change, even if you also build to another location. CI checks that the committed copy is up to date.
- The build never deletes files. If a change removes a page, `check-generated` reports it as stale and prints the `git rm` command for it.

See ADR 0003.

## Lint rules

`build-sdm validate` runs these rules:

| Rule | Checks |
|---|---|
| `naming` | Class, category, subcategory and event type names are lowercase `a-z` words separated by underscores |
| `ascii-meta` | Meta fields contain printable US-ASCII only |
| `unique-names` | Subcategory and event type names are unique across the GIM, except `default` |
| `default-99` | The `default` subcategory is number `99`, and `99` is only `default` |
| `default-baseline` | Every subcategory requires at least the fields its category's `default` subcategory requires |
| `fields-exist` | Every field in a required, recommended or optional list is defined in the schema |
| `wildcards` | No broad wildcards; sub-field group wildcards only in recommended or optional |
| `codes` | Category codes are unique, and each infomodel file name starts with its code |

The existing data has known violations. With `--base-ref`:
- A violation that already exists at the base ref is a warning. One that doesn't is an error.
- A violation is identified by its rule and its entry. GIM entries are keyed by code (`gim:26.01/name`), so renaming a category, subcategory or event type keeps its existing violations as warnings, and renumbering it makes them new.
- Schema entries are keyed by name (`schema:user/fields/name/description`), and so are field references in GIM lists (`gim:26.01/required_fields/user_name`). Renaming a schema entity or field makes its existing violations new, so fix them in the same change.
- If any rule's violation count goes up, that fails too, even when each violation already existed.

Without `--base-ref`, every violation is an error, so plain `validate` exits 1 on the current data. See ADR 0004.

## Formatting

TOML under `src/sdm/` and `tools/build_sdm/configs/` is formatted with taplo, configured in `taplo.toml`. Run `uv run taplo fmt` before committing; CI runs `uv run taplo fmt --check`.

## CI

`.github/workflows/ci.yml` runs on every PR into `main`, on every push to `main`, and on demand. CI never commits; fix failures locally and push.

| Job | Fails when | Fix |
|---|---|---|
| `data-lint` | TOML isn't formatted | `uv run taplo fmt`, then commit |
| `data-lint` | `validate` finds a new violation, or a rule's count goes up | Run `uv run build-sdm validate --base-ref origin/main` and fix the errors it lists. Errors also show as annotations on the PR |
| `generated-fresh` | The committed MadCap HTML doesn't match a fresh build | Run the commands in the job summary: `uv run build-sdm build`, plus `git rm` for any stale file, then commit `generated/` |
| `python-qa` | ruff, ruff format, mypy or pytest fails | Run the same command locally. If a test in `tests/test_golden_outputs.py` fails because the output changed on purpose, refresh the snapshots (see [Editing the SDM](#editing-the-sdm)) |

Retargeting a PR to `main` doesn't start a run. Push a commit, or close and reopen the PR.

## Plans and decisions

- **ADRs** in `docs/decisions/` record lasting decisions and are authoritative. To add one, copy `docs/decisions/0000-template.md` to the next number, fill in `Context`, `Decision` and `Consequences`, and set `Status: accepted` when it's agreed. To change a decision, amend the ADR and say in which PR, or supersede it with a new one.
- **Plans** in `docs/plans/<name>/` describe intended work. They aren't facts: when a plan and the code disagree, the code wins. When a plan is done or abandoned, record its lasting decisions in ADRs, then `git mv` it to `docs/plans/archive/<Created as YYYYMMDD>-<name>/`. The archive is history only. Conventions are in [`docs/plans/README.md`](plans/README.md); see also ADR 0005.
- **Proposals** in `docs/proposals/` describe changes that need a decision before any work starts.
