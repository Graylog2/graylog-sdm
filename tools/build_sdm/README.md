# build_sdm

Generates Graylog Security Data Model (SDM) build artifacts and documentation, including the GIM (Graylog Information Model), from the source data in `src/sdm/`, via a pluggable output-plugin architecture.

## Requirements

- [uv](https://docs.astral.sh/uv/) — manages the Python environment and dependencies
- Python 3.13 (uv will install this automatically if it isn't already available)

## Setup

From the repository root:

```bash
uv sync
```

This creates a `.venv` from the root `pyproject.toml`, installs the pinned dependencies from `uv.lock`, and installs this package as `build_sdm` with the `build-sdm` console script.

## Usage

Run the build from anywhere inside the repository (the repository root is found by walking up to the `pyproject.toml` with `name = "build-sdm"`):

```bash
uv run build-sdm build
```

`build` options:

| Flag | Description | Default |
|---|---|---|
| `-ll`, `--loglevel` | `debug`, `info`, `warning`, `error`, or `critical` | `info` |
| `-c`, `--config_dir` | Directory of script config files; a relative path resolves against the current directory | the package's `configs/` |
| `--dry-run` | Log what each enabled plugin would generate, and where, without writing any files | off |
| `--madcap-output-dir PATH` | Write the MadCap HTML only to `PATH` (relative to the current directory), instead of its configured location | unset |

Example:

```bash
uv run build-sdm build -ll debug --dry-run
```

Other commands:

| Command | Purpose |
|---|---|
| `uv run build-sdm check-generated` | Builds into a temporary directory and compares the MadCap HTML byte for byte with the committed `generated/MadcapHtmlOutput/` (the MadCap plugin's `output_dir`). It exits 1 and lists every changed, stale (no longer built) or missing file. To fix: `rm -rf generated/MadcapHtmlOutput && uv run build-sdm build`, then commit the result. |
| `uv run build-sdm validate` | Placeholder until PR 3; it exits 2. |

## Configuration

- **`configs/build_sdm.toml`** — global settings: `sdm_source_dir` (where `src/sdm/` lives; must be a relative path, because it is recorded in the output) and `output_dir` (where generated artifacts are written), both resolved relative to the repository root.
- **`configs/plugin.config.madcap.toml`** — MadCap presentation config (`type = "config_output_plugin"`), kept here rather than with the SDM data (ADR 0001). Files of this type in the config directory are loaded alongside the source data.
- **`configs/<plugin_name>.toml`** — one file per output plugin, each with a `[plugin]` table (`name`, `enabled`, plus that plugin's own options). Set `enabled = 0`/`1` to toggle a plugin without touching code. A plugin with no config file falls back to its `enabled_by_default` class attribute.

By default, output is written to `build/sdm_artifacts/<PluginClassName>/` at the repository root. A plugin can choose its own directory through its config, which replaces the default rather than adding a copy. `MadcapHtmlOutput` does this with `output_dir = "generated/MadcapHtmlOutput"` in `configs/madcap_html_output.toml`, a path relative to the repository root. The `--madcap-output-dir` flag takes precedence over that setting.

## Output plugins

All plugins live under `output_plugins/` and are auto-discovered — no registration step beyond adding the module.

| Plugin | Produces | Enabled by default |
|---|---|---|
| `CategoryDataCSVOutput` | `category_data.csv` — GIM event-type lookup consumed by Illuminate Core | yes |
| `FieldMappingCSVOutput` | `gim_field_mapping.csv` — one row per (event type, field) pair, joining each category's required/recommended/optional fields against `field_schema` metadata | yes |
| `JsonFileOutput` | Full GIM config dumped as JSON | yes |
| `JsonConsoleOutput` | Full GIM config printed to stdout (debug tool) | no |
| `MadcapHtmlOutput` | MadCap Flare-compatible HTML documentation | yes |
| `MessageSummariesOutput` | `message_summaries.json` — Graylog Security message-summary/indicator config | yes |
| `PlainTextOutput` (`sample_plaintext_output`) | Reference/example plugin, heavily commented as an authoring template | no |

### Adding a new output plugin

Follow the pattern in `output_plugins/sample_plaintext_output/plugin.py` (a fully-commented template) and `output_plugins/category_data_csv_output/plugin.py` (a simpler real example):

1. Create `output_plugins/<name>/{__init__.py,plugin.py}` with a `pydantic.BaseModel` config class and a class inheriting `base_output.OutputPlugin[YourConfig]` implementing `generate(gim_config, output_dir, plugin_config)`.
2. Add `configs/<name>.toml` with a `[plugin]` table.
3. Add tests under the repository's `tests/`, mirroring the naming/style of existing `test_<plugin>_*.py` files. `tests/gim_config_helpers.py` has shared builders (`build_gim_config`, `build_field_schema`) for constructing minimal `gim_config` fixtures.

## Running tests

From the repository root:

```bash
uv run pytest
uv run ruff check
uv run mypy
```

The root `pyproject.toml` grandfathers pre-existing modules against the newly-added strict ruff/mypy rules (see the `extend-exclude`/`[[tool.mypy.overrides]]` sections) — new and modified code is held to the full standard described in the `python-coding-standards` skill.

## Known data gaps

`FieldMappingCSVOutput` fails fast if a category references a field with no matching `field_schema` entry, surfacing gaps in `src/sdm/schema/`.

### Sub-fields

Some `src/sdm/schema/*.toml` entities are sub-field groups (`entity_type = "sub"`, e.g. `hash`, `geo`, `as`) whose fields are appended onto one or more "top" entities rather than existing as standalone fields. Each sub-entity declares its parents once via `applies_to = ["file", "process"]`; `gim_schema/sub_fields.py` validates those references (every name must be a real `entity_type = "top"` entity) and composes the resulting field names (e.g. `hash`'s `sha256` field becomes both `file_hash_sha256` and `process_hash_sha256`).

This composition is applied consistently in two places:
- `MadcapHtmlOutput` renders a "Sub-fields" table on every parent entity's page (linking back to the sub-entity's own page), and an "Applies to" list on the sub-entity's page.
- `FieldMappingCSVOutput` resolves composed names like `file_hash_sha256` directly, and expands wildcard patterns like `file_hash_*` in `recommended_fields`/`optional_fields` (wildcards are never allowed in `required_fields`, matching the `sdm-build` skill's rule).

A sub-entity's own bare field name (e.g. `hash_sha256`, with no parent prefix) is intentionally not a valid field on its own and will not resolve.

## Project layout

```
tools/build_sdm/
├── cli.py                  # CLI entry point (build-sdm)
├── runner.py               # Orchestrates the build
├── base_output.py          # OutputPlugin abstract base class + registry
├── config_loader.py        # Parses/validates GIM + script config TOML
├── plugin_loader.py        # Discovers and instantiates enabled plugins
├── gim_schema/              # Pydantic models for source TOML validation
├── utils/                   # Shared helpers (file I/O, paths, sanitization, serialization)
├── output_plugins/          # One subpackage per output plugin
└── configs/                 # Per-script and per-plugin TOML configuration
```

Tests live in the repository's `tests/` directory, one test file per behavior.
