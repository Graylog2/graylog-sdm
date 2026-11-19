---
applyTo: "src/sdm/**"
---

# SDM data review rules

These files are the SDM source data: GIM infomodels (classes, categories, subcategories, event types) and schema field definitions.

Rules marked with a rule ID are enforced by `build-sdm validate` in CI; don't comment on them. Review the rest, which need judgment.

## Meta fields

- `title`, `description` and other meta fields use US-ASCII printable characters only. No Unicode, smart quotes, em dashes, or non-ASCII symbols. (`ascii-meta`)
- Write for a technical audience (somewhat to very technical). Use precise, unambiguous language suited to security practitioners and engineers.

## GIM configuration

Apply these strictly to new or changed entries. Some existing entries do not conform; that is known. Do not accept new entries that copy a non-conforming pattern.

- **Naming:** class, category, subcategory and event type names are all lowercase, letters `a-z` only, words separated by underscores. No spaces, hyphens, digits, or other characters. (`naming`)
- **Uniqueness:** subcategory names and event type names are unique across the entire GIM. The only exception is `default`. (`unique-names`)
- **Default subcategory number:** the `default` subcategory is always number `99`, and `99` is used only for `default`. (`default-99`)
- **Codes:** category codes are unique, and each infomodel file name starts with its category code (`10.authentication.toml`). (`codes`)
- **Field references:** every field in a required, recommended or optional list is defined in the schema. (`fields-exist`)

## Field classification

Every field attached to a GIM subcategory is classified as required, recommended, or optional.

- **Required:** the minimum fields needed for Illuminate to work. Only fields very likely to appear in event logs for the subcategory. Keep it conservative: a field is required only when it is needed for proper event analysis (e.g. used in event definitions or alerts). If many dashboard widgets depend on a recommended field, promotion to required may be justified.
- **Recommended:** fields that typically appear in events for the subcategory and are likely used in Illuminate content, but are not critical (e.g. not used in event definitions). Dashboard widgets may use them and may degrade when the field is absent.
- **Optional:** fields useful for investigation, not required for Illuminate to work. Illuminate content must not rely on them.
- **Default baseline:** the fields required by a category's `default` subcategory are the baseline for every other subcategory in that category. Other subcategories may require more fields, never fewer. (`default-baseline`)
- **Cross-category fields:** classification arrays may include fields from any GIM category (e.g. `user_name`, `process_name`) when they are semantically important for the subcategory.

## Field enumeration

- List every field explicitly. Never accept a broad wildcard (e.g. `entity_*`) in place of enumeration. (`wildcards`)
- Sub-field group wildcards (e.g. `entity_hash_*`) are allowed only in recommended or optional, never in required (`wildcards`). Whether the member fields are really interchangeable or not yet enumerated is a judgment call: review it.

## Change policy

- A rename, removal, or type change is breaking and requires an `sdm_version` bump.
- A removed field name or GIM code must never be reused for a different meaning.
