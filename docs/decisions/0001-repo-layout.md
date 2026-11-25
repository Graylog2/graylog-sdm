# 0001. Repository layout

Status: accepted; partly superseded by 0007 (MadCap output location)
Date: 2026-11-17

## Context
The SDM data and its generator move from graylog-project-illuminate (`_meta/gim/`, `scripts/build_gim/`) to this repo. In Illuminate, the data, the MadCap presentation config, and the tool sat side by side with no clear boundary.

## Decision
- SDM source data lives in `src/sdm/` (`infomodels/`, `schema/`, `config/`).
- The build tool lives in `tools/build_sdm/`, with tests in `tests/`.
- Output that is consumed downstream is committed to `generated/`. Output from other plugins goes to `build/sdm_artifacts/<Plugin>/`, which is gitignored.
- Presentation config (the MadCap output plugin config) is kept separate from SDM data and lives with the tool in `tools/build_sdm/configs/`. Per-entity `meta.plugin_config` blocks stay in the data files.

## Consequences
- `src/sdm/` is the one place to edit the SDM. Review rules and CI can be scoped to it by path.
- The tool needs repo-root discovery to find data and output paths (PR 2).
