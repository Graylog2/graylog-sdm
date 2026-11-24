# 0004. SDM lint policy

Status: accepted
Date: 2026-11-17

## Context
Nothing validated the SDM data automatically. Several authoring rules existed only as prose in the `sdm-build` skill. The existing data has known violations that cannot all be fixed at once.

## Decision
- `build-sdm validate` runs structural validation and a codified rule set derived from the authoring rules.
- TOML formatting is enforced with taplo, configured in `taplo.toml` so it never reorders keys and never collapses hand-wrapped arrays. A test formats a copy of every included file and checks that each still parses to the same values, which also guards future taplo upgrades. (Added in PR 3, follow-up F12.)
- A violation is identified by `rule_id` + `entry_key`. It fails only when it is new relative to a base ref. Violations that already exist at the base ref are reported as warnings.
- Each violation also reports the line of its entry in the source file, looked up from the `entry_key` after the rules run. The line is for display only and never part of the identity: it moves whenever lines above it change. (Added for follow-up F19.)
- GIM `entry_key`s use codes, not names (`gim:10.05/name`), so renaming an entry keeps its existing violations as warnings; renumbering it makes them new. (Added in PR 3, follow-up F5.)
- Ratchet: with a base ref, the check also fails if any rule's violation count goes up, even when every individual violation already existed. (Added in PR 3, follow-up F5.)
- If the base ref's source fails to load, every violation is treated as new.
- Without a base ref, every violation is an error.
- CI picks the base ref per event: the PR's base branch, or on push the commit before the push (ADR 0006).

## Consequences
- New content must conform; existing violations can be fixed over time without blocking unrelated PRs.
- Plain `build-sdm validate` with no base ref exits 1 on the current data. That is expected, not a broken checkout.
