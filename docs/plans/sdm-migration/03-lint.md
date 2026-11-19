# SDM Migration — PR 3 of 5: Source-data linting (`build-sdm validate`) + TOML formatting

Status: active
Tracking: (PR link)

Overview: `docs/plans/sdm-migration/README.md`. Depends on PR 2 (`02-package.md`). Next: `04-ci.md`.

## Context
Today the only checks on SDM data are the pydantic models, and nobody runs them automatically. The authoring rules in the `sdm-build` skill (`~/.claude/plugins/marketplaces/graylog-dev/illuminate/skills/sdm-build/SKILL.md`) exist only as prose. The skill admits some existing entries break them. This PR codifies the rules, so that CI can fail on **new** violations and only warn on violations that already exist.

## Decisions (from interview)
- Every rule below is in scope.
- New versus existing: a violation fails only if it is **not** present on the base ref. A violation counts as present if the same `rule_id` and `entry_key` occur there. Editing an entry that already violated a rule still produces only a warning.
- Without `--base-ref`, every violation is an error.
- TOML formatting is enforced with taplo. The imported data is reformatted in a **separate commit**.
- Follow-ups targeted at this PR are folded in: F5 (code-based `entry_key`s and a per-rule ratchet), F12 (taplo must not change string values) and F18 (log build errors once). See `docs/plans/sdm-follow-ups/README.md`.

## Steps
1. Branch `migration/03-lint`.
2. Structural validation in `build_sdm.validate`:
   - run the same load path as `build`: TOML parse → pydantic models → `restructure_gim_config` → `sub_fields.validate_applies_to`
   - do not run any output plugins
   - collect errors (fail fast is acceptable for parse errors)
3. Rules framework in `tools/build_sdm/rules/`:
   - `Violation(rule_id: str, entry_key: str, message: str, file: Path)`
   - `entry_key` is a stable logical path that doesn't depend on line numbers. GIM entries are keyed by code, not name, so a rename keeps the key (F5): `gim:10` (category), `gim:10.05` (subcategory), `gim:10.05.03` (event type), then an attribute and optionally a list item, e.g. `gim:10.05/name` or `gim:10.05/required_fields/user_name`. Schema entries are keyed by entity and full field name, e.g. `schema:source/fields/source_bytes_sent`.
   - `file` is repo-relative, e.g. `src/sdm/infomodels/10.authentication.toml`
   - each rule is a function `(model) -> Iterable[Violation]`, registered in a list
4. Rules (IDs are stable and appear in output and docs):

| rule_id | Check |
|---|---|
| `naming` | class, category, subcategory and event-type names match `^[a-z]+(_[a-z]+)*$` |
| `ascii-meta` | meta fields contain only printable US-ASCII (plus `\n`/`\t` in multiline strings): GIM category, subcategory and event-type `description`, subcategory `summary.*`, `summaries`/`indicators` `title` and `description`; schema entity `title`/`description` and field `description` |
| `unique-names` | subcategory names and event-type names are unique across the GIM, except `default` |
| `default-99` | a subcategory named `default` has code `99`, and code `99` is named `default` |
| `default-baseline` | each subcategory's `required_fields` include the default subcategory's `required_fields` in the same category |
| `fields-exist` | every non-wildcard entry in required/recommended/optional (category and subcategory level) resolves to a schema field: `<entity>_<field_suffix>` for top entities, `<parent>_<sub>_<field_suffix>` for sub entities, or a reserved literal |
| `wildcards` | no wildcard in required; in recommended/optional, a wildcard must be exactly a sub-field group `<parent>_<sub>_*` where `<sub>` is a sub entity whose `applies_to` lists `<parent>` |
| `codes` | category codes are unique; the `NN.` filename prefix equals `code`. Two-digit subcategory and event-type codes are already enforced by the pydantic models, so a violation there is a structural error. |

Check the exact meta-field list and the field-name composition rules against `gim_schema/atomic_fields.py` and `field_schema_model.py` before you implement them.

5. Base-ref comparison:
   - for `validate --base-ref REF`, export `src/sdm` at REF with `git archive REF src/sdm` into a temporary dir
   - run structural validation and the rules on both trees, then diff the violation sets on `(rule_id, entry_key)`
   - new violations are errors (exit 1); existing ones are warnings
   - if the base tree fails to load structurally, treat every head violation as new and say so in the output
   - output format: `LEVEL rule_id file entry_key: message`, then a summary count
   - ratchet (F5): report the per-rule counts for base and head; fail if any rule's count goes up, even when every individual violation is existing. When `GITHUB_STEP_SUMMARY` is set, also write the counts there as a Markdown table.
   - for GitHub Actions, also emit `::error file=…::` and `::warning file=…::` annotations when `GITHUB_ACTIONS=true`
6. CLI: `build-sdm validate [--base-ref REF] [-ll LEVEL]`.
7. Tests in `tests/rules/`: one passing fixture and one failing fixture per rule, using the `gim_config_helpers` builders, plus a base-ref test that builds a temporary git repo. The base-ref tests include a rename (same code, so the violation stays a warning) and a renumber (new code, so it is a new error), per F5.
8. TOML formatting:
   - add `taplo` to the dev dependencies (the `taplo` PyPI wheel)
   - add a root `taplo.toml` with include `src/sdm/**/*.toml` and `tools/build_sdm/configs/*.toml`; choose options that keep multiline `"""` strings intact
   - F12: before formatting, add a test that copies every included file to a temporary directory, runs `taplo fmt` on the copies with the repo's `taplo.toml`, and checks each copy parses (`tomllib`) to the same values as the original. That covers future taplo upgrades too. The golden snapshots and `check-generated` must also pass after the format commit.
   - **separate commit:** `taplo fmt`, then `uv run build-sdm build`, so the reformat doesn't change `generated/`. If it does, that is a formatter bug; fix the config.
9. Record the current warning baseline in the PR description: the per-rule counts from `validate` on main.
10. Update the standards files:
    - `AGENTS.md`: add `build-sdm validate` and `taplo fmt` to the commands
    - `.github/copilot-instructions.md`: finalize the "CI enforces this, don't comment" list using the rule IDs
    - `.github/instructions/sdm-data.instructions.md`: add the rule ID beside each rule that is now enforced, and keep inline only the judgment guidance CI can't check
    - amend ADR 0004 if the rule set or policy changed
11. F18, separate commit: log build errors once, in the CLI. Lower layers stop logging before re-raising; where a handler adds context, it raises with `from e` instead. Message-summary validation failures log as errors. A test checks that one failure produces one error-level record.
12. Plan status: set `docs/plans/sdm-migration/03-lint.md` to `Status: done` and mark PR 3 done in the `README.md` status table.

## Verification
- `uv run pytest tests/rules` passes; every rule has a seeded failing case.
- `uv run build-sdm validate` on the imported data with no base ref lists the existing violations and exits 1, as expected.
- `uv run build-sdm validate --base-ref HEAD` exits 0, warnings only.
- Add a subcategory named `Bad-Name`, run again: exit 1 with one `naming` error.
- `taplo fmt --check` passes after the format commit, and the parse-equivalence test passes.
- Renaming an existing violating subcategory keeps its violations as warnings; renumbering it makes them errors.
- `build-sdm check-generated` still passes.
