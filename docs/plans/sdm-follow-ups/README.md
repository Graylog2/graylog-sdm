# SDM Follow-ups: review findings beyond the migration

Status: active
Created: 2026-11-10
Tracking: (issue link)

Follow-up activities from a tech-lead review of the SDM migration plan (`docs/plans/archive/20261109-sdm-migration/`). The review's core point: the SDM is a **data contract** consumed by Illuminate's pipelines and lookups, not just documentation. Most items move it toward machine-enforced compatibility.

Not covered here:
- **Two sources of truth / drift with Illuminate:** handled by the planned Illuminate issue to remove the SDM artifacts and tools once graylog-sdm can publish docs.
- **PR 2 bundling a refactor with behavior changes:** handled in `docs/plans/archive/20261109-sdm-migration/02-package.md` with ordered commits and a parity check across all plugins.

## Summary

The migration is done (2026-11-20), so each Target below is for the remaining work. Targets that named a migration PR the item missed now say "Any time".

| # | Follow-up | Priority | Status | Target | Decision needed |
|---|---|---|---|---|---|
| F1 | Golden-file tests for all output plugins | High | Partly done | Fixture-based tests before tool refactors (F7 v2, F16) | No |
| F2 | Compatibility checker + enforced `sdm_version` bump | High | Open | After F8's deprecation fields | Yes: versioning policy |
| F3 | Minimal CI from PR 2; branch protection now | High | Partly done | Required checks before more data PRs | Yes: required checks |
| F4 | Safe writes for the MadCap output path | High | Open | Any time | No |
| F5 | Robust violation fingerprints + violation ratchet | Medium | Done | | No |
| F6 | Correct base ref for push events | Medium | Done | | No |
| F7 | Check that pydantic v1 works on Python 3.13; schedule v2 | Medium | Partly done | v2 before F9's JSON Schema | Yes: v2 date |
| F8 | Semantic validation rules | Medium | Open | Deprecation fields before F2 | No |
| F9 | Machine-readable contract: JSON export, JSON Schema, release artifact | Medium | Open | After F2; before Illuminate cutover | Yes: artifact format |
| F10 | Reconsider the `src/sdm` directory name | Low | Done (kept) | | No |
| F11 | Collapse generated output in PR diffs | Low | Done | | No |
| F12 | Check that taplo preserves multiline strings | Low | Done | | No |
| F13 | Fix the field-schema index stylesheet path | Low | Done | | No |
| F14 | Replace non-ASCII characters in SDM meta text | Low | Open | Any time | No |
| F15 | Review `system_time` required `user_name` | Medium | Open | After F2's versioning policy | Yes: field classification |
| F16 | Per-entity MadCap config is keyed by module path, so `alert.toml`'s block is ignored | Medium | Open | Any time | Yes: key format |
| F17 | Decide whether to narrow `allowed_field_types` | Low | Open | After F2's versioning policy | Yes: SDM change policy |
| F18 | Log build errors once, at the CLI, instead of at every layer | Low | Done | | No |
| F19 | Line numbers for `validate` violations, so annotations show inline in PR diffs | Low | Done | | No |
| F20 | MadCap pages link resources at two different depths | Low | Open | Any time | Yes: Flare project layout |

## Order and dependencies

The F numbers are the order the items were recorded, not the order to work them. Most items are independent. These are not:

- **F8 before F2.** F2 detects deprecations from the `deprecated` and `replaced_by` fields that F8 adds to the schema model.
- **F2 before F9's release artifact.** F9 tags a release on each `sdm_version` bump, which only means something once F2 ties the bump to the change class.
- **F2's versioning policy before F15 and F17.** Both need a change classification and an `sdm_version` decision; the policy ADR answers them instead of one-off judgments.
- **F9 before the Illuminate cutover**, and before the long-term option in `docs/proposals/illuminate-skills-update.md` (a published artifact).
- **F7's v2 migration before F9's JSON Schema**, or plan for rework: v2 changes how JSON Schema is generated from the models. F8's new model fields are also cheaper to write once, after v2.
- **F1's fixture-based tests before tool refactors** (F7 v2, F16), so behavior changes show up independently of data changes.

F14, F16 and F20 each regenerate `generated/`. They can be worked in parallel, but every PR after the first needs a rebase and a rebuild, so merging them one at a time is simpler.

Suggested order:
1. Quick, independent fixes: F4, F19 (done).
2. The rest of F3 (required checks), before more data PRs land.
3. F14, as a data-only PR.
4. Decisions for the SDM owners: F2's versioning policy, F16's key format, F15, F17, F7's v2 date.
5. F8 (deprecation fields) → F2 → F9.

---

## F1. Golden-file tests for all output plugins

