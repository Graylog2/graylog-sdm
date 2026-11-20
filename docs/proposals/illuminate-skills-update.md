# Proposal: update the Illuminate SDM skills for graylog-sdm

Status: proposed
Date: 2026-11-20

Two skills in the `ai-community` marketplace repo work with the SDM: `sdm-terminology` and `sdm-build`. Both assume the SDM lives in graylog-project-illuminate. This proposal says what to change once graylog-sdm is the source of truth. Nothing here is implemented; the skills live in another repo.

References checked on 2026-11-20 against `ai-community` at `9e6b81e`.

## `sdm-terminology`

File: `illuminate/skills/sdm-terminology/SKILL.md`.

What it does today:
- Reads `build/sdm_ref.md`, generating it with `python scripts/llm/build_sdm_ref.py` if it's missing.
- Names `_meta/gim/infomodels/` and `_meta/gim/schema/` as the source of truth.
- Checks that it's in an Illuminate repo by looking for `_meta/gim/`, and that `scripts/llm/build_sdm_ref.py` exists.

Problems:
- `scripts/llm/build_sdm_ref.py` doesn't exist in graylog-project-illuminate, so the skill can't generate its reference file anywhere.
- After the cutover, `_meta/gim/` won't exist in Illuminate either.

Proposed changes:
1. **Source paths:** point to graylog-sdm's `src/sdm/infomodels/` and `src/sdm/schema/`.
2. **Repo check:** replace the `_meta/gim/` check with one that finds graylog-sdm (see the open question below) and confirms `src/sdm/infomodels/` exists there.
3. **Reference index:** drop `build_sdm_ref.py`. Generate the index with `build-sdm` instead, so it's built from the same loaded and validated model as every other output. Two options:
   - **An output plugin** (recommended), for example `SdmReferenceOutput`, writing `build/sdm_artifacts/SdmReferenceOutput/sdm_ref.md`. It fits the existing plugin model, runs with every `build`, and is covered by the golden snapshots.
   - **A subcommand**, `build-sdm reference`, writing the index on demand. It's more direct for a skill to call, but adds a second path that loads the model.

   Either way, the index lists categories, subcategories and event types with their codes and names, and every full field name with its type and description. `category_data.csv` and `gim_field_mapping.csv` already hold most of this and could serve as a stopgap.
4. **Version:** bump the skill's `metadata.version`.

## `sdm-build`

File: `illuminate/skills/sdm-build/SKILL.md`.

Its meta-field, classification, enumeration and naming rules are now also written out in this repo's `.github/instructions/sdm-data.instructions.md`, and most of its checklist is enforced by `build-sdm validate`. This repo should be the source, and the skill should defer to it.

Proposed changes:
1. State that graylog-sdm's `.github/instructions/sdm-data.instructions.md` and `AGENTS.md` are authoritative, and that the skill summarizes them.
2. Replace the manual checks with `uv run build-sdm validate --base-ref origin/main`, run in graylog-sdm. Map each checklist item to what enforces it:

   | Checklist item | Enforced by |
   |---|---|
   | Meta fields are printable US-ASCII | `ascii-meta` |
   | New names are lowercase and underscore-separated | `naming` |
   | No duplicate subcategory or event type names | `unique-names` |
   | Default subcategory is numbered 99 | `default-99` |
   | Classification with justification | Review (judgment) |
   | Required fields are conservative | Review (judgment) |
   | Explicit enumeration; sub-field wildcards only in recommended or optional | `wildcards` |

   Two rules the skill doesn't mention are also enforced: `default-baseline` (a subcategory requires at least its `default`'s fields; the skill states the rule but has no checklist item) and `fields-exist`.
3. Add the steps that make a change complete in graylog-sdm: `uv run build-sdm build`, commit `generated/`, refresh the golden snapshots, classify the change (additive, deprecation, breaking) and bump `sdm_version` if it's breaking. See `docs/contributing.md`.
4. Bump the skill's `metadata.version`.

## Skills README

File: `illuminate/skills/README.md`, lines 35-37 (the `sdm-terminology` prerequisites). They list `_meta/gim/infomodels/`, `_meta/gim/schema/` and `scripts/llm/build_sdm_ref.py`. Replace them with the graylog-sdm requirement and the way the skill finds it.

## Open question: how a skill finds graylog-sdm

The skills run in an Illuminate checkout, which won't contain the SDM after the cutover. Options:

| Option | How | Trade-off |
|---|---|---|
| Sibling checkout | Look for `../graylog-sdm` next to the current repo | No setup when the convention holds; fragile when it doesn't |
| Environment variable | `GRAYLOG_SDM_DIR` points to a checkout | Explicit and works anywhere; every user must set it |
| Published artifact | Download a released reference index or JSON export (follow-up F9) | No checkout and pinned to a version; needs a release process first, and can't see unreleased changes |

A reasonable path: the environment variable, falling back to the sibling checkout, until F9's published artifact exists. `sdm-build` needs a checkout regardless, because it edits the source.

**Decision needed:** which option, and whether to wait for F9.
