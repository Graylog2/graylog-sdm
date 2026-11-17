# Review standards for graylog-sdm

This repo is the source of truth for the Graylog Security Data Model (SDM). Downstream repos consume it and never edit it.

## What to check

- **Source of truth.** SDM definitions are edited only under `src/sdm/`. Flag any PR that changes SDM meaning anywhere else.
- **Generated output.** Files under `generated/` must never be hand-edited. If a PR changes `src/sdm/` or the build tool, it must also include the regenerated `generated/` output. If a PR changes `generated/` without a matching source or tool change, flag it.
- **Change classification.** Every SDM change is additive, deprecation, or breaking. A rename, removal, or type change is breaking and requires an `sdm_version` bump. Scrutinize changes claimed as additive: changing a field's meaning, narrowing allowed values, or promoting a field to required is not additive. A removed field name or GIM code must never be reused for a different meaning.
- **Descriptions.** Meta fields (`title`, `description`) must be US-ASCII printable characters only (no smart quotes, em dashes, or other Unicode) and written for a technical audience: precise, unambiguous, useful to security practitioners and engineers.
- **Field classification.** Judge whether each required / recommended / optional assignment is justified. Required must stay conservative: only fields needed for correct event analysis (e.g. used by event definitions or alerts).

## What not to comment on

Do not comment on things CI enforces: formatting, naming patterns, and generated-output freshness. Focus on judgment calls: whether a classification is justified, description quality, and whether a change is really additive.

## Plans

Files in `docs/plans/` describe intended work, not facts. Review the code against the PR's stated purpose, not against a plan. ADRs in `docs/decisions/` are authoritative decisions. Ignore `docs/plans/archive/`; it is history only.