**Problem:** CI checks only the committed MadCap HTML for staleness. `category_data.csv` (Illuminate's core GIM lookup table) and `message_summaries.json` (core spotlight) matter more for production, yet a change that breaks them passes CI.

**Activity:**
- Add golden-file (snapshot) tests in `tests/golden/` for `CategoryDataCSVOutput`, `FieldMappingCSVOutput`, `JsonFileOutput` and `MessageSummariesOutput`, built from a small fixed fixture dataset (not the live data).
- Optionally, also snapshot outputs built from the live `src/sdm/` data. Updating a snapshot then becomes an explicit, reviewed act (`pytest --update-golden` or similar).

**Done when:** a change to any plugin's output fails `pytest` until the golden files are updated in the same PR.

**Status:** snapshots of the live-data output are planned for PR 2 (`02-package.md` step 12c). Still open: the snapshots built from a small fixed fixture dataset, which test plugin behavior independently of data changes.

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

**Status:** partly done (2026-11-20). CI wasn't moved earlier; it arrived in PR 4 as planned. A ruleset on `main` already requires a PR with 1 approval and resolved review threads, and blocks force pushes and deletion. Still open: making `data-lint`, `generated-fresh` and `python-qa` required checks, proposed in `docs/proposals/repo-governance.md`.

## F4. Safe writes for the MadCap output path

**Problem:** `--madcap-output-dir` replaces the default location. If the plugin clears or overwrites its output directory, pointing it at a Flare project could destroy hand-written content.

**Activity:**
1. Check whether `MadcapHtmlOutput` (or `utils.file.write_file`) deletes or cleans its target directory. Checked 2026-11-17: nothing in the tool deletes files (no `rmtree`, `unlink`, `remove` or `shutil`); it creates directories and overwrites same-named files. The risk is overwriting hand-edited files, not wiping a directory.
2. Write only into an empty directory, or one containing a `.build-sdm-output` marker file that the tool itself created. Otherwise refuse, unless `--force` is given.
3. Never delete files the tool didn't write. If stale-file cleanup is needed, limit it to files listed in a manifest from the previous run.
4. Add tests for the refuse, force and marker cases.

**Done when:** running with `--madcap-output-dir` pointed at a non-empty directory without a marker exits non-zero and changes nothing.

**Status:** open (2026-11-20). Planned for PR 2 but not done: the tool has no marker file and no `--force`. Only step 1 (the check) is complete.

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

**Status:** done in PR 3 (2026-11-19). GIM `entry_key`s use codes (`gim:10.05/name`); field references use the full field name. `validate --base-ref` prints per-rule base and head counts, fails when any count goes up, and writes the counts to the GitHub job summary. Tests cover a rename (stays a warning) and a renumber (becomes an error).

## F6. Correct base ref for push events

**Problem:** on push to `main`, `04-ci.md` compares against `HEAD~1`. That misses all but the last commit when several are pushed at once.

**Activity:**
- Use `${{ github.event.before }}` as the base ref for push events.
- Fall back to no base when it's the all-zero SHA (first push or new branch).
- Update `04-ci.md`.

**Status:** done in PR 4 (2026-11-19). On push, `data-lint` passes `github.event.before` as the base ref. When that is the all-zero SHA, or a commit missing after a force push, it compares against `HEAD` with a warning instead of using no base: with no base, every existing violation is an error and the job would always fail. Runs on `main` are not cancelled by later pushes, so no pushed range goes unchecked.

## F7. Pydantic v1 on Python 3.13; schedule v2

**Problem:** the plan keeps pydantic v1 and pins Python 3.13. That combination has to be confirmed rather than assumed, and pydantic v1 has no long-term future.

**Activity:**
- Before PR 2, confirm that the pinned `pydantic>=1.10,<2` resolves to a release that supports 3.13, and that the full test suite passes on 3.13 with no deprecation errors.
- Open a tracked issue for the pydantic v2 migration with a target date. The model code uses `parse_obj`, `root_validator`, `constr(regex=)` and `Extra`, so the change is contained but not trivial.

**Decision needed:** the target date or release for v2.

**Status:** the first activity is done (2026-11-17): `pydantic>=1.10,<2` resolves to 1.10.26 on Python 3.13.2, and the test suite passes with `-W error::DeprecationWarning` (on the imported tool before PR 2, and on `build_sdm` in PR 2). Still open: the v2 issue and its date.

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

**Status:** done (2026-11-20): kept. The migration shipped with `src/sdm/` and ADR 0001 records it. The tool config, docs and the path-scoped Copilot instructions all use it; renaming it now is a separate decision with its own ADR.

## F11. Collapse generated output in PR diffs

**Problem:** committed MadCap HTML produces large diffs that reviewers will skim, and that bury the source changes.

**Activity:**
- Add `.gitattributes` with `generated/** linguist-generated=true`. GitHub then collapses those files in PR diffs and leaves them out of language stats.
- `check-generated` still guards their correctness.

**Status:** done (2026-11-23). `.gitattributes` marks `generated/**` as `linguist-generated`.

## F12. Check that taplo preserves multiline strings

**Problem:** PR 3 reformats all source TOML with taplo. Multiline `"""` descriptions hold Markdown, and changes to whitespace or line endings inside them would change the content.

**Activity:**
- In PR 3, before the formatting commit, pin the taplo options that touch strings and arrays.
- After formatting, confirm that every source file still parses to the same values (a parse → compare script, not just a check that the output is unchanged) and that `generated/` is byte-identical.
- Add the parse-equivalence check as a test, so future formatter upgrades are covered too.

**Status:** done in PR 3 (2026-11-19). `taplo.toml` turns off key reordering and entry and comment alignment. `tests/test_taplo_roundtrip.py` formats a copy of every included file and checks that each parses to the same values. The format commit changed no parsed value in any of the 18 files it touched, and `generated/` and the golden snapshots were unchanged.

## F13. Fix the field-schema index stylesheet path

**Problem:** `field_schema_top_template.j2:6` uses `{{ resource_path }}`, but the template defines `resources_path`. The link renders as `/TableStyles/Alternate-Row-Color.css`, so the field-schema index page loads no table styles. Found in the PR 1 Copilot review (PR #3). The migration keeps output unchanged, so it isn't fixed there.

**Activity:**
- Use `resources_path` in the link.
- Regenerate `generated/MadcapHtmlOutput/` and check that only the field-schema index page changes.

**Done when:** the generated field-schema index links `../../Resources/TableStyles/Alternate-Row-Color.css`.

**Status:** done (2026-11-23). The template uses `resources_path`, and only the field-schema index page changed in `generated/`. `tests/output_madcap/test_madcap_resource_links.py` checks that every stylesheet reference in the generated pages is relative. The fix uses the path the template defines; whether that depth is right is F20.

## F14. Replace non-ASCII characters in SDM meta text

**Problem:** 16 source files contain non-ASCII characters (em dashes, curly apostrophes) in meta text, against the US-ASCII rule. The PR 1 Copilot review (PR #3) flagged `gim.config.toml`, `alert.toml`, `file.toml` and `reserved.toml`. PR 3's `ascii-meta` rule will report all of them as existing violations, which only warn.

**Activity:**
- After PR 3 lands, run `build-sdm validate` and fix every `ascii-meta` violation in one data PR, with ASCII equivalents (`-` or `--`, `'`, `"`).
- Regenerate `generated/`; only the affected text changes.
- Classify as additive (no meaning change).

**Done when:** `build-sdm validate` with no base ref reports no `ascii-meta` violations.

## F15. Review `system_time` required `user_name`

**Problem:** `26.system_time.toml` requires `source` and `user_name` for the whole category. Its description includes automatic changes (NTP, domain time sync), which may carry no user. Because the default subcategory's required fields are the baseline for the category, events from automatic sync can never satisfy it. Raised in the PR 1 Copilot review (PR #3).

**Activity:**
- Check what the supported sources actually emit for automatic time changes, and which Illuminate content (event definitions, dashboards) relies on `user_name` for this category.
- If `user_name` is not reliably present, move it to recommended.

**Decision needed:** keep `user_name` required, or move it to recommended. The SDM owners decide; record the change classification (relaxing a requirement) and whether it needs an `sdm_version` bump.

## F16. Per-entity MadCap config is keyed by module path

**Problem:** `MadcapHtmlOutput` reads per-entity config from `meta.plugin_config.<key>`, where `<key>` is its full module path (`build_sdm.output_plugins.madcap_html_output.plugin.MadcapHtmlOutput`). The data uses the short key `MadcapHtmlOutput`, so it never matches:
- `src/sdm/schema/alert.toml` has an active `[alert.meta.plugin_config.MadcapHtmlOutput]` block with `field_column_order`. The plugin ignores it, so the alert entity page uses the default column order. This was already the case in Illuminate.
- 21 other files carry commented-out examples with the short key; `12.network.toml` has one with the old `output_plugins.` module path.

Keying data by a Python module path also couples the SDM source to the tool's package layout: the PR 2 rename changed the key.

Found while implementing PR 2.

**Activity:**
- Decide the key format. The short class name (`MadcapHtmlOutput`) matches the data and survives refactors.
- Make the plugin read that key (optionally also the module path, with a warning, for a transition).
- Regenerate `generated/`; the alert entity page changes column order. Update the commented examples to the chosen key.
- Add a rule in `build-sdm validate` that flags `plugin_config` keys no plugin recognizes.

**Decision needed:** the key format.

## F17. Decide whether to narrow `allowed_field_types`

**Problem:** PR 2 moved field-type validation from a hard-coded set in the tool to `allowed_field_types` in `src/sdm/config/field_schema.config.toml`. To keep the rule unchanged, the config list holds all 23 types the tool accepted before (several OpenSearch types such as `half_float`, `*_range`, `object`, `nested` and `alias`). Before PR 2 the config list had 7 types, but nothing enforced them. The data uses 9 types: `text`, `keyword`, `keyword/lowercase`, `integer`, `long`, `byte`, `boolean`, `date`, `ip`.

Narrowing the list rejects definitions that build today. The PR 2 Copilot review (PR #4) raised this. It needs a deliberate decision, not a side effect of the migration.

**Activity:**
- Decide which types the SDM should allow, e.g. only those Graylog's index mappings support for normalized fields.
- Classify the change under the SDM change policy (it restricts authors, not consumers) and decide whether it needs an `sdm_version` bump.
- Update the list and `tests/test_field_types.py::test_allowlist_keeps_every_previously_accepted_type`.

**Decision needed:** the allowed set, and its change classification.

## F18. Log build errors once, at the CLI

**Problem:** PR 2 made plugin failures fatal by adding a bare `raise` after the log call in each legacy `except` handler. The re-raises are correct, but every layer still logs, so one failure is reported several times. A failed write logs in `write_file`, again in the plugin's handler, again in `plugin_loader.safe_execute`, and finally in the CLI with the traceback. Related inconsistencies:
- `message_summaries_output/plugin.py` logs invalid templates at warning level, then fails the build.
- `safe_execute` formats its log messages with f-strings.
- `runner.py` and `safe_execute` catch `Exception` only to log and re-raise.

Raised during the PR 2 review.

**Activity:**
- Log errors once, in the CLI (`Build failed`, with the traceback at debug or always).
- In lower layers, drop log-and-re-raise handlers. Where a handler adds useful context (plugin name, category, file), raise a project exception with `raise ... from e` instead of logging.
- Make `message_summaries_output` validation failures errors, not warnings.
- Add a test that one failure produces a single error-level log record.

**Decision needed:** none.

**Status:** done in PR 3 (2026-11-19). The CLI logs one error record with the exception chain and notes, and the traceback at debug level; lower layers add context with `add_note()`. `tests/test_cli_build_failures.py` checks that one failure produces one error record.

## F19. Line numbers for `validate` violations

**Problem:** a violation carries a file but no line. In CI, its `::error` annotation is attached to the file at line 0, so GitHub shows it only on the Checks tab, not inline in the PR diff next to the change that caused it. The loader parses with tomlkit and normalizes to plain Python values, which drops source positions. Seen on the PR 4 test PR (#8).

**Activity:**
- Add an optional `line` to `Violation` and pass it as `line=` in `format_github_annotations` and in the text report.
- Find the line after the fact rather than threading positions through the loader: from the `entry_key` (for example `gim:26.01/name`), locate the table header for that entry in the source file (`[system_time.subcategories.01]`), then the key within that table. Fall back to no line when the lookup fails.
- Keep `entry_key` as the identity for the base-ref comparison. A line number changes whenever lines above it move, so it must not affect whether a violation counts as new.
- Tests: a violation in a subcategory, an event type, and a schema field each get the right line; an entry that can't be located gets none.

**Decision needed:** none.

**Status:** done (2026-11-24). `build_sdm/rules/locate.py` indexes each source file's tables, dotted keys, array-of-table elements (matched by `field_suffix`, `template_id` or `type`) and list items, skipping multiline strings, then resolves each `entry_key` to a line. An attribute with no line of its own, such as a subcategory's code, resolves to its table header. The text report shows `file:line` and annotations get `line=`. All 211 violations on `main` at the time were located. `tests/rules/test_locate.py` covers each entry shape, the fallbacks, unlocatable entries, and that a moved line keeps a violation existing.

## F20. MadCap pages link resources at two different depths

**Problem:** every generated page sits one directory below the output root (`Graylog Information Models/` or `Field Schema Entities/`), but the pages reference `Resources/` at two depths:
- the 21 category pages link their stylesheets with `../Resources/` (`gim_category_template.j2`)
- every table's `mc-table-style` uses `../../Resources/` (the default in `macros/tables.html.j2`), which the two top-level templates also set

At most one depth can be right for a given Flare project, so either the category page stylesheets or every table style resolves to a missing file. Which one depends on where the output is placed in the Flare project, and nothing in this repo records that (ADR 0003 leaves delivery to Flare out of scope). Found while fixing F13.

**Activity:**
- Find out from the Flare project where the generated folders go, relative to its `Resources/` folder.
- Set one `resources_path` for all templates, passed in from the plugin config rather than set in each template, and pass it to `render_table`.
- Regenerate `generated/` and record the layout in ADR 0003.

**Decision needed:** the Flare project layout, from whoever maintains the Flare project.
