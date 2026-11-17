# 0004. SDM lint policy

Status: accepted
Date: 2026-11-17

## Context
Nothing validated the SDM data automatically. Several authoring rules existed only as prose in the `sdm-build` skill. The existing data has known violations that cannot all be fixed at once.

## Decision
- `build-sdm validate` runs structural validation and a codified rule set derived from the authoring rules.
- TOML formatting is enforced with taplo.
- A violation is identified by `rule_id` + `entry_key`. It fails only when it is new relative to a base ref. Violations that already exist at the base ref are reported as warnings.
- Without a base ref, every violation is an error.

## Consequences
- New content must conform; existing violations can be fixed over time without blocking unrelated PRs.
- Plain `build-sdm validate` with no base ref exits 1 on the current data. That is expected, not a broken checkout.
