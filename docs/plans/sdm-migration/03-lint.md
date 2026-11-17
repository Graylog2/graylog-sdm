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

## Steps
1. Branch `migration/03-lint`.
2. Structural validation in `build_sdm.validate`:
   - run the same load path as `build`: TOML parse → pydantic models → `restructure_gim_config` → `sub_fields.validate_applies_to`
   - do not run any output plugins
   - collect errors (fail fast is acceptable for parse errors)
3. Rules framework in `tools/build_sdm/rules/`:
   - `Violation(rule_id: str, entry_key: str, message: str, file: Path)`
   - `entry_key` is a stable logical path that doesn't depend on line numbers, e.g. `infomodel:authentication/subcategories/00/name` or `schema:source/fields/bytes_sent`
   - each rule is a function `(model) -> Iterable[Violation]`, registered in a list
4. Rules (IDs are stable and appear in output and docs):

| rule_id | Check |
|---|---|
| `naming` | class, category, subcategory and event-type names match `^[a-z]+(_[a-z]+)*$` |
| `ascii-meta` | meta fields (`description`, `title`, `summary.*`, event-type `description`) contain only printable US-ASCII (plus `\n`/`\t` in multiline strings) |
| `unique-names` | subcategory names and event-type names are unique across the GIM, except `default` |
| `default-99` | a subcategory named `default` has code `99`, and code `99` is named `default` |
| `default-baseline` | each subcategory's `required_fields` include the default subcategory's `required_fields` in the same category |
| `fields-exist` | every entry in required/recommended/optional (category and subcategory level) resolves to a schema field (`<entity>_<field_suffix>`, or a reserved literal); `<entity>_<sub>_*` must match a real sub-entity listed in `applies_to` |
| `wildcards` | no wildcard in required; wildcards in recommended/optional only as `<entity>_<sub>_*` sub-field groups |
| `codes` | category codes are unique; the `NN.` filename prefix equals `code`; subcategory and event-type codes are two digits |

Check the exact meta-field list and the field-name composition rules against `gim_schema/atomic_fields.py` and `field_schema_model.py` before you implement them.

5. Base-ref comparison:
   - for `validate --base-ref REF`, export `src/sdm` at REF with `git archive REF src/sdm` into a temporary dir
   - run structural validation and the rules on both trees, then diff the violation sets on `(rule_id, entry_key)`
   - new violations are errors (exit 1); existing ones are warnings
   - if the base tree fails to load structurally, treat every head violation as new and say so in the output
   - output format: `LEVEL rule_id file entry_key: message`, then a summary count
   - for GitHub Actions, also emit `::error file=…::` and `::warning file=…::` annotations when `GITHUB_ACTIONS=true`
6. CLI: `build-sdm validate [--base-ref REF] [-ll LEVEL]`.
7. Tests in `tests/rules/`: one passing fixture and one failing fixture per rule, using the `gim_config_helpers` builders, plus a base-ref test that builds a temporary git repo.
8. TOML formatting:
   - add `taplo` to the dev dependencies (the `taplo` PyPI wheel)
   - add a root `taplo.toml` with include `src/sdm/**/*.toml` and `tools/build_sdm/configs/*.toml`; choose options that keep multiline `"""` strings intact
   - **separate commit:** `taplo fmt`, then `uv run build-sdm build`, so the reformat doesn't change `generated/`. If it does, that is a formatter bug; fix the config.
9. Record the current warning baseline in the PR description: the per-rule counts from `validate` on main.
10. Update the standards files:
    - `AGENTS.md`: add `build-sdm validate` and `taplo fmt` to the commands
    - `.github/copilot-instructions.md`: finalize the "CI enforces this, don't comment" list using the rule IDs
    - `.github/instructions/sdm-data.instructions.md`: add the rule ID beside each rule that is now enforced, and keep inline only the judgment guidance CI can't check
    - amend ADR 0004 if the rule set or policy changed
11. Plan status: set `docs/plans/sdm-migration/03-lint.md` to `Status: done` and mark PR 3 done in the `README.md` status table.

## Verification
- `uv run pytest tests/rules` passes; every rule has a seeded failing case.
- `uv run build-sdm validate` on the imported data with no base ref lists the existing violations and exits 1, as expected.
- `uv run build-sdm validate --base-ref HEAD` exits 0, warnings only.
- Add a subcategory named `Bad-Name`, run again: exit 1 with one `naming` error.
- `taplo fmt --check` passes after the format commit.
- `build-sdm check-generated` still passes.
