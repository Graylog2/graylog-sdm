# graylog-sdm

The Graylog Security Data Model (SDM) is the authoritative source for the field schema, the GIM (Graylog Information Model: classes, categories, subcategories and event types) and reserved values.

This repo is the source of truth. graylog-project-illuminate keeps its own copy of the SDM until a later cutover switches it to consume this repo.

## Layout

| Path | Contents |
|---|---|
| `src/sdm/infomodels/` | GIM categories, one file per category (`10.authentication.toml`) |
| `src/sdm/schema/` | Field schema, one file per entity (`user.toml`) |
| `src/sdm/config/` | SDM-wide config: `sdm_version`, allowed field types, documentation sections |
| `tools/build_sdm/` | The `build-sdm` tool, with its output plugins and their config in `configs/` |
| `generated/MadcapHtmlOutput/` | MadCap HTML built from the source. Committed; never edit it by hand |
| `build/sdm_artifacts/` | Output from the other plugins (CSV, JSON). Gitignored |
| `tests/` | Tests for `build-sdm`, including output snapshots in `tests/golden/` |
| `docs/decisions/` | Architecture decision records (ADRs) |
| `docs/plans/` | Active plans, and finished ones in `archive/` |
| `docs/proposals/` | Proposals that need a decision before any work starts |
| `docs/templates/` | A template for new GIM category files |

## Quick start

You need [uv](https://docs.astral.sh/uv/). It installs Python 3.13 and the dependencies.

```sh
uv sync
uv run build-sdm build
uv run build-sdm validate --base-ref origin/main
```

- `build` writes the MadCap HTML to `generated/MadcapHtmlOutput/` and the other output to `build/sdm_artifacts/`.
- `validate --base-ref origin/main` is the check CI runs: a violation that is new relative to `main` fails, and violations that already exist on `main` are only warnings.

Plain `uv run build-sdm validate`, with no base ref, lists every known existing violation and exits 1. That is expected, not a broken checkout: without a base ref, every violation is an error (ADR 0004).

## More

- [docs/contributing.md](docs/contributing.md): how to change the SDM, every command, the lint rules and CI.
- [docs/decisions/](docs/decisions/): why the repo works the way it does.
- [AGENTS.md](AGENTS.md): development standards for people and AI agents.
