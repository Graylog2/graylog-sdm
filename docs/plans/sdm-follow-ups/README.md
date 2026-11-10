# SDM Follow-ups: review findings beyond the migration

Status: active
Created: 2026-11-10
Tracking: (issue link)

Follow-up activities from a tech-lead review of the SDM migration plan (`docs/plans/sdm-migration/`). The review's core point: the SDM is a **data contract** consumed by Illuminate's pipelines and lookups, not just documentation. Most items move it toward machine-enforced compatibility.

Not covered here:
- **Two sources of truth / drift with Illuminate:** handled by the planned Illuminate issue to remove the SDM artifacts and tools once graylog-sdm can publish docs.
- **PR 2 bundling a refactor with behavior changes:** handled in `docs/plans/sdm-migration/02-package.md` with ordered commits and a parity check across all plugins.

## Summary

| # | Follow-up | Priority | Target | Decision needed |
|---|---|---|---|---|
| F1 | Golden-file tests for all output plugins | High | PR 2 or PR 3 | No |
| F2 | Compatibility checker + enforced `sdm_version` bump | High | After PR 3 (extends `validate --base-ref`) | Yes: versioning policy |
| F3 | Minimal CI from PR 2; branch protection now | High | Now / PR 2 | Yes: CI sequencing |
| F4 | Safe writes for the MadCap output path | High | PR 2 | No |
| F5 | Robust violation fingerprints + violation ratchet | Medium | PR 3 | No |
| F6 | Correct base ref for push events | Medium | PR 4 | No |
| F7 | Check that pydantic v1 works on Python 3.13; schedule v2 | Medium | Before PR 2 | Yes: v2 date |
| F8 | Semantic validation rules | Medium | After migration | No |
| F9 | Machine-readable contract: JSON export, JSON Schema, release artifact | Medium | After migration (before Illuminate cutover) | Yes: artifact format |
| F10 | Reconsider the `src/sdm` directory name | Low | Before PR 1 | Yes |
| F11 | Collapse generated output in PR diffs | Low | PR 2 | No |
| F12 | Check that taplo preserves multiline strings | Low | PR 3 | No |

---

## F1. Golden-file tests for all output plugins

**Problem:** CI checks only the committed MadCap HTML for staleness. `category_data.csv` (Illuminate's core GIM lookup table) and `message_summaries.json` (core spotlight) matter more for production, yet a change that breaks them passes CI.

**Activity:**
- Add golden-file (snapshot) tests in `tests/golden/` for `CategoryDataCSVOutput`, `FieldMappingCSVOutput`, `JsonFileOutput` and `MessageSummariesOutput`, built from a small fixed fixture dataset (not the live data).
- Optionally, also snapshot outputs built from the live `src/sdm/` data. Updating a snapshot then becomes an explicit, reviewed act (`pytest --update-golden` or similar).

**Done when:** a change to any plugin's output fails `pytest` until the golden files are updated in the same PR.

## F2. Compatibility checker with an enforced `sdm_version` bump

**Problem:** "Classify every change as additive, deprecation or breaking" and "never reuse removed names or codes" exist only as prose and PR-template checkboxes. `sdm_version` (currently `7.1.0`) is hard-coded more than 100 times in Illuminate, so an unflagged breaking change is expensive downstream.

**Activity:** extend the base-ref comparison from PR 3 into `build-sdm compat --base-ref REF`:
- **Breaking** (fails unless the major version is bumped):
  - a field removed or renamed
  - a `field_type` changed
  - a category, subcategory or event-type code removed or reassigned to a different name
  - a field removed from a subcategory's required list
- **Additive** (requires at least a minor bump):
  - a new field, code or subcategory
  - a field added to recommended or optional
- **Deprecation:** a field marked deprecated (see F8).
- Fail CI when the detected change class isn't matched by an equal or greater bump in `src/sdm/config/sdm_version.config.toml`.
- Keep a registry of retired names and codes so they can never be reused, even several versions later.

**Decision needed:** the versioning policy. Is adding a required field breaking? What exactly does a major, minor and patch bump mean? Record the answer as an ADR.

**Done when:** a PR that removes a field without a major bump fails CI with a clear message.

## F3. Minimal CI from PR 2; branch protection now

**Problem:** CI arrives in PR 4, so PRs 1–3 merge into the source of truth unchecked. Branch protection is only a proposal in PR 5, but the repo is public and already in use.

**Activity:**
- **Now:** turn on branch protection or a ruleset for `main`:
  - at least one approval from someone other than the author
  - auto-merge disabled
  - pushes to `main` restricted
- **PR 2:** add a minimal workflow running `uv run pytest` and `uv run build-sdm check-generated`. PR 4 then expands it rather than creating it.
- Update `04-ci.md` and the `repo-governance.md` proposal to match.

**Decision needed:** whether to move CI earlier. This changes the scope of PRs 2 and 4.

## F4. Safe writes for the MadCap output path

**Problem:** `--madcap-output-dir` replaces the default location. If the plugin clears or overwrites its output directory, pointing it at a Flare project could destroy hand-written content.

**Activity:**
1. Check whether `MadcapHtmlOutput` (or `utils.file.write_file`) deletes or cleans its target directory.
2. Write only into an empty directory, or one containing a `.build-sdm-output` marker file that the tool itself created. Otherwise refuse, unless `--force` is given.
3. Never delete files the tool didn't write. If stale-file cleanup is needed, limit it to files listed in a manifest from the previous run.
4. Add tests for the refuse, force and marker cases.

**Done when:** running with `--madcap-output-dir` pointed at a non-empty directory without a marker exits non-zero and changes nothing.

## F5. Robust violation fingerprints and a violation ratchet

**Problem:** violations are matched across base and head by `rule_id` + `entry_key`.
- A rename or move changes `entry_key`, so an existing violation looks new (a false failure), or a new violation can hide behind a rename.
- Existing violations warn forever, and nothing drives the count down.

**Activity:**
- Include stable identifiers in `entry_key` where they exist: codes for categories, subcategories and event types; full field names for fields.
- Add tests for rename and move scenarios.
- **Ratchet:**
  - `validate` reports the count per rule for base and head.
  - CI fails if any count goes up, even where every individual violation is "existing".
  - The counts go in the PR job summary.

## F6. Correct base ref for push events

**Problem:** on push to `main`, `04-ci.md` compares against `HEAD~1`. That misses all but the last commit when several are pushed at once.

**Activity:**
- Use `${{ github.event.before }}` as the base ref for push events.
- Fall back to no base when it's the all-zero SHA (first push or new branch).
- Update `04-ci.md`.

## F7. Pydantic v1 on Python 3.13; schedule v2

**Problem:** the plan keeps pydantic v1 and pins Python 3.13. That combination has to be confirmed rather than assumed, and pydantic v1 has no long-term future.

**Activity:**
- Before PR 2, confirm that the pinned `pydantic>=1.10,<2` resolves to a release that supports 3.13, and that the full test suite passes on 3.13 with no deprecation errors.
- Open a tracked issue for the pydantic v2 migration with a target date. The model code uses `parse_obj`, `root_validator`, `constr(regex=)` and `Extra`, so the change is contained but not trivial.

**Decision needed:** the target date or release for v2.

## F8. Semantic validation rules

**Problem:** the PR 3 rules check naming and references. They miss semantic errors that would produce wrong data downstream.

**Activity:** add rules (each with a `rule_id`, tests and docs) for:
- **`field-type-consistency`:** a field name has the same `field_type` everywhere it appears, including sub-field expansion.
- **`example-values-typed`:** `example_values` parse as the declared `field_type` (`long`, `boolean`, `ip`, and so on).
- **`deprecation-metadata`:** deprecated fields carry `deprecated = true` and `replaced_by` (or an explicit `replaced_by = ""`); referencing a deprecated field in required lists warns. This requires adding the fields to the schema model.
- **`category-required-on-default`:** category-level required fields also appear in the default subcategory's effective required set.

## F9. Machine-readable contract

**Problem:** TOML is a good authoring format but a poor interface. Consumers other than `build_sdm` (Illuminate tooling, skills, other teams) have nothing stable to depend on, and editors give no feedback while authoring.

**Activity:**
1. **JSON Schema for the source files:**
   - Generate it from the pydantic models, or write it by hand.
   - Commit it under `schemas/`.
   - Wire it into `taplo.toml`, so editors validate TOML as you type.
2. **Normalized JSON export:**
   - Add a `JsonFileOutput`-style plugin that emits the full resolved SDM (categories, subcategories, event types, fields, sub-field expansion) in one documented, versioned format.
3. **Release artifact:**
   - On an `sdm_version` bump merged to `main`, tag `vX.Y.Z` and publish a GitHub release containing the JSON export, the JSON Schema, `category_data.csv` and `message_summaries.json`.
   - This becomes what Illuminate consumes after cutover.

**Decision needed:** the export format and the release mechanism. Settle both before the Illuminate cutover issue is worked.

## F10. Reconsider the `src/sdm` directory name

**Problem:** under Python's `src/` layout convention, `src/` holds packages. Build backends, pytest and IDEs may treat `src/sdm` as an import root. Here it holds TOML data while the code lives in `tools/`, which is confusing.

**Activity:**
- Decide between keeping `src/sdm/` (with explicit exclusions in hatch, pytest and IDE configs) and renaming it before PR 1 to `sdm/` or `data/sdm/`.
- Renaming later is a breaking path change for every consumer, so decide before PR 1.

**Decision needed:** keep or rename. If you rename, update the plans and ADR 0001.

## F11. Collapse generated output in PR diffs

**Problem:** committed MadCap HTML produces large diffs that reviewers will skim, and that bury the source changes.

**Activity:**
- Add `.gitattributes` with `generated/** linguist-generated=true`. GitHub then collapses those files in PR diffs and leaves them out of language stats.
- `check-generated` still guards their correctness.

## F12. Check that taplo preserves multiline strings

**Problem:** PR 3 reformats all source TOML with taplo. Multiline `"""` descriptions hold Markdown, and changes to whitespace or line endings inside them would change the content.

**Activity:**
- In PR 3, before the formatting commit, pin the taplo options that touch strings and arrays.
- After formatting, confirm that every source file still parses to the same values (a parse → compare script, not just a check that the output is unchanged) and that `generated/` is byte-identical.
- Add the parse-equivalence check as a test, so future formatter upgrades are covered too.
